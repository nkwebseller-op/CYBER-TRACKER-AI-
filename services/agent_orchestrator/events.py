"""Agent event stream — integrates with the existing WebSocket hub
(apps/api/app/ws/gateway.py) rather than creating a second transport.
`AgentEventBus` is a storage-independent Protocol; apps/api's route layer
subscribes a broadcaster that forwards to `hub.broadcast`. Every event
emitted here corresponds to something that actually happened — nothing is
fabricated to make progress look smoother than it is."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

AGENT_STARTED = "AGENT_STARTED"
OBJECTIVE_PARSED = "OBJECTIVE_PARSED"
TARGET_IDENTIFIED = "TARGET_IDENTIFIED"
AUTHORIZATION_CHECK = "AUTHORIZATION_CHECK"
PLAN_CREATED = "PLAN_CREATED"
TOOL_SELECTED = "TOOL_SELECTED"
APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
APPROVAL_RECEIVED = "APPROVAL_RECEIVED"
ACTION_STARTED = "ACTION_STARTED"
ACTION_OUTPUT = "ACTION_OUTPUT"
ANALYSIS_STARTED = "ANALYSIS_STARTED"
FINDING_CREATED = "FINDING_CREATED"
RECOVERY_STARTED = "RECOVERY_STARTED"
VERIFICATION_STARTED = "VERIFICATION_STARTED"
TASK_PAUSED = "TASK_PAUSED"
TASK_RESUMED = "TASK_RESUMED"
TASK_COMPLETED = "TASK_COMPLETED"
TASK_FAILED = "TASK_FAILED"

ALL_EVENT_TYPES = frozenset(
    {
        AGENT_STARTED,
        OBJECTIVE_PARSED,
        TARGET_IDENTIFIED,
        AUTHORIZATION_CHECK,
        PLAN_CREATED,
        TOOL_SELECTED,
        APPROVAL_REQUIRED,
        APPROVAL_RECEIVED,
        ACTION_STARTED,
        ACTION_OUTPUT,
        ANALYSIS_STARTED,
        FINDING_CREATED,
        RECOVERY_STARTED,
        VERIFICATION_STARTED,
        TASK_PAUSED,
        TASK_RESUMED,
        TASK_COMPLETED,
        TASK_FAILED,
    }
)


@dataclass
class AgentEvent:
    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    event_type: str = AGENT_STARTED
    data: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AgentEventBus(Protocol):
    def publish(self, event: AgentEvent) -> None: ...
    def events_for(self, task_id: UUID) -> list[AgentEvent]: ...


class InMemoryAgentEventBus:
    def __init__(self) -> None:
        self._events: list[AgentEvent] = []

    def publish(self, event: AgentEvent) -> None:
        self._events.append(event)

    def events_for(self, task_id: UUID) -> list[AgentEvent]:
        return [e for e in self._events if e.task_id == task_id]
