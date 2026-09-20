"""Installation readiness checklist.

Runs the eleven checks the phase spec requires *before* any install plan
is even generated. Any critical check that comes back FAIL or UNKNOWN
means `ready=False` — installation must never proceed on an assumption.
"""

from dataclasses import dataclass, field
from uuid import UUID

from services.policy.engine import (
    ActionRequest,
    PolicyDecision,
    PolicyEngine,
    PolicyVerdict,
    TargetScope,
)
from services.terminal.command_templates import INSTALL_ACTION_TYPE
from services.tools.errors import ToolRegistryError
from services.tools.models import SourceType, ToolRecord, TrustStatus
from services.tools.registry import ToolRegistry


class CheckStatus:
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: str
    detail: str
    critical: bool = True


@dataclass
class ReadinessReport:
    tool: ToolRecord | None
    checks: list[ReadinessCheck] = field(default_factory=list)
    policy_decision: PolicyDecision | None = None

    @property
    def ready(self) -> bool:
        if self.tool is None:
            return False
        if self.policy_decision is not None and self.policy_decision.verdict == PolicyVerdict.DENY:
            return False
        return all(c.status == CheckStatus.PASS for c in self.checks if c.critical)


class ReadinessChecker:
    def __init__(self, *, policy_engine: PolicyEngine | None = None) -> None:
        self._policy_engine = policy_engine or PolicyEngine()

    async def check(
        self, registry: ToolRegistry, tool_id: UUID, *, target_scope: TargetScope, platform: str
    ) -> ReadinessReport:
        try:
            tool = await registry.get(tool_id)
        except ToolRegistryError:
            return ReadinessReport(
                tool=None,
                checks=[
                    ReadinessCheck(
                        "tool_exists", CheckStatus.FAIL, "Tool was not found in the registry."
                    )
                ],
            )

        checks = [self._exists_check(), self._provenance_check(tool), self._source_check(tool)]
        checks.append(self._platform_check(tool, platform))
        checks.append(self._license_check(tool))
        checks.append(self._dependency_check(tool))
        checks.append(self._permissions_check(tool))
        checks.append(self._risk_check(tool))
        checks.append(self._trust_check(tool))

        decision = self._policy_engine.evaluate(
            ActionRequest(
                action_id=tool.id,
                action_type=INSTALL_ACTION_TYPE,
                risk_tier=tool.risk_level,
                target=target_scope,
            )
        )
        checks.append(self._policy_check(decision))
        checks.append(self._authorization_check(target_scope))

        return ReadinessReport(tool=tool, checks=checks, policy_decision=decision)

    @staticmethod
    def _exists_check() -> ReadinessCheck:
        return ReadinessCheck("tool_exists", CheckStatus.PASS, "Tool exists in the registry.")

    @staticmethod
    def _provenance_check(tool: ToolRecord) -> ReadinessCheck:
        known = tool.provenance.source_type != SourceType.UNKNOWN
        return ReadinessCheck(
            "provenance_known",
            CheckStatus.PASS if known else CheckStatus.UNKNOWN,
            f"Source type is '{tool.provenance.source_type.value}'.",
        )

    @staticmethod
    def _source_check(tool: ToolRecord) -> ReadinessCheck:
        trusted = tool.provenance.source_type in {
            SourceType.OFFICIAL_WEBSITE,
            SourceType.OFFICIAL_GITHUB,
            SourceType.OFFICIAL_PACKAGE_REGISTRY,
        }
        return ReadinessCheck(
            "source_trusted",
            CheckStatus.PASS if trusted else CheckStatus.FAIL,
            "Source is an official first-party source."
            if trusted
            else f"Source type '{tool.provenance.source_type.value}' is not trusted enough "
            "for installation.",
        )

    @staticmethod
    def _platform_check(tool: ToolRecord, platform: str) -> ReadinessCheck:
        supported = platform in tool.supported_platforms
        return ReadinessCheck(
            "platform_supported",
            CheckStatus.PASS if supported else CheckStatus.FAIL,
            f"Tool declares support for {list(tool.supported_platforms)}; target is '{platform}'.",
        )

    @staticmethod
    def _license_check(tool: ToolRecord) -> ReadinessCheck:
        known = bool(tool.license)
        return ReadinessCheck(
            "license_known",
            CheckStatus.PASS if known else CheckStatus.UNKNOWN,
            f"License: {tool.license}" if known else "No license information on record.",
            critical=False,
        )

    @staticmethod
    def _dependency_check(tool: ToolRecord) -> ReadinessCheck:
        return ReadinessCheck(
            "dependencies_understood",
            CheckStatus.PASS,
            f"Declares {len(tool.dependencies)} dependency(ies): {list(tool.dependencies)}.",
            critical=False,
        )

    @staticmethod
    def _permissions_check(tool: ToolRecord) -> ReadinessCheck:
        return ReadinessCheck(
            "permissions_known",
            CheckStatus.PASS,
            f"Declares {len(tool.required_permissions)} required permission(s): "
            f"{list(tool.required_permissions)}.",
            critical=False,
        )

    @staticmethod
    def _risk_check(tool: ToolRecord) -> ReadinessCheck:
        return ReadinessCheck(
            "risk_evaluated", CheckStatus.PASS, f"Risk level: {tool.risk_level.value}."
        )

    @staticmethod
    def _trust_check(tool: ToolRecord) -> ReadinessCheck:
        approved = tool.trust_status == TrustStatus.APPROVED
        return ReadinessCheck(
            "trust_approved",
            CheckStatus.PASS if approved else CheckStatus.FAIL,
            f"Trust status is '{tool.trust_status.value}'"
            + ("" if approved else " (must be APPROVED before installation)."),
        )

    @staticmethod
    def _policy_check(decision: PolicyDecision) -> ReadinessCheck:
        if decision.verdict == PolicyVerdict.DENY:
            status = CheckStatus.FAIL
        else:
            status = CheckStatus.PASS
        return ReadinessCheck(
            "policy_allows", status, f"Policy verdict: {decision.verdict.value}."
        )

    @staticmethod
    def _authorization_check(target_scope: TargetScope) -> ReadinessCheck:
        authorized = target_scope.is_authorized_now()
        return ReadinessCheck(
            "target_authorized",
            CheckStatus.PASS if authorized else CheckStatus.FAIL,
            "Target has active, non-expired authorization."
            if authorized
            else "Target is inactive or its authorization has expired.",
        )
