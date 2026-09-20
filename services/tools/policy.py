"""Tool eligibility pre-check — NOT the authorization system.

This module answers "is this tool even eligible to be considered for
installation/execution on this platform" (compatible platform, no
prohibited capability, acceptable trust status). It never authorizes an
actual execution — that remains exclusively `services.policy.engine.
PolicyEngine`, evaluated per-action against a real target scope at
execution time, exactly as for every other action type in this system.
Passing this gate changes nothing about what the terminal engine will
allow; it only decides whether the tool registry will let a tool reach
`TrustStatus.APPROVED` at all.
"""

from dataclasses import dataclass, field

from services.tools.models import ToolRecord, TrustStatus
from services.tools.verification import VerificationResult, VerificationStage

_PROHIBITED_CAPABILITY_MARKERS = (
    "credential_theft",
    "credential_dump",
    "persistence",
    "evasion",
    "exploit_auto",
    "av_bypass",
    "security_control_bypass",
)


@dataclass
class ToolEligibilityDecision:
    eligible: bool
    reasons: list[str] = field(default_factory=list)


class ToolPolicyGate:
    def evaluate(
        self, tool: ToolRecord, *, target_platform: str | None = None
    ) -> ToolEligibilityDecision:
        reasons: list[str] = []

        if tool.trust_status == TrustStatus.BLOCKED:
            reasons.append("Tool is explicitly BLOCKED.")
            return ToolEligibilityDecision(eligible=False, reasons=reasons)
        if tool.trust_status == TrustStatus.DEPRECATED:
            reasons.append("Tool is DEPRECATED.")
            return ToolEligibilityDecision(eligible=False, reasons=reasons)

        capability_text = " ".join(tool.capabilities).lower()
        prohibited = next((m for m in _PROHIBITED_CAPABILITY_MARKERS if m in capability_text), None)
        if prohibited:
            reasons.append(f"Declares prohibited capability marker '{prohibited}'.")
            return ToolEligibilityDecision(eligible=False, reasons=reasons)

        if target_platform is not None and target_platform not in tool.supported_platforms:
            reasons.append(
                f"Tool does not declare support for platform '{target_platform}' "
                f"(declares {list(tool.supported_platforms)})."
            )
            return ToolEligibilityDecision(eligible=False, reasons=reasons)

        security_review = tool.verification.results.get(VerificationStage.SECURITY_POLICY_REVIEW)
        if security_review == VerificationResult.FAILED:
            reasons.append("Security/policy review stage failed verification.")
            return ToolEligibilityDecision(eligible=False, reasons=reasons)

        if tool.trust_status != TrustStatus.APPROVED:
            reasons.append(
                f"Trust status is '{tool.trust_status.value}', not APPROVED — "
                "eligibility requires explicit approval, not merely verification."
            )
            return ToolEligibilityDecision(eligible=False, reasons=reasons)

        reasons.append(
            "Tool is APPROVED, platform-compatible, and declares no prohibited capability."
        )
        return ToolEligibilityDecision(eligible=True, reasons=reasons)
