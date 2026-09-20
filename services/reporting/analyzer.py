"""Result Analyzer + Report Engine interfaces.

Phase 1 defines the contracts consumed by the API's reports routes; no
analysis logic is implemented since there are no real executions yet to
analyze (see services/policy.engine — the action registry is empty)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from services.terminal.adapters.base import ExecutionResult


@dataclass
class Finding:
    title: str
    severity: str
    description: str
    evidence: dict


class ResultAnalyzer(ABC):
    @abstractmethod
    async def analyze(self, result: ExecutionResult) -> list[Finding]:
        """Turn a raw execution result into structured findings."""


class ReportEngine(ABC):
    @abstractmethod
    async def generate(self, findings: list[Finding]) -> str:
        """Render findings into a human-readable report (markdown)."""
