"""Test doubles for Agent Orchestrator tests — no real Gemini/network
access, per the phase's testing requirements."""

from services.agent.providers.base import (
    AIProvider,
    AIProviderError,
    CompletionResult,
    Message,
    ProviderHealth,
    ProviderHealthStatus,
    StructuredCompletionResult,
)
from services.policy.engine import RiskTier
from services.tools.models import (
    SourceProvenance,
    SourceType,
    ToolCategory,
    ToolRecord,
    TrustStatus,
)


class ScriptedProvider(AIProvider):
    """Returns pre-scripted decision payloads in order, one per call to
    `generate_structured`. Never calls a real model."""

    name = "scripted"

    def __init__(self, decisions: list[dict]) -> None:
        self._decisions = list(decisions)
        self.calls: list[list[Message]] = []

    async def complete(self, messages, *, temperature=0.2) -> CompletionResult:
        raise NotImplementedError

    async def stream(self, messages, *, temperature=0.2):
        raise NotImplementedError
        yield ""  # pragma: no cover

    async def generate_structured(
        self, messages: list[Message], *, schema: dict, temperature=0.2, max_output_tokens=None
    ) -> StructuredCompletionResult:
        self.calls.append(messages)
        if not self._decisions:
            raise AIProviderError("ScriptedProvider ran out of scripted decisions")
        return StructuredCompletionResult(
            data=self._decisions.pop(0), raw_text="", model="scripted-1", provider=self.name
        )

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, status=ProviderHealthStatus.CONNECTED)


class FailingProvider(AIProvider):
    name = "failing"

    async def complete(self, messages, *, temperature=0.2):
        raise NotImplementedError

    async def stream(self, messages, *, temperature=0.2):
        raise NotImplementedError
        yield ""  # pragma: no cover

    async def generate_structured(
        self, messages, *, schema, temperature=0.2, max_output_tokens=None
    ):
        raise AIProviderError("provider unavailable")

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, status=ProviderHealthStatus.UNAVAILABLE)


def decision(
    action_type: str,
    *,
    intent: str = "CONTINUE",
    requires_approval: bool = False,
    tool: str | None = None,
    required_capability: str | None = None,
    arguments: dict | None = None,
    confidence: float = 0.7,
) -> dict:
    return {
        "reasoningSummary": f"Proposing {action_type}.",
        "intent": intent,
        "nextAction": f"Do {action_type}",
        "actionType": action_type,
        "requiredCapability": required_capability,
        "tool": tool,
        "arguments": arguments or {},
        "requiresApproval": requires_approval,
        "missingInformation": [],
        "expectedEvidence": [],
        "verificationPlan": [],
        "confidence": confidence,
    }


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
