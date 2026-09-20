"""Tool Registry abstraction + in-memory reference implementation.

Same split as services/terminal/session_manager.py: the interface here is
storage-independent so apps/api can back it with the database (see
apps/api/app/db/tool_repository.py) while unit tests and local
development use `InMemoryToolRegistry` directly — no DB required to
exercise discovery/verification/policy logic.
"""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from services.tools.errors import DuplicateToolError, ToolNotFoundError
from services.tools.models import ToolCategory, ToolRecord, TrustStatus, VerificationReport


class ToolRegistry(Protocol):
    async def create(self, tool: ToolRecord) -> ToolRecord: ...
    async def get(self, tool_id: UUID) -> ToolRecord: ...
    async def get_by_name(self, name: str) -> ToolRecord | None: ...
    async def list(
        self,
        *,
        category: ToolCategory | None = None,
        platform: str | None = None,
        trust_status: TrustStatus | None = None,
        search: str | None = None,
    ) -> list[ToolRecord]: ...
    async def update_trust_status(self, tool_id: UUID, status: TrustStatus) -> ToolRecord: ...
    async def record_verification(
        self, tool_id: UUID, report: VerificationReport
    ) -> ToolRecord: ...


class InMemoryToolRegistry:
    """Reference implementation used by default in services-level tests
    and available to the API as a dependency override — the same role
    TerminalEngine's in-memory SessionManager plays for terminal sessions."""

    def __init__(self) -> None:
        self._tools: dict[UUID, ToolRecord] = {}

    async def create(self, tool: ToolRecord) -> ToolRecord:
        if await self.get_by_name(tool.name) is not None:
            raise DuplicateToolError(f"A tool named '{tool.name}' is already registered.")
        self._tools[tool.id] = tool
        return tool

    async def get(self, tool_id: UUID) -> ToolRecord:
        tool = self._tools.get(tool_id)
        if tool is None:
            raise ToolNotFoundError(f"Tool {tool_id} was not found.")
        return tool

    async def get_by_name(self, name: str) -> ToolRecord | None:
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None

    async def list(
        self,
        *,
        category: ToolCategory | None = None,
        platform: str | None = None,
        trust_status: TrustStatus | None = None,
        search: str | None = None,
    ) -> list[ToolRecord]:
        results = list(self._tools.values())
        if category is not None:
            results = [t for t in results if t.category == category]
        if platform is not None:
            results = [t for t in results if platform in t.supported_platforms]
        if trust_status is not None:
            results = [t for t in results if t.trust_status == trust_status]
        if search:
            needle = search.lower()
            results = [
                t
                for t in results
                if needle in t.name.lower()
                or needle in t.display_name.lower()
                or needle in t.description.lower()
                or any(needle in c.lower() for c in t.capabilities)
            ]
        return results

    async def update_trust_status(self, tool_id: UUID, status: TrustStatus) -> ToolRecord:
        tool = await self.get(tool_id)
        tool.trust_status = status
        tool.updated_at = datetime.now(UTC)
        return tool

    async def record_verification(self, tool_id: UUID, report: VerificationReport) -> ToolRecord:
        tool = await self.get(tool_id)
        tool.verification = report
        tool.updated_at = datetime.now(UTC)
        return tool
