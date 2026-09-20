"""Policy / Authorization Engine.

This is the single gate between any proposed action and execution. It is
intentionally the only module allowed to construct an `ApprovedExecution`
(see services/terminal/controller.py) — the terminal adapters' `execute()`
refuses anything else at the type level.

Phase 1 ships the decision model and a conservative rule set:
  - DENY if the target has no active, non-expired authorization record.
  - DENY if the action type is not in the (currently empty) registry of
    recognized, reviewed action types — i.e. nothing is allowed by default.
  - REQUIRE_APPROVAL for medium/high/critical risk actions even when in
    scope.
  - ALLOW only for low-risk, in-scope, registered actions.

The action-type registry is populated by services/tools in a later phase.
Until then every action falls through to DENY, which is correct: there are
no reviewed, executable action types yet.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class PolicyVerdict(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class RiskTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TargetScope:
    id: UUID
    is_active: bool
    expires_at: datetime | None

    def is_authorized_now(self, *, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        if not self.is_active:
            return False
        if self.expires_at is not None and self.expires_at <= now:
            return False
        return True


@dataclass
class ActionRequest:
    action_id: UUID
    action_type: str
    risk_tier: RiskTier
    target: TargetScope


@dataclass
class PolicyDecision:
    verdict: PolicyVerdict
    reasons: list[str] = field(default_factory=list)
    requires_approval: bool = False


# Registry of action types reviewed and approved for execution. Empty by
# design in Phase 1 — see module docstring.
REGISTERED_ACTION_TYPES: frozenset[str] = frozenset()


class PolicyEngine:
    def evaluate(self, request: ActionRequest) -> PolicyDecision:
        reasons: list[str] = []

        if not request.target.is_authorized_now():
            reasons.append("Target has no active, non-expired authorization.")
            return PolicyDecision(verdict=PolicyVerdict.DENY, reasons=reasons)

        if request.action_type not in REGISTERED_ACTION_TYPES:
            reasons.append(
                f"Action type '{request.action_type}' is not in the reviewed action registry."
            )
            return PolicyDecision(verdict=PolicyVerdict.DENY, reasons=reasons)

        if request.risk_tier in (RiskTier.MEDIUM, RiskTier.HIGH, RiskTier.CRITICAL):
            reasons.append(f"Risk tier '{request.risk_tier}' requires explicit human approval.")
            return PolicyDecision(
                verdict=PolicyVerdict.REQUIRE_APPROVAL, reasons=reasons, requires_approval=True
            )

        reasons.append("Target authorized and action type registered at low risk.")
        return PolicyDecision(verdict=PolicyVerdict.ALLOW, reasons=reasons)
