"""ToolInstallationService: the Phase 11 orchestrator.

    DISCOVERED -> REVIEWING -> DEPENDENCIES_CHECKING -> WAITING_FOR_APPROVAL
    -> PREPARING -> INSTALLING -> VERIFYING -> INSTALLED
                                             \\-> FAILED / BLOCKED /
                                                 CANCELLED / ROLLBACK_REQUIRED

Every install/verify command is built by services.terminal.
command_templates (the only place argv is produced) and run through the
*existing, unchanged* TerminalEngine -> PolicyEngine -> PlatformAdapter
pipeline — this service never spawns a process itself and never lets the
AI see a shell. Approval for the install step is enforced twice: once
when the plan is generated (`ReadinessChecker`/`PolicyEngine.evaluate`)
and again, freshly, at execution time — a decision never survives from
request time to execution time without being an explicit `ALLOW`/approved
`REQUIRE_APPROVAL`.
"""

from datetime import UTC, datetime
from uuid import UUID

from services.installation.audit_events import (
    INSTALL_APPROVED,
    INSTALL_BLOCKED,
    INSTALL_CANCELLED,
    INSTALL_COMPLETED,
    INSTALL_FAILED,
    INSTALL_PLAN_GENERATED,
    INSTALL_READINESS_CHECKED,
    INSTALL_REJECTED,
    INSTALL_REQUESTED,
    INSTALL_STARTED,
    INSTALL_STEP_COMPLETED,
    INSTALL_STEP_FAILED,
    INSTALL_VERIFICATION_FAILED,
    INSTALL_VERIFIED,
    INSTALL_VERIFYING,
)
from services.installation.config import InstallationServiceConfig
from services.installation.environment import EnvironmentInspector
from services.installation.errors import (
    ApprovalRequiredError,
    InvalidStateTransitionError,
    PackageManagerUnavailableError,
    ToolNotApprovedError,
    UnsupportedPlatformForToolError,
)
from services.installation.models import (
    InstallationAttempt,
    InstallationRequest,
    InstallationState,
)
from services.installation.planner import InstallationPlanner
from services.installation.readiness import ReadinessChecker
from services.installation.registry import InstallationRegistry
from services.installation.verifier import InstallationVerifier
from services.policy.engine import (
    ActionRequest,
    PolicyEngine,
    PolicyVerdict,
    RiskTier,
    TargetScope,
)
from services.terminal.audit import AuditEvent, AuditSink, LoggingAuditSink, truncate_for_log
from services.terminal.command_templates import (
    INSTALL_ACTION_TYPE,
    VERIFY_ACTION_TYPE,
    build_install_command,
    build_verification_command,
)
from services.terminal.engine import TerminalEngine
from services.terminal.models import CommandStatus, TerminalCommandRequest
from services.tools.models import ToolRecord, TrustStatus
from services.tools.registry import ToolRegistry


