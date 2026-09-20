"""Core state models for the autonomous Agent Orchestrator.

Framework/database-independent dataclasses — same split as every other
services/ package (terminal, tools, installation, termux). Nothing here
is directly executable: a `StructuredAction` carries an `ActionType` and
plain-data `parameters`, never a shell string or raw argv. Turning one
into a real effect always goes through the existing, unmodified
TerminalEngine / PolicyEngine / ToolRegistry / ToolInstallationService —
see services/agent_orchestrator/orchestrator.py.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from services.agent_orchestrator.actions import ActionType

__all__ = [
    "AgentPhase",
    "ApprovalState",
    "CancellationState",
    "EvidenceKind",
    "Evidence",
    "AgentAction",
    "AgentError",
    "RecoveryAttempt",
    "Subtask",
    "SubtaskStatus",
    "AgentTaskState",
]


class AgentPhase(StrEnum):
    CREATED = "CREATED"
    UNDERSTANDING = "UNDERSTANDING"
    RESEARCHING = "RESEARCHING"
    PLANNING = "PLANNING"
    WAITING_FOR_AUTHORIZATION = "WAITING_FOR_AUTHORIZATION"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    PREPARING = "PREPARING"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    ANALYZING = "ANALYZING"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


_TERMINAL_PHASES = frozenset(
    {AgentPhase.CANCELLED, AgentPhase.COMPLETED, AgentPhase.FAILED, AgentPhase.BLOCKED}
)


class ApprovalState(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CancellationState(StrEnum):
    NONE = "NONE"
    REQUESTED = "REQUESTED"
    CANCELLED = "CANCELLED"


class SubtaskStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class EvidenceKind(StrEnum):
    """Never let an ASSUMPTION or OBSERVATION silently become a FACT —
    see services/agent_orchestrator/analysis.py."""

    FACT = "FACT"
    OBSERVATION = "OBSERVATION"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"
    FINDING = "FINDING"
    VERIFIED_FINDING = "VERIFIED_FINDING"


@dataclass
class Evidence:
    id: UUID = field(default_factory=uuid4)
    kind: EvidenceKind = EvidenceKind.OBSERVATION
    summary: str = ""
    source_action_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Subtask:
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    category: str = ""
    status: SubtaskStatus = SubtaskStatus.PENDING
    depends_on: tuple[UUID, ...] = ()


@dataclass
class AgentAction:
    id: UUID = field(default_factory=uuid4)
    action_type: ActionType = ActionType.COLLECT_INFORMATION
    target: str | None = None
    capability: str | None = None
    tool: str | None = None
    parameters: dict = field(default_factory=dict)
    requires_approval: bool = False
    approval_state: ApprovalState = ApprovalState.NOT_REQUIRED
    expected_result: str = ""
    verification_requirement: str = ""
    reasoning_summary: str = ""
    confidence: float = 0.0
    result_summary: str | None = None
    error_category: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


@dataclass
class AgentError:
    id: UUID = field(default_factory=uuid4)
    action_id: UUID | None = None
    category: str = "unknown"
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class RecoveryAttempt:
    action_id: UUID
    error_category: str
    strategy: str
    id: UUID = field(default_factory=uuid4)
    outcome: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AgentTaskState:
    id: UUID = field(default_factory=uuid4)
    objective: str = ""
    user_request: str = ""
    target: str | None = None
    target_type: str | None = None
    authorization_status: str = "UNKNOWN"
    target_id: UUID | None = None
    scope: list[str] = field(default_factory=list)

    phase: AgentPhase = AgentPhase.CREATED
    current_subtask_id: UUID | None = None
    subtasks: list[Subtask] = field(default_factory=list)

    selected_tools: list[str] = field(default_factory=list)
    tool_capabilities: dict[str, list[str]] = field(default_factory=dict)
    installation_state: dict[str, str] = field(default_factory=dict)
    execution_state: str = "idle"

    actions: list[AgentAction] = field(default_factory=list)
    observations: list[Evidence] = field(default_factory=list)
    findings: list[Evidence] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)

    errors: list[AgentError] = field(default_factory=list)
    recovery_attempts: list[RecoveryAttempt] = field(default_factory=list)
    verification_results: dict[str, bool] = field(default_factory=dict)

    confidence: float = 0.0
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    next_action: str | None = None

    approval_state: ApprovalState = ApprovalState.NOT_REQUIRED
    pending_action_id: UUID | None = None
    cancellation_state: CancellationState = CancellationState.NONE
    clarification_question: str | None = None

    action_count: int = 0
    model_call_count: int = 0
    installation_count: int = 0
    retry_count_by_action: dict[str, int] = field(default_factory=dict)
    last_error_signature: str | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    def is_terminal(self) -> bool:
        return self.phase in _TERMINAL_PHASES

    def completed_subtasks(self) -> list[Subtask]:
        return [s for s in self.subtasks if s.status == SubtaskStatus.COMPLETED]

    def pending_subtasks(self) -> list[Subtask]:
        return [s for s in self.subtasks if s.status == SubtaskStatus.PENDING]

    def blocked_subtasks(self) -> list[Subtask]:
        return [s for s in self.subtasks if s.status == SubtaskStatus.BLOCKED]
