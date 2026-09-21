"""AgentOrchestrator: the stateful, resumable control loop.

    create_task()  -> UNDERSTANDING -> PLANNING
    step()         -> one reasoning call -> one structured action ->
                      AgentPolicyGate -> (approval?) -> execute via the
                      EXISTING, unmodified TerminalEngine / ToolRegistry /
                      ToolDiscoveryService / ToolInstallationService ->
                      observe -> classify -> adapt -> persist

`step()` is the only place actions happen, and it always re-reads state
from `AgentTaskRegistry` first — nothing is held only in Python-process
memory that isn't also in the registry, so calling `step()` again after a
hypothetical process restart continues from exactly where persisted state
left off rather than re-running completed actions. There is deliberately
no separate durable-execution engine in this phase; see the module
docstring's design note in the Phase 12 summary for why that's an honest
scope cut, not an oversight.

AI -> shell is structurally impossible here: the reasoner never returns
argv, only an `ActionType` + free-form `arguments` dict, and
RUN_DIAGNOSTIC/COLLECT_INFORMATION only ever resolve to
services.terminal.command_templates.resolve_command("diagnostics.echo_test")
— the one reviewed, registered action type that exists today. Adding a
new capability means registering a new reviewed template, exactly as
every prior phase already required; the agent has no way to invent one.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from services.agent_orchestrator.actions import ActionType
from services.agent_orchestrator.analysis import ResultAnalyzer, VerificationEngine
from services.agent_orchestrator.budget import AgentBudgetManager
from services.agent_orchestrator.errors import (
    BudgetExceededError,
    ConcurrentTaskLimitError,
    InvalidStateTransitionError,
    NotWaitingForApprovalError,
)
from services.agent_orchestrator.errors import OutOfScopeError as _OutOfScopeError
from services.agent_orchestrator.events import (
    ACTION_OUTPUT,
    ACTION_STARTED,
    AGENT_STARTED,
    APPROVAL_RECEIVED,
    APPROVAL_REQUIRED,
    AUTHORIZATION_CHECK,
    OBJECTIVE_PARSED,
    RECOVERY_STARTED,
    TARGET_IDENTIFIED,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_PAUSED,
    TASK_RESUMED,
    AgentEvent,
    AgentEventBus,
)
from services.agent_orchestrator.models import (
    AgentAction,
    AgentError,
    AgentPhase,
    AgentTaskState,
    ApprovalState,
    CancellationState,
    Evidence,
    EvidenceKind,
    RecoveryAttempt,
)
from services.agent_orchestrator.policy_gate import AgentPolicyGate
from services.agent_orchestrator.reasoning import (
    AgentReasoner,
    AgentReasoningError,
    ReasoningContext,
)
from services.agent_orchestrator.recovery import (
    AdaptationEngine,
    AdaptationStrategy,
    ErrorClassifier,
)
from services.agent_orchestrator.registry import AgentTaskRegistry
from services.agent_orchestrator.report import ReportBuilder
from services.installation.environment import EnvironmentInspector
from services.installation.service import ToolInstallationService
from services.policy.engine import (
    ActionRequest,
    PolicyDecision,
    PolicyEngine,
    PolicyVerdict,
    TargetScope,
)
from services.terminal.command_templates import ACTION_RISK_TIERS, resolve_command
from services.terminal.engine import TerminalEngine
from services.terminal.models import CommandStatus, TerminalCommandRequest
from services.tools.discovery import ToolDiscoveryService
from services.tools.registry import ToolRegistry

_DIAGNOSTIC_ACTION_TYPE = "diagnostics.echo_test"

_POST_ACTION_PHASE: dict[ActionType, AgentPhase] = {
    ActionType.ANALYZE_OUTPUT: AgentPhase.ANALYZING,
    ActionType.VERIFY_FINDING: AgentPhase.VERIFYING,
    ActionType.INSTALL_TOOL: AgentPhase.OBSERVING,
    ActionType.RESEARCH_TOOL: AgentPhase.RESEARCHING,
}


class AgentOrchestrator:
    def __init__(
        self,
        *,
        registry: AgentTaskRegistry,
        event_bus: AgentEventBus,
        reasoner: AgentReasoner,
        tool_registry: ToolRegistry,
        discovery_service: ToolDiscoveryService,
        installation_service: ToolInstallationService,
        terminal_engine: TerminalEngine,
        budget: AgentBudgetManager | None = None,
        policy_gate: AgentPolicyGate | None = None,
        policy_engine: PolicyEngine | None = None,
        environment_inspector: EnvironmentInspector | None = None,
        analyzer: ResultAnalyzer | None = None,
        verifier: VerificationEngine | None = None,
        report_builder: ReportBuilder | None = None,
        self_healing_engine=None,
    ) -> None:
        self._registry = registry
        self._events = event_bus
        self._reasoner = reasoner
        self._tools = tool_registry
        self._discovery = discovery_service
        self._installations = installation_service
        self._terminal = terminal_engine
        self._budget = budget or AgentBudgetManager()
        self._gate = policy_gate or AgentPolicyGate()
        self._policy_engine = policy_engine or PolicyEngine()
        self._environment = environment_inspector or EnvironmentInspector()
        self._analyzer = analyzer or ResultAnalyzer()
        self._verifier = verifier or VerificationEngine()
        self._reports = report_builder or ReportBuilder()
        self._adaptation = AdaptationEngine(self._budget)
        self._classifier = ErrorClassifier()
        # Optional Phase 13 upgrade: if provided, a failed action goes
        # through DiagnosisEngine + HealingPlanner in addition to the
        # simpler AdaptationEngine, and the proposal is stored on the
        # task's recovery attempts. Never applied automatically — it's
        # informational until a human or a future controller acts on it.
        self._self_healing = self_healing_engine

    def _emit(self, state: AgentTaskState, event_type: str, data: dict) -> None:
        self._events.publish(AgentEvent(task_id=state.id, event_type=event_type, data=data))

    # --- read-only accessors (route layer never reaches into privates) ------

    async def get_task(self, task_id: UUID) -> AgentTaskState:
        return await self._registry.get(task_id)

    async def list_tasks(self) -> list[AgentTaskState]:
        return await self._registry.list_all()

    def budget_status(self, state: AgentTaskState) -> dict:
        return self._budget.status(state)

    # --- lifecycle -----------------------------------------------------------

    async def create_task(
        self,
        *,
        objective: str,
        user_request: str,
        target: str | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        authorization_status: str = "UNKNOWN",
        scope: list[str] | None = None,
    ) -> AgentTaskState:
        if await self._registry.count_active() >= self._budget.config.max_concurrent_tasks:
            raise ConcurrentTaskLimitError(
                f"Maximum concurrent agent tasks reached "
                f"({self._budget.config.max_concurrent_tasks})."
            )

        state = AgentTaskState(
            objective=objective,
            user_request=user_request,
            target=target,
            target_type=target_type,
            target_id=target_id,
            authorization_status=authorization_status,
            scope=scope or [],
            phase=AgentPhase.UNDERSTANDING,
            started_at=datetime.now(UTC),
        )
        await self._registry.create(state)
        self._emit(state, AGENT_STARTED, {"objective": objective})
        self._emit(state, OBJECTIVE_PARSED, {"objective": objective})
        if target:
            self._emit(state, TARGET_IDENTIFIED, {"target": target})
        self._emit(state, AUTHORIZATION_CHECK, {"status": authorization_status})

        state.phase = (
            AgentPhase.WAITING_FOR_AUTHORIZATION
            if authorization_status != "AUTHORIZED"
            else AgentPhase.PLANNING
        )
        await self._registry.save(state)
        return state

    async def pause(self, task_id: UUID) -> AgentTaskState:
        state = await self._registry.get(task_id)
        if state.is_terminal():
            raise InvalidStateTransitionError(f"Task {task_id} is already in a terminal state.")
        state.phase = AgentPhase.PAUSED
        await self._registry.save(state)
        self._emit(state, TASK_PAUSED, {})
        return state

    async def resume(self, task_id: UUID) -> AgentTaskState:
        state = await self._registry.get(task_id)
        if state.phase != AgentPhase.PAUSED:
            raise InvalidStateTransitionError(f"Task {task_id} is not paused.")
        state.phase = AgentPhase.PLANNING
        await self._registry.save(state)
        self._emit(state, TASK_RESUMED, {})
        return state

    async def cancel(self, task_id: UUID) -> AgentTaskState:
        state = await self._registry.get(task_id)
        if state.is_terminal():
            return state
        state.cancellation_state = CancellationState.CANCELLED
        state.phase = AgentPhase.CANCELLED
        state.completed_at = datetime.now(UTC)
        await self._registry.save(state)
        return state

    async def provide_clarification(self, task_id: UUID, answer: str) -> AgentTaskState:
        state = await self._registry.get(task_id)
        if state.phase != AgentPhase.WAITING_FOR_AUTHORIZATION:
            raise InvalidStateTransitionError(f"Task {task_id} is not awaiting clarification.")
        state.observations.append(
            Evidence(kind=EvidenceKind.OBSERVATION, summary=f"User clarification: {answer}")
        )
        state.clarification_question = None
        state.unknowns = [u for u in state.unknowns if u.lower() not in answer.lower()]
        state.phase = AgentPhase.PLANNING
        await self._registry.save(state)
        return state

    async def approve_action(self, task_id: UUID, *, approved_by: str) -> AgentTaskState:
        state = await self._registry.get(task_id)
        if state.phase != AgentPhase.WAITING_FOR_APPROVAL or state.pending_action_id is None:
            raise NotWaitingForApprovalError(f"Task {task_id} has no action awaiting approval.")
        action = self._find_action(state, state.pending_action_id)
        action.approval_state = ApprovalState.APPROVED
        state.approval_state = ApprovalState.APPROVED
        state.phase = AgentPhase.PREPARING
        await self._registry.save(state)
        self._emit(
            state, APPROVAL_RECEIVED, {"actionId": str(action.id), "approvedBy": approved_by}
        )
        return state

    async def reject_action(self, task_id: UUID, *, reason: str) -> AgentTaskState:
        state = await self._registry.get(task_id)
        if state.phase != AgentPhase.WAITING_FOR_APPROVAL or state.pending_action_id is None:
            raise NotWaitingForApprovalError(f"Task {task_id} has no action awaiting approval.")
        action = self._find_action(state, state.pending_action_id)
        action.approval_state = ApprovalState.REJECTED
        action.result_summary = f"Rejected: {reason}"
        state.approval_state = ApprovalState.REJECTED
        state.pending_action_id = None
        state.phase = AgentPhase.BLOCKED
        state.completed_at = datetime.now(UTC)
        await self._registry.save(state)
        return state

    @staticmethod
    def _find_action(state: AgentTaskState, action_id: UUID) -> AgentAction:
        for action in state.actions:
            if action.id == action_id:
                return action
        raise InvalidStateTransitionError(f"Action {action_id} not found on task {state.id}.")

    # --- the reasoning/execution step -----------------------------------------

    async def step(
        self, task_id: UUID, *, target_scope: TargetScope | None = None, platform: str = "LINUX"
    ) -> AgentTaskState:
        state = await self._registry.get(task_id)

        if state.is_terminal() or state.phase in (
            AgentPhase.PAUSED,
            AgentPhase.WAITING_FOR_APPROVAL,
            AgentPhase.WAITING_FOR_AUTHORIZATION,
        ):
            return state

        if state.phase == AgentPhase.PREPARING and state.pending_action_id is not None:
            # An action was already reasoned about and approved — execute
            # exactly that action rather than asking the reasoner for a
            # new one (which would silently drop the approved action).
            action = self._find_action(state, state.pending_action_id)
            state.pending_action_id = None
            return await self._execute(state, action, target_scope=target_scope, platform=platform)

        try:
            self._budget.check_action_budget(state)
            self._budget.check_model_call_budget(state)
        except BudgetExceededError as exc:
            return await self._block(state, str(exc))

        environment = self._environment.inspect()
        context = ReasoningContext(
            available_capabilities=sorted(
                {c for t in await self._tools.list() for c in t.capabilities}
            ),
            platform=environment.platform,
            policy_constraints=[],
            budget_remaining=self._budget.status(state),
        )

        try:
            decision = await self._reasoner.decide(state, context)
        except AgentReasoningError as exc:
            state.errors.append(AgentError(category="invalid_decision", message=str(exc)))
            return await self._block(state, f"Reasoning failed: {exc}")
        state.model_call_count += 1

        try:
            gate = self._gate.evaluate(state, decision)
        except _OutOfScopeError as exc:
            state.errors.append(AgentError(category="out_of_scope", message=str(exc)))
            return await self._block(state, str(exc))

        action = self._gate.build_action(decision, gate)
        state.actions.append(action)
        state.action_count += 1
        self._emit(
            state,
            ACTION_STARTED,
            {"actionId": str(action.id), "actionType": action.action_type.value},
        )

        if not gate.allowed:
            action.result_summary = "; ".join(gate.reasons)
            state.phase = AgentPhase.WAITING_FOR_AUTHORIZATION
            state.clarification_question = gate.reasons[0] if gate.reasons else None
            await self._registry.save(state)
            return state

        if action.requires_approval and action.approval_state == ApprovalState.PENDING:
            state.phase = AgentPhase.WAITING_FOR_APPROVAL
            state.pending_action_id = action.id
            state.approval_state = ApprovalState.PENDING
            self._emit(state, APPROVAL_REQUIRED, {"actionId": str(action.id)})
            await self._registry.save(state)
            return state

        return await self._execute(state, action, target_scope=target_scope, platform=platform)

    async def _block(self, state: AgentTaskState, reason: str) -> AgentTaskState:
        state.phase = AgentPhase.BLOCKED
        state.next_action = reason
        state.completed_at = datetime.now(UTC)
        await self._registry.save(state)
        return state

    async def _execute(
        self, state: AgentTaskState, action: AgentAction, *, target_scope, platform: str
    ) -> AgentTaskState:
        state.phase = AgentPhase.EXECUTING
        await self._registry.save(state)

        try:
            if action.action_type == ActionType.CHECK_ENVIRONMENT:
                await self._do_check_environment(state, action)
            elif action.action_type == ActionType.DISCOVER_TARGET:
                self._do_discover_target(state, action)
            elif action.action_type == ActionType.RESEARCH_TOOL:
                await self._do_research_tool(state, action)
            elif action.action_type == ActionType.INSTALL_TOOL:
                await self._do_install_tool(
                    state, action, target_scope=target_scope, platform=platform
                )
            elif action.action_type in (ActionType.RUN_DIAGNOSTIC, ActionType.COLLECT_INFORMATION):
                await self._do_run_diagnostic(state, action, target_scope=target_scope)
            elif action.action_type == ActionType.ANALYZE_OUTPUT:
                self._do_analyze(state, action)
            elif action.action_type == ActionType.VERIFY_FINDING:
                self._do_verify(state, action)
            elif action.action_type == ActionType.ASK_USER:
                self._do_ask_user(state, action)
                await self._registry.save(state)
                return state
            elif action.action_type == ActionType.WAIT_FOR_APPROVAL:
                state.phase = AgentPhase.WAITING_FOR_APPROVAL
                state.pending_action_id = action.id
                await self._registry.save(state)
                return state
            elif action.action_type in (ActionType.GENERATE_REPORT, ActionType.COMPLETE_TASK):
                self._do_complete(state, action)
                await self._registry.save(state)
                return state
        except _ActionFailure as failure:
            return await self._handle_failure(state, action, failure)

        action.completed_at = datetime.now(UTC)
        state.confidence = action.confidence
        self._emit(
            state, ACTION_OUTPUT, {"actionId": str(action.id), "summary": action.result_summary}
        )
        state.phase = _POST_ACTION_PHASE.get(action.action_type, AgentPhase.OBSERVING)
        await self._registry.save(state)
        return state

    # --- action implementations (each delegates to an existing service) -----

    async def _do_check_environment(self, state: AgentTaskState, action: AgentAction) -> None:
        env = self._environment.inspect()
        summary = (
            f"Platform {env.platform}, package managers: "
            f"{[m.value for m in env.available_package_managers]}."
        )
        state.observations.append(self._analyzer.observe(action_id=action.id, summary=summary))
        action.result_summary = summary

    def _do_discover_target(self, state: AgentTaskState, action: AgentAction) -> None:
        if not state.target:
            raise _ActionFailure(category="invalid_argument", message="No target is known yet.")
        summary = f"Target confirmed: {state.target} ({state.target_type or 'unknown type'})."
        state.observations.append(self._analyzer.observe(action_id=action.id, summary=summary))
        action.result_summary = summary

    async def _do_research_tool(self, state: AgentTaskState, action: AgentAction) -> None:
        capability = action.capability or ""
        candidates = await self._discovery.discover(capability)
        if not candidates:
            raise _ActionFailure(
                category="tool_unavailable", message=f"No candidates found for '{capability}'."
            )
        state.tool_capabilities[capability] = [c.name for c in candidates]
        summary = f"Found {len(candidates)} candidate(s) for '{capability}': " + ", ".join(
            c.name for c in candidates
        )
        state.observations.append(self._analyzer.observe(action_id=action.id, summary=summary))
        action.result_summary = summary

    async def _do_install_tool(
        self, state: AgentTaskState, action: AgentAction, *, target_scope, platform: str
    ) -> None:
        if not action.tool:
            raise _ActionFailure(category="invalid_argument", message="No tool name specified.")
        self._budget.check_installation_budget(state)
        tool = await self._tools.get_by_name(action.tool)
        if tool is None:
            raise _ActionFailure(
                category="tool_unavailable", message=f"Tool '{action.tool}' is not registered."
            )
        if target_scope is None:
            raise _ActionFailure(
                category="policy_restriction",
                message="No target scope available for installation.",
            )

        request = await self._installations.request_installation(
            tool.id, target_scope=target_scope, platform=platform, requested_by="agent"
        )
        if request.state.value == "BLOCKED":
            raise _ActionFailure(
                category="policy_restriction",
                message=request.error_message or "Installation blocked.",
            )
        if request.state.value == "WAITING_FOR_APPROVAL":
            request = await self._installations.approve(
                request.id, approved_by="agent(user-approved)"
            )

        session = self._terminal.create_session(task_id=f"agent-install-{state.id}")
        finished = await self._installations.start_installation(
            request.id, engine=self._terminal, session_id=session.id, target_scope=target_scope
        )
        state.installation_count += 1
        state.installation_state[tool.name] = finished.state.value

        if finished.state.value != "INSTALLED":
            raise _ActionFailure(
                category="tool_unavailable",
                message=finished.error_message or f"Installation ended in {finished.state.value}.",
            )

        state.selected_tools.append(tool.name)
        summary = f"Installed and verified '{tool.name}'."
        state.observations.append(self._analyzer.observe(action_id=action.id, summary=summary))
        action.result_summary = summary

    async def _do_run_diagnostic(
        self, state: AgentTaskState, action: AgentAction, *, target_scope
    ) -> None:
        if target_scope is None:
            raise _ActionFailure(
                category="policy_restriction", message="No target scope available for execution."
            )
        risk_tier = ACTION_RISK_TIERS.get(_DIAGNOSTIC_ACTION_TYPE)
        decision: PolicyDecision = self._policy_engine.evaluate(
            ActionRequest(
                action_id=uuid4(), action_type=_DIAGNOSTIC_ACTION_TYPE, risk_tier=risk_tier,
                target=target_scope,
            )
        )
        if decision.verdict == PolicyVerdict.DENY:
            raise _ActionFailure(category="policy_restriction", message="; ".join(decision.reasons))

        command = resolve_command(_DIAGNOSTIC_ACTION_TYPE)
        session = self._terminal.create_session(task_id=f"agent-diag-{state.id}")
        result = await self._terminal.execute(
            TerminalCommandRequest(
                session_id=session.id,
                command=command,
                authorization_context=decision,
                approved_by_user=decision.verdict == PolicyVerdict.ALLOW,
            )
        )
        if result.status != CommandStatus.COMPLETED:
            failure = self._classifier.classify(
                timed_out=result.status == CommandStatus.TIMEOUT,
                policy_denied=result.status == CommandStatus.REJECTED,
                exit_code=result.exit_code,
                stderr=result.stderr,
            )
            raise _ActionFailure(
                category=failure.value, message=result.error_message or "Diagnostic failed."
            )

        stdout_preview = result.stdout.strip() if result.stdout else "(no output)"
        summary = f"Diagnostic completed: {stdout_preview}"
        state.outputs.append(result.stdout or "")
        state.observations.append(self._analyzer.observe(action_id=action.id, summary=summary))
        action.result_summary = summary

    def _do_analyze(self, state: AgentTaskState, action: AgentAction) -> None:
        if not state.observations:
            raise _ActionFailure(category="unexpected_output", message="Nothing to analyze yet.")
        latest = state.observations[-1]
        finding = self._analyzer.propose_finding(
            action_id=action.id, summary=f"Based on: {latest.summary}"
        )
        state.findings.append(finding)
        state.evidence.append(finding)
        action.result_summary = finding.summary

    def _do_verify(self, state: AgentTaskState, action: AgentAction) -> None:
        pending = [f for f in state.findings if f.kind == EvidenceKind.FINDING]
        if not pending:
            raise _ActionFailure(category="unexpected_output", message="No finding to verify.")
        finding = pending[-1]
        corroboration = [o.summary for o in state.observations[-3:]]
        verified = self._verifier.verify(finding, corroborating_evidence=corroboration)
        state.findings = [verified if f.id == finding.id else f for f in state.findings]
        state.evidence.append(verified)
        state.verification_results[str(finding.id)] = verified.kind == EvidenceKind.VERIFIED_FINDING
        action.result_summary = verified.summary

    def _do_ask_user(self, state: AgentTaskState, action: AgentAction) -> None:
        state.clarification_question = action.expected_result
        state.phase = AgentPhase.WAITING_FOR_AUTHORIZATION
        action.result_summary = "Awaiting user clarification."

    def _do_complete(self, state: AgentTaskState, action: AgentAction) -> None:
        action.result_summary = "Task marked complete."
        action.completed_at = datetime.now(UTC)
        state.phase = AgentPhase.COMPLETED
        state.completed_at = datetime.now(UTC)
        self._emit(state, TASK_COMPLETED, {"report": self._reports.build(state)})

    async def _handle_failure(
        self, state: AgentTaskState, action: AgentAction, failure: "_ActionFailure"
    ) -> AgentTaskState:
        category_value = failure.category
        action.error_category = category_value
        action.result_summary = failure.message
        state.errors.append(
            AgentError(action_id=action.id, category=category_value, message=failure.message)
        )

        # Phase 13: if a SelfHealingEngine was injected, get a proposal
        # and stash the suggested strategy on the task's recovery
        # attempts. Never applied automatically — it's a hint for the
        # AdaptationEngine below (which still decides retry/ask/fail) and
        # for the operator UI.
        if self._self_healing is not None:
            try:
                from services.self_healing.diagnosis import FailureSignals

                proposal = self._self_healing.heal(
                    task_id=state.id,
                    action_id=action.id,
                    signals=FailureSignals(
                        stderr=failure.message,
                        error_category=category_value,
                        policy_denied=(category_value == "policy_restriction"),
                    ),
                )
                state.recovery_attempts.append(
                    RecoveryAttempt(
                        action_id=action.id,
                        error_category=category_value,
                        strategy=f"proposed:{proposal.strategy.kind.value}",
                    )
                )
            except Exception:  # noqa: BLE001 - self-healing is optional; never blocks recovery
                pass

        action_key = action.action_type.value
        decision = self._adaptation.decide(
            state, action_key=action_key, failure=_CategoryProxy(category_value)
        )
        signature = f"{action_key}:{category_value}"

        if decision.strategy == AdaptationStrategy.RETRY:
            state.retry_count_by_action[action_key] = (
                state.retry_count_by_action.get(action_key, 0) + 1
            )
            state.last_error_signature = signature
            state.recovery_attempts.append(
                RecoveryAttempt(
                    action_id=action.id, error_category=category_value, strategy="retry"
                )
            )
            self._emit(state, RECOVERY_STARTED, {"strategy": "retry", "reason": decision.reason})
            state.phase = AgentPhase.RECOVERING
            await self._registry.save(state)
            return state

        if decision.strategy == AdaptationStrategy.ASK_USER:
            state.recovery_attempts.append(
                RecoveryAttempt(
                    action_id=action.id, error_category=category_value, strategy="ask_user"
                )
            )
            state.clarification_question = decision.reason
            state.phase = AgentPhase.WAITING_FOR_AUTHORIZATION
            self._emit(state, RECOVERY_STARTED, {"strategy": "ask_user", "reason": decision.reason})
            await self._registry.save(state)
            return state

        state.phase = AgentPhase.FAILED
        state.completed_at = datetime.now(UTC)
        self._emit(state, TASK_FAILED, {"reason": decision.reason})
        await self._registry.save(state)
        return state


class _ActionFailure(RuntimeError):
    def __init__(self, *, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


class _CategoryProxy(str):
    """Lets `_ActionFailure.category` (a plain string) satisfy
    `AdaptationEngine.decide`'s `FailureClass` parameter without a lookup
    table — `.value` mirrors the enum's own attribute so both call
    patterns work identically."""

    @property
    def value(self) -> str:
        return str(self)
