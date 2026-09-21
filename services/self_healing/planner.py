"""HealingPlanner: proposes a `HealingStrategy` for a given `Diagnosis`.

The mapping is a lookup table, not a model call — deterministic, easy to
audit, and impossible to jailbreak into proposing something outside
`HealingStrategyKind`. Every strategy that would touch the OS is marked
`requires_policy_recheck=True`; every strategy above a minimum risk bar
is marked `requires_user_approval=True`.
"""

from dataclasses import dataclass

from services.self_healing.models import (
    Diagnosis,
    DiagnosisConfidence,
    HealingStrategy,
    HealingStrategyKind,
)


@dataclass(frozen=True)
class HealingPlannerConfig:
    max_retries: int = 2
    backoff_base_seconds: float = 1.0
    max_timeout_multiplier: float = 4.0


class HealingPlanner:
    def __init__(self, config: HealingPlannerConfig | None = None) -> None:
        self._config = config or HealingPlannerConfig()

    def propose(
        self, diagnosis: Diagnosis, *, retries_used: int, prior_categories: list[str] | None = None
    ) -> HealingStrategy:
        prior = prior_categories or []
        # Loop detection: same category twice in a row -> abandon rather
        # than keep proposing the same futile fix.
        repeated_category = (
            prior
            and prior[-1] == diagnosis.error_category
            and diagnosis.error_category != "timeout"
        )
        if repeated_category:
            return HealingStrategy(
                kind=HealingStrategyKind.ABANDON,
                description=(
                    f"Category '{diagnosis.error_category}' repeated on consecutive attempts — "
                    "further retries are unlikely to help without new information."
                ),
            )

        category = diagnosis.error_category
        low_confidence = diagnosis.confidence in (
            DiagnosisConfidence.LOW,
            DiagnosisConfidence.UNKNOWN,
        )

        if category == "policy_restriction":
            return HealingStrategy(
                kind=HealingStrategyKind.ESCALATE_TO_USER,
                description="Policy denied the action; only a human can decide whether to "
                "widen scope or drop the action.",
                requires_user_approval=True,
            )

        if category == "timeout" and retries_used < self._config.max_retries:
            multiplier = min(2 ** (retries_used + 1), int(self._config.max_timeout_multiplier))
            return HealingStrategy(
                kind=HealingStrategyKind.ADJUST_TIMEOUT,
                description=f"Timeout hit; retry with {multiplier}× timeout.",
                parameters={"timeout_multiplier": multiplier},
                requires_policy_recheck=True,
            )

        if category == "missing_package" or category == "missing_executable":
            return HealingStrategy(
                kind=HealingStrategyKind.INSTALL_MISSING_DEPENDENCY,
                description="A required package/executable is missing — try installing it via the "
                "existing Tool Installation service.",
                parameters={"hint": diagnosis.root_cause},
                requires_policy_recheck=True,
                requires_user_approval=True,
            )

        if category == "network_connectivity" and retries_used < self._config.max_retries:
            delay = self._config.backoff_base_seconds * (2**retries_used)
            return HealingStrategy(
                kind=HealingStrategyKind.RETRY_WITH_BACKOFF,
                description=f"Transient network issue; retry after {delay:.1f}s backoff.",
                parameters={"backoff_seconds": delay},
            )

        if category == "incompatible_version":
            return HealingStrategy(
                kind=HealingStrategyKind.USE_ALTERNATIVE_TOOL,
                description="No compatible version — search the Tool Registry for an alternative.",
                requires_user_approval=True,
            )

        if category in ("permission_issue", "disk_space"):
            return HealingStrategy(
                kind=HealingStrategyKind.ESCALATE_TO_USER,
                description=f"'{category}' requires operator action; the agent cannot resolve it.",
                requires_user_approval=True,
            )

        if category == "invalid_argument":
            return HealingStrategy(
                kind=HealingStrategyKind.REDUCE_SCOPE,
                description="Command arguments were rejected — propose a simpler variant.",
                requires_policy_recheck=True,
                requires_user_approval=True,
            )

        if low_confidence or retries_used >= self._config.max_retries:
            return HealingStrategy(
                kind=HealingStrategyKind.ESCALATE_TO_USER,
                description="Diagnosis inconclusive or retry budget exhausted — escalating.",
                requires_user_approval=True,
            )

        # Default: a bounded retry once, then escalate on the next round.
        return HealingStrategy(
            kind=HealingStrategyKind.RETRY_WITH_BACKOFF,
            description="Category was inconclusive but retryable; one bounded retry.",
            parameters={"backoff_seconds": self._config.backoff_base_seconds},
        )
