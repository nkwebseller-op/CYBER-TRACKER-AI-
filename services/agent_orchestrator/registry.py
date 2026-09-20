"""AgentTaskState persistence abstraction — same split as every other
services/ registry (tools, installation, termux pairing): a
storage-independent Protocol plus an in-memory reference implementation.
apps/api backs this with the database (app/db/agent_repository.py) for
resumability across restarts; the orchestrator itself never assumes
in-process state survives beyond what this registry persists."""

from typing import Protocol
from uuid import UUID

from services.agent_orchestrator.errors import TaskNotFoundError
from services.agent_orchestrator.models import AgentTaskState


class AgentTaskRegistry(Protocol):
    async def create(self, state: AgentTaskState) -> AgentTaskState: ...
    async def get(self, task_id: UUID) -> AgentTaskState: ...
    async def save(self, state: AgentTaskState) -> AgentTaskState: ...
    async def list_all(self) -> list[AgentTaskState]: ...
    async def count_active(self) -> int: ...


class InMemoryAgentTaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[UUID, AgentTaskState] = {}

    async def create(self, state: AgentTaskState) -> AgentTaskState:
        self._tasks[state.id] = state
        return state

    async def get(self, task_id: UUID) -> AgentTaskState:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Agent task {task_id} was not found.")
        return task

    async def save(self, state: AgentTaskState) -> AgentTaskState:
        state.touch()
        self._tasks[state.id] = state
        return state

    async def list_all(self) -> list[AgentTaskState]:
        return list(self._tasks.values())

    async def count_active(self) -> int:
        return sum(1 for t in self._tasks.values() if not t.is_terminal())
