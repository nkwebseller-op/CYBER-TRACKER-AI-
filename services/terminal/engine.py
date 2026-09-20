"""TerminalEngine: the platform-independent core of the Terminal Engine.

    AI / Task Planner
          |
    Policy / Authorization Layer          (services/policy/engine.py)
          |
    TerminalCommandRequest                (services/terminal/models.py)
          |
    TerminalEngine (this file)
          |
    Platform Adapter                      (services/terminal/adapters/*)
          |
    Controlled Process
          |
    Output Collector -> Result -> Audit Log

`execute()` never runs a process without a `PolicyDecision` attached to
the request, and that decision is never produced by this engine — it must
come from `services.policy.engine.PolicyEngine`, upstream of this module.
A DENY, an un-approved REQUIRE_APPROVAL, or a missing decision all result
in a REJECTED result with nothing ever reaching the OS.
"""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from services.terminal.adapters.base import CommandSpec, ExecutionStatus, TerminalAdapter
from services.terminal.audit import (
    COMMAND_APPROVED,
    COMMAND_CANCELLED,
    COMMAND_COMPLETED,
    COMMAND_FAILED,
    COMMAND_REJECTED,
    COMMAND_REQUESTED,
    COMMAND_STARTED,
    COMMAND_TIMEOUT,
    AuditEvent,
    AuditSink,
    LoggingAuditSink,
    truncate_for_log,
)
from services.terminal.config import TerminalEngineConfig
from services.terminal.controller import ApprovedExecution, ExecutionNotApprovedError
from services.terminal.errors import TerminalEngineError
from services.terminal.models import (
    CommandStatus,
    SessionStatus,
    TerminalCommandRequest,
    TerminalCommandResult,
    TerminalSession,
)
from services.terminal.platform_select import select_adapter
from services.terminal.platform_types import PlatformIdentifier, platform_for_adapter_name
from services.terminal.session_manager import SessionManager
from services.terminal.validation import (
    filter_environment,
    validate_argv,
    validate_working_directory,
)


