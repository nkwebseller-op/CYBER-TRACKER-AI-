"""In-memory session lifecycle management.

Sessions are process-local for this phase — there is no cross-process or
cross-restart persistence yet (a later phase can back this with the
database without changing the SessionManager interface). What matters now
is that sessions are never unbounded: a configurable TTL expires idle
sessions and a configurable cap limits how many can exist at once.
"""

from datetime import UTC, datetime
from uuid import UUID

from services.terminal.audit import (
    SESSION_CLOSED,
    SESSION_CREATED,
    SESSION_EXPIRED,
    AuditEvent,
    AuditSink,
    LoggingAuditSink,
)
from services.terminal.config import TerminalEngineConfig
from services.terminal.errors import InvalidRequestError, SessionExpiredError, SessionNotFoundError
from services.terminal.models import SessionStatus, TerminalSession
from services.terminal.platform_types import PlatformIdentifier


class SessionManager:
    def __init__(
        self, config: TerminalEngineConfig, *, audit_sink: AuditSink | None = None
    ) -> None:
        self._config = config
        self._audit = audit_sink or LoggingAuditSink()
        self._sessions: dict[UUID, TerminalSession] = {}

    def _emit(self, event_type: str, session: TerminalSession, **data: object) -> None:
        self._audit.emit(
            AuditEvent(
                event_type=event_type,
                session_id=str(session.id),
                command_id=None,
                task_id=session.task_id,
                data={"status": session.status.value, "platform": session.platform.value, **data},
            )
        )

    def create_session(
        self,
        *,
        platform: PlatformIdentifier,
        task_id: str | None = None,
        working_directory: str | None = None,
    ) -> TerminalSession:
        self._reap_expired()

        if len(self._sessions) >= self._config.max_concurrent_sessions:
            raise InvalidRequestError(
                "Maximum concurrent terminal sessions reached "
                f"({self._config.max_concurrent_sessions})."
            )

        session = TerminalSession(
            platform=platform,
            task_id=task_id,
            working_directory=working_directory or self._config.workspace_root,
            status=SessionStatus.READY,
        )
        self._sessions[session.id] = session
        self._emit(SESSION_CREATED, session)
        return session

    def get_session(self, session_id: UUID) -> TerminalSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session {session_id} does not exist.")

        active_states = (SessionStatus.STOPPED, SessionStatus.FAILED, SessionStatus.EXPIRED)
        if session.status not in active_states and session.is_expired(
            ttl_seconds=self._config.session_ttl_seconds
        ):
            session.status = SessionStatus.EXPIRED
            self._emit(SESSION_EXPIRED, session)

        return session

    def require_active_session(self, session_id: UUID) -> TerminalSession:
        session = self.get_session(session_id)
        if session.status == SessionStatus.EXPIRED:
            raise SessionExpiredError(f"Session {session_id} has expired from inactivity.")
        if session.status not in (SessionStatus.READY, SessionStatus.RUNNING):
            raise SessionExpiredError(
                f"Session {session_id} is not active (status={session.status})."
            )
        return session

    def close_session(self, session_id: UUID) -> TerminalSession:
        session = self.get_session(session_id)
        session.status = SessionStatus.STOPPED
        session.touch()
        self._emit(SESSION_CLOSED, session)
        return session

    def _reap_expired(self) -> None:
        now = datetime.now(UTC)
        for session in self._sessions.values():
            if session.status in (
                SessionStatus.READY,
                SessionStatus.RUNNING,
            ) and session.is_expired(ttl_seconds=self._config.session_ttl_seconds, now=now):
                session.status = SessionStatus.EXPIRED
                self._emit(SESSION_EXPIRED, session)