class ToolInstallationService:
    def __init__(
        self,
        *,
        tools: ToolRegistry,
        installations: InstallationRegistry,
        config: InstallationServiceConfig | None = None,
        policy_engine: PolicyEngine | None = None,
        environment_inspector: EnvironmentInspector | None = None,
        planner: InstallationPlanner | None = None,
        verifier: InstallationVerifier | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._tools = tools
        self._installations = installations
        self._config = config or InstallationServiceConfig()
        self._policy_engine = policy_engine or PolicyEngine()
        self._readiness = ReadinessChecker(policy_engine=self._policy_engine)
        self._environment = environment_inspector or EnvironmentInspector()
        self._planner = planner or InstallationPlanner()
        self._verifier = verifier or InstallationVerifier()
        self._audit = audit_sink or LoggingAuditSink()
        self._running_commands: dict[UUID, UUID] = {}

    def _emit(self, event_type: str, request: InstallationRequest, **data: object) -> None:
        self._audit.emit(
            AuditEvent(
                event_type=event_type,
                session_id=str(request.session_id) if request.session_id else None,
                command_id=None,
                task_id=None,
                data={
                    "request_id": str(request.id),
                    "tool_id": str(request.tool_id),
                    "state": request.state.value,
                    **data,
                },
            )
        )

    # --- read-only accessors (route layer never reaches into privates) ------

    async def check_readiness(self, tool_id: UUID, *, target_scope: TargetScope, platform: str):
        return await self._readiness.check(
            self._tools, tool_id, target_scope=target_scope, platform=platform
        )

    async def get_request(self, request_id: UUID) -> InstallationRequest:
        return await self._installations.get(request_id)

    async def list_installations(self) -> list[InstallationRequest]:
        return await self._installations.list_all()

    async def list_installed(self) -> list[InstallationRequest]:
        return await self._installations.list_installed()

    # --- request / plan / approval -----------------------------------------

    async def request_installation(
        self,
        tool_id: UUID,
        *,
        target_scope: TargetScope,
        platform: str,
        requested_by: str | None = None,
    ) -> InstallationRequest:
        request = InstallationRequest(
            tool_id=tool_id, target_id=target_scope.id, requested_by=requested_by
        )
        self._emit(INSTALL_REQUESTED, request, platform=platform)

        report = await self._readiness.check(
            self._tools, tool_id, target_scope=target_scope, platform=platform
        )
        self._emit(
            INSTALL_READINESS_CHECKED,
            request,
            ready=report.ready,
            checks={c.name: c.status for c in report.checks},
        )

        if not report.ready or report.tool is None:
            request.state = InstallationState.BLOCKED
            request.error_message = "; ".join(
                c.detail for c in report.checks if c.status == "FAIL"
            ) or "Tool is not ready for installation."
            await self._installations.create(request)
            self._emit(INSTALL_BLOCKED, request, reason=request.error_message)
            return request

        environment = self._environment.inspect()
        try:
            plan = self._planner.build_plan(report.tool, environment, target_platform=platform)
        except (UnsupportedPlatformForToolError, PackageManagerUnavailableError) as exc:
            request.state = InstallationState.BLOCKED
            request.error_message = str(exc)
            await self._installations.create(request)
            self._emit(INSTALL_BLOCKED, request, reason=request.error_message)
            return request

        request.plan = plan
        self._emit(INSTALL_PLAN_GENERATED, request, package_manager=plan.package_manager.value)

        policy_denied = (
            report.policy_decision is not None
            and report.policy_decision.verdict == PolicyVerdict.DENY
        )
        if policy_denied:
            request.state = InstallationState.BLOCKED
            request.error_message = "; ".join(report.policy_decision.reasons)
            await self._installations.create(request)
            self._emit(INSTALL_BLOCKED, request, reason=request.error_message)
            return request

        request.state = (
            InstallationState.WAITING_FOR_APPROVAL
            if plan.approval_required
            else InstallationState.PREPARING
        )
        await self._installations.create(request)
        return request

    async def approve(self, request_id: UUID, *, approved_by: str) -> InstallationRequest:
        request = await self._installations.get(request_id)
        if request.state != InstallationState.WAITING_FOR_APPROVAL:
            raise InvalidStateTransitionError(
                f"Installation request {request_id} is not waiting for approval "
                f"(state={request.state.value})."
            )
        request.approved_by = approved_by
        request.approved_at = datetime.now(UTC)
        request.state = InstallationState.PREPARING
        await self._installations.save(request)
        self._emit(INSTALL_APPROVED, request, approved_by=approved_by)
        return request

    async def reject(self, request_id: UUID, *, reason: str) -> InstallationRequest:
        request = await self._installations.get(request_id)
        if request.is_terminal():
            raise InvalidStateTransitionError(
                f"Installation request {request_id} is already in a terminal state "
                f"(state={request.state.value})."
            )
        request.state = InstallationState.CANCELLED
        request.rejection_reason = reason
        await self._installations.save(request)
        self._emit(INSTALL_REJECTED, request, reason=reason)
        return request

    async def cancel(self, request_id: UUID, engine: TerminalEngine) -> InstallationRequest:
        request = await self._installations.get(request_id)
        if request.is_terminal():
            return request
        command_id = self._running_commands.get(request_id)
        if command_id is not None:
            await engine.terminate(command_id)
        else:
            request.state = InstallationState.CANCELLED
            await self._installations.save(request)
            self._emit(INSTALL_CANCELLED, request)
        return request

    # --- execution -----------------------------------------------------------

    async def start_installation(
        self,
        request_id: UUID,
        *,
        engine: TerminalEngine,
        session_id: UUID,
        target_scope: TargetScope,
    ) -> InstallationRequest:
        request = await self._installations.get(request_id)
        if request.state == InstallationState.WAITING_FOR_APPROVAL:
            raise ApprovalRequiredError(
                f"Installation request {request_id} requires approval before it can start."
            )
        if request.state != InstallationState.PREPARING:
            raise InvalidStateTransitionError(
                f"Installation request {request_id} is not ready to start "
                f"(state={request.state.value})."
            )
        if request.plan is None:
            raise InvalidStateTransitionError("Installation request has no plan.")

        request.session_id = session_id
        request.state = InstallationState.INSTALLING
        await self._installations.save(request)
        self._emit(INSTALL_STARTED, request)

        tool = await self._tools.get(request.tool_id)
        if tool.trust_status != TrustStatus.APPROVED:
            raise ToolNotApprovedError(f"Tool '{tool.name}' is not APPROVED.")

        step = request.plan.installation_steps[0]

        last_error_category: str | None = None
        succeeded = False

        for attempt_number in range(1, self._config.max_install_attempts + 1):
            argv = build_install_command(
                step.package_manager.value, step.package_name, step.version
            )
            decision = self._policy_engine.evaluate(
                ActionRequest(
                    action_id=request.id,
                    action_type=INSTALL_ACTION_TYPE,
                    risk_tier=request.plan.risk_level,
                    target=target_scope,
                )
            )
            if decision.verdict == PolicyVerdict.DENY:
                request.state = InstallationState.BLOCKED
                request.error_message = "; ".join(decision.reasons)
                await self._installations.save(request)
                self._emit(INSTALL_BLOCKED, request, reason=request.error_message)
                return request

            approved_by_user = (
                decision.verdict == PolicyVerdict.ALLOW or request.approved_by is not None
            )
            terminal_request = TerminalCommandRequest(
                session_id=session_id,
                command=argv,
                authorization_context=decision,
                timeout_seconds=self._config.install_timeout_seconds,
                approved_by_user=approved_by_user,
            )
            self._running_commands[request.id] = terminal_request.id
            attempt_started = datetime.now(UTC)
            result = await engine.execute(terminal_request)
            self._running_commands.pop(request.id, None)

            attempt = InstallationAttempt(
                attempt_number=attempt_number,
                started_at=attempt_started,
                completed_at=result.completed_at,
                exit_code=result.exit_code,
                stdout=truncate_for_log(result.stdout),
                stderr=truncate_for_log(result.stderr),
                duration_seconds=result.duration_seconds,
                error_category=(
                    result.status.value if result.status != CommandStatus.COMPLETED else None
                ),
            )
            request.attempts.append(attempt)
            await self._installations.save(request)

            if result.status == CommandStatus.CANCELLED:
                request.state = InstallationState.CANCELLED
                await self._installations.save(request)
                self._emit(INSTALL_CANCELLED, request)
                return request

            if result.status == CommandStatus.COMPLETED:
                self._emit(INSTALL_STEP_COMPLETED, request, attempt=attempt_number)
                succeeded = True
                break

            self._emit(
                INSTALL_STEP_FAILED,
                request,
                attempt=attempt_number,
                status=result.status.value,
                stderr_preview=truncate_for_log(result.stderr),
            )
            # Loop detection: an identical failure category on consecutive
            # attempts means retrying again would just repeat it — stop
            # early instead of burning the remaining attempt budget.
            if last_error_category is not None and last_error_category == attempt.error_category:
                break
            last_error_category = attempt.error_category

        if not succeeded:
            request.state = InstallationState.FAILED
            request.error_message = f"Installation failed after {len(request.attempts)} attempt(s)."
            await self._installations.save(request)
            self._emit(INSTALL_FAILED, request, attempts=len(request.attempts))
            return request

        return await self._verify(request, tool, engine, session_id, target_scope)

    async def _verify(
        self,
        request: InstallationRequest,
        tool: ToolRecord,
        engine: TerminalEngine,
        session_id: UUID,
        target_scope: TargetScope,
    ) -> InstallationRequest:
        request.state = InstallationState.VERIFYING
        await self._installations.save(request)
        self._emit(INSTALL_VERIFYING, request)

        step = request.plan.installation_steps[0]
        verify_argv = build_verification_command(
            step.package_manager.value, step.package_name, entrypoint=tool.entrypoint
        )
        decision = self._policy_engine.evaluate(
            ActionRequest(
                action_id=request.id,
                action_type=VERIFY_ACTION_TYPE,
                risk_tier=RiskTier.LOW,
                target=target_scope,
            )
        )
        verify_request = TerminalCommandRequest(
            session_id=session_id,
            command=verify_argv,
            authorization_context=decision,
            timeout_seconds=self._config.verify_timeout_seconds,
            approved_by_user=decision.verdict == PolicyVerdict.ALLOW,
        )
        result = await engine.execute(verify_request)
        verification = self._verifier.evaluate(result)
        request.verification = verification

        if verification.verified:
            request.state = InstallationState.INSTALLED
            await self._installations.save(request)
            self._emit(INSTALL_VERIFIED, request, checks=verification.checks)
            self._emit(INSTALL_COMPLETED, request)
        else:
            request.state = InstallationState.ROLLBACK_REQUIRED
            request.error_message = (
                "Installation command succeeded but verification could not confirm the "
                "tool is actually usable."
            )
            await self._installations.save(request)
            self._emit(INSTALL_VERIFICATION_FAILED, request, checks=verification.checks)
        return request