class TerminalEngine:
    def __init__(
        self,
        *,
        config: TerminalEngineConfig | None = None,
        adapter: TerminalAdapter | None = None,
        session_manager: SessionManager | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._config = config or TerminalEngineConfig()
        self._audit = audit_sink or LoggingAuditSink()
        self._sessions = session_manager or SessionManager(self._config, audit_sink=self._audit)
        self._adapter_override = adapter
        self._running: dict[UUID, asyncio.Task] = {}
        # Most recent result per session — a minimal placeholder for
        # GET /api/terminal/sessions/{id}/output until a later phase backs
        # command history with real persistence.
        self._last_result_by_session: dict[UUID, TerminalCommandResult] = {}

    def get_last_result(self, session_id: UUID) -> TerminalCommandResult | None:
        return self._last_result_by_session.get(session_id)

    # --- session lifecycle -------------------------------------------------

    def create_session(
        self, *, task_id: str | None = None, working_directory: str | None = None
    ) -> TerminalSession:
        adapter = self._resolve_adapter()
        platform = self._platform_of(adapter)
        session = self._sessions.create_session(
            platform=platform, task_id=task_id, working_directory=working_directory
        )
        # In addition to the generic terminal.session.created event
        # (emitted by SessionManager) — platform adapters that define their
        # own event namespace (see adapters/windows.py, adapters/linux.py)
        # get a second, platform-specific event. Imported locally so the
        # platform-independent engine doesn't take a module-level
        # dependency on any specific adapter.
        platform_session_event = {
            PlatformIdentifier.WINDOWS: self._windows_session_created_event,
            PlatformIdentifier.LINUX: self._linux_session_created_event,
        }.get(platform)
        if platform_session_event is not None:
            self._audit.emit(
                AuditEvent(
                    event_type=platform_session_event(),
                    session_id=str(session.id),
                    command_id=None,
                    task_id=task_id,
                )
            )
        return session

    @staticmethod
    def _windows_session_created_event() -> str:
        from services.terminal.adapters.windows import WINDOWS_SESSION_CREATED

        return WINDOWS_SESSION_CREATED

    @staticmethod
    def _linux_session_created_event() -> str:
        from services.terminal.adapters.linux import LINUX_SESSION_CREATED

        return LINUX_SESSION_CREATED

    def get_status(self, session_id: UUID) -> TerminalSession:
        return self._sessions.get_session(session_id)

    def describe_adapter(self) -> dict:
        """Platform-independent capability summary for the currently
        selected adapter — used by the API to tell the frontend e.g.
        "shell: POWERSHELL" without the route layer depending on any
        specific adapter class. Adapters that don't expose
        `get_capabilities()` (Linux/macOS/Termux, unchanged from Phase 5)
        just report their platform with `shell=None`."""
        adapter = self._resolve_adapter()
        platform = self._platform_of(adapter)
        get_capabilities = getattr(adapter, "get_capabilities", None)
        if get_capabilities is None:
            return {"platform": platform, "shell": None}
        capabilities = get_capabilities()
        return {"platform": platform, "shell": capabilities.shell}

    def close_session(self, session_id: UUID) -> TerminalSession:
        return self._sessions.close_session(session_id)

    # --- execution -----------------------------------------------------------

    async def execute(self, request: TerminalCommandRequest) -> TerminalCommandResult:
        result = await self._execute(request)
        self._last_result_by_session[request.session_id] = result
        return result

    async def _execute(self, request: TerminalCommandRequest) -> TerminalCommandResult:
        session = self._sessions.require_active_session(request.session_id)
        session.touch()

        self._emit(COMMAND_REQUESTED, request, data={"argv_length": len(request.command)})

        started_at = datetime.now(UTC)

        try:
            validate_argv(request.command)
            working_dir = validate_working_directory(
                request.working_directory, workspace_root=self._config.workspace_root
            )
            timeout = self._config.clamp_timeout(request.timeout_seconds)
            safe_env = filter_environment(request.environment)
        except TerminalEngineError as exc:
            return self._rejected_result(request, started_at, str(exc))

        spec = CommandSpec(
            argv=request.command,
            timeout_seconds=timeout,
            working_dir=working_dir,
            env_overrides=safe_env,
            env_allowlist=self._config.env_allowlist,
            max_stdout_bytes=self._config.max_stdout_bytes,
            max_stderr_bytes=self._config.max_stderr_bytes,
        )

        try:
            approved = ApprovedExecution.from_policy_decision(
                action_id=request.id,
                command=spec,
                decision=request.authorization_context,
                approved_by_user=request.approved_by_user,
            )
        except ExecutionNotApprovedError as exc:
            self._emit(COMMAND_REJECTED, request, data={"reason": str(exc)})
            return self._rejected_result(request, started_at, str(exc))

        self._emit(COMMAND_APPROVED, request)

        adapter = self._resolve_adapter()
        session.status = SessionStatus.RUNNING
        run_context = {
            "session_id": str(request.session_id),
            "command_id": str(request.id),
            "task_id": request.task_id,
        }
        task = asyncio.ensure_future(
            adapter.run(approved.command, audit=self._audit, context=run_context)
        )
        self._running[request.id] = task
        self._emit(COMMAND_STARTED, request)

        try:
            result = await task
        except asyncio.CancelledError:
            self._emit(COMMAND_CANCELLED, request)
            return TerminalCommandResult(
                command_id=request.id,
                session_id=request.session_id,
                status=CommandStatus.CANCELLED,
                platform=self._platform_of(adapter),
                started_at=started_at,
                completed_at=datetime.now(UTC),
                error_message="Execution was cancelled.",
            )
        finally:
            self._running.pop(request.id, None)
            session.touch()
            if session.status == SessionStatus.RUNNING:
                session.status = SessionStatus.READY

        return self._finalize_result(request, adapter, started_at, result)

    async def terminate(self, command_id: UUID) -> bool:
        task = self._running.get(command_id)
        if task is None:
            return False
        task.cancel()
        return True

    def stream_output(self, command_id: UUID):
        """Abstraction for future live output streaming. Adapters in this
        phase return output only once a command completes, so there is
        nothing to stream yet — a real streaming adapter will publish
        `terminal.stdout` / `terminal.stderr` audit events as it produces
        output, and a consumer of this method will receive them here
        instead. Not implemented as a fake, delayed replay of buffered
        output — see docs/ARCHITECTURE.md for why that would misrepresent
        real streaming."""
        raise NotImplementedError(
            "Live output streaming requires a streaming-capable platform adapter, "
            "which is not implemented in this phase."
        )

    # --- internals -------------------------------------------------------

    def _resolve_adapter(self) -> TerminalAdapter:
        if self._adapter_override:
            return self._adapter_override
        return select_adapter(
            windows_powershell_path=self._config.windows_powershell_path,
            linux_shell_path=self._config.linux_shell_path,
        )

    @staticmethod
    def _platform_of(adapter: TerminalAdapter) -> PlatformIdentifier:
        return platform_for_adapter_name(adapter.name)

    def _rejected_result(
        self, request: TerminalCommandRequest, started_at: datetime, reason: str
    ) -> TerminalCommandResult:
        return TerminalCommandResult(
            command_id=request.id,
            session_id=request.session_id,
            status=CommandStatus.REJECTED,
            platform=self._platform_of(self._resolve_adapter()),
            started_at=started_at,
            completed_at=datetime.now(UTC),
            error_message=reason,
        )

    def _finalize_result(self, request, adapter, started_at, result) -> TerminalCommandResult:
        completed_at = result.finished_at or datetime.now(UTC)

        if result.timed_out:
            status = CommandStatus.TIMEOUT
        elif result.status == ExecutionStatus.SUCCEEDED:
            status = CommandStatus.COMPLETED
        else:
            status = CommandStatus.FAILED

        event_type = {
            CommandStatus.COMPLETED: COMMAND_COMPLETED,
            CommandStatus.TIMEOUT: COMMAND_TIMEOUT,
        }.get(status, COMMAND_FAILED)
        self._emit(
            event_type,
            request,
            data={
                "exit_code": result.exit_code,
                "stdout_preview": truncate_for_log(result.stdout),
                "stderr_preview": truncate_for_log(result.stderr),
                "stdout_truncated": result.stdout_truncated,
                "stderr_truncated": result.stderr_truncated,
            },
        )

        return TerminalCommandResult(
            command_id=request.id,
            session_id=request.session_id,
            status=status,
            platform=self._platform_of(adapter),
            started_at=started_at,
            completed_at=completed_at,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            stdout_truncated=result.stdout_truncated,
            stderr_truncated=result.stderr_truncated,
        )

    def _emit(
        self, event_type: str, request: TerminalCommandRequest, *, data: dict | None = None
    ) -> None:
        self._audit.emit(
            AuditEvent(
                event_type=event_type,
                session_id=str(request.session_id),
                command_id=str(request.id),
                task_id=request.task_id,
                data=data or {},
            )
        )
