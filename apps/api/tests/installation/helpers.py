"""Test doubles for Tool Installation tests — no real package manager or
network access, per the phase's testing requirements."""

from services.policy.engine import RiskTier
from services.terminal.adapters.base import (
    CommandSpec,
    ExecutionResult,
    ExecutionStatus,
    TerminalAdapter,
)
from services.tools.models import (
    SourceProvenance,
    SourceType,
    ToolCategory,
    ToolRecord,
    TrustStatus,
)


class ScriptedAdapter(TerminalAdapter):
    """Returns pre-scripted ExecutionResults in order, one per call to
    `run()`. Never touches a real process or package manager."""

    name = "scripted"

    def __init__(self, results: list[ExecutionResult]) -> None:
        self._results = list(results)
        self.calls: list[CommandSpec] = []

    async def run(self, command: CommandSpec, *, audit=None, context=None) -> ExecutionResult:
        self.calls.append(command)
        if not self._results:
            raise AssertionError("ScriptedAdapter ran out of scripted results")
        return self._results.pop(0)


def success_result(stdout: str = "ok", exit_code: int = 0) -> ExecutionResult:
    return ExecutionResult(
        adapter="scripted", status=ExecutionStatus.SUCCEEDED, exit_code=exit_code, stdout=stdout
    )


def failure_result(stderr: str = "boom", exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        adapter="scripted", status=ExecutionStatus.FAILED, exit_code=exit_code, stderr=stderr
    )


def approved_tool(**overrides) -> ToolRecord:
    defaults = dict(
        name="dig",
        display_name="dig",
        description="DNS lookup tool",
        category=ToolCategory.DNS_DOMAIN_ANALYSIS,
        capabilities=("dns_lookup",),
        supported_platforms=("LINUX", "MACOS"),
        provenance=SourceProvenance(
            source_type=SourceType.OFFICIAL_WEBSITE, source_url="https://isc.org"
        ),
        version="9.18",
        license="MPL-2.0",
        risk_level=RiskTier.MEDIUM,
        trust_status=TrustStatus.APPROVED,
    )
    defaults.update(overrides)
    return ToolRecord(**defaults)
