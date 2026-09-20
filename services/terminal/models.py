"""Core data models for the Terminal Engine: sessions, command requests,
and command results. These are the shapes every future UI, agent,
reporting, and audit consumer should use — nothing platform-specific
leaks into them.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from services.policy.engine import PolicyDecision
from services.terminal.platform_types import PlatformIdentifier

# The Terminal Engine never decides authorization itself — it only ever
# acts on a PolicyDecision produced by services.policy.engine.PolicyEngine.
# See services/terminal/engine.py for how ALLOW / REQUIRE_APPROVAL / DENY
# are enforced before a process is ever created.
AuthorizationContext = PolicyDecision


class SessionStatus(StrEnum):
    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class CommandStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class TerminalSession:
    id: UUID = field(default_factory=uuid4)
    platform: PlatformIdentifier = PlatformIdentifier.UNKNOWN
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: SessionStatus = SessionStatus.CREATED
    working_directory: str | None = None
    task_id: str | None = None
    authorization_context: AuthorizationContext | None = None
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        self.last_activity_at = datetime.now(UTC)

    def is_expired(self, *, ttl_seconds: int, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        age = (now - self.last_activity_at).total_seconds()
        return age > ttl_seconds


@dataclass
class TerminalCommandRequest:
    """A structured execution request. Every field is validated before a
    process is created — see services/terminal/engine.py. `command` is
    never raw shell text typed by a user or produced verbatim by the AI —
    it is argv built from a vetted command template once an action type
    has been ALLOWed (see services/terminal/command_templates.py)."""

    session_id: UUID
    command: list[str]
    authorization_context: AuthorizationContext
    task_id: str | None = None
    id: UUID = field(default_factory=uuid4)
    working_directory: str | None = None
    environment: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int | None = None
    approved_by_user: bool = False


@dataclass
class TerminalCommandResult:
    command_id: UUID
    session_id: UUID
    status: CommandStatus
    platform: PlatformIdentifier
    started_at: datetime
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    completed_at: datetime | None = None
    error_message: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()
