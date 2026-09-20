"""Research Engine interface: given a security domain + objective, find
candidate tools/techniques (via services.tools.registry and, later, external
sources). Phase 1 ships the interface only; no external research sources
are wired up yet."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from services.tools.registry import ToolSpec


@dataclass
class ResearchQuery:
    domain: str
    objective: str


class ResearchEngine(ABC):
    @abstractmethod
    async def find_candidates(self, query: ResearchQuery) -> list[ToolSpec]:
        """Return candidate tools for the given domain/objective."""


class RegistryOnlyResearchEngine(ResearchEngine):
    """Phase 1 implementation: searches only the local, vetted tool
    registry. No network calls, no unvetted sources."""

    async def find_candidates(self, query: ResearchQuery) -> list[ToolSpec]:
        from services.tools.registry import TOOL_REGISTRY

        return [tool for tool in TOOL_REGISTRY.values() if query.domain in tool.domains]
