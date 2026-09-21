"""Self-Healing Engine data models — extends the Phase 12 AdaptationEngine
with structured diagnosis, remediation strategies, and a learning history.

Framework/database-independent dataclasses, same pattern as every other
services/ package. The healing engine never invents authorization: every
proposed remediation still goes through the existing PolicyEngine /
TerminalEngine / ToolInstallationService pipeline before it can take
effect.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class DiagnosisConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class HealingStrategyKind(StrEnum):
    """The fixed vocabulary of what self-healing can propose. Anything
    the engine wants to do that isn't one of these is out of scope, and
    the task falls back to human clarification — never silent
    improvisation."""

    RETRY_WITH_BACKOFF = "retry_with_backoff"
    INSTALL_MISSING_DEPENDENCY = "install_missing_dependency"
    USE_ALTERNATIVE_TOOL = "use_alternative_tool"
    ADJUST_TIMEOUT = "adjust_timeout"
    REDUCE_SCOPE = "reduce_scope"
    ESCALATE_TO_USER = "escalate_to_user"
    ABANDON = "abandon"


class HealingOutcome(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class Diagnosis:
    """Structured explanation of why an action failed — never the model's
    hidden chain-of-thought, only factual signals plus a category."""

    id: UUID = field(default_factory=uuid4)
    error_category: str = "unknown"
    root_cause: str = ""
    supporting_signals: list[str] = field(default_factory=list)
    confidence: DiagnosisConfidence = DiagnosisConfidence.UNKNOWN
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class HealingStrategy:
    id: UUID = field(default_factory=uuid4)
    kind: HealingStrategyKind = HealingStrategyKind.RETRY_WITH_BACKOFF
    description: str = ""
    parameters: dict = field(default_factory=dict)
    # Whether this strategy would touch the OS (install a package,
    # execute a diagnostic) — determines if it goes through the policy
    # gate again before being applied.
    requires_policy_recheck: bool = False
    # Whether the *human operator* must explicitly approve this specific
    # remediation before it runs (higher bar than requires_policy_recheck).
    requires_user_approval: bool = False


@dataclass
class HealingAttempt:
    id: UUID = field(default_factory=uuid4)
    task_id: UUID | None = None
    action_id: UUID | None = None
    diagnosis: Diagnosis | None = None
    strategy: HealingStrategy | None = None
    outcome: HealingOutcome = HealingOutcome.PENDING
    note: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
