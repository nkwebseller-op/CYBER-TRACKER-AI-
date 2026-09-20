"""Error classification + bounded adaptation.

    ACTION FAILS
      -> ErrorClassifier.classify (deterministic, from real stderr/exit
         code/exception — never guessed by the model)
      -> AdaptationEngine.decide (retry / ask_user / fail), respecting
         the budget's per-action retry cap and loop detection (the same
         error category twice in a row for the same action stops
         retrying immediately rather than burning the whole budget)

Never retries indefinitely, never retries a policy/authorization
rejection (retrying that just repeats the same refusal), and always
returns a reason a human could read directly.
"""

from dataclasses import dataclass
from enum import StrEnum

from services.agent_orchestrator.budget import AgentBudgetManager
from services.agent_orchestrator.models import AgentTaskState

_NEVER_RETRY_CATEGORIES = frozenset(
    {"policy_restriction", "permission_issue", "unsupported_platform"}
)


class FailureClass(StrEnum):
    MISSING_DEPENDENCY = "missing_dependency"
    MISSING_EXECUTABLE = "missing_executable"
    INCOMPATIBLE_VERSION = "incompatible_version"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    PERMISSION_ISSUE = "permission_issue"
    INVALID_ARGUMENT = "invalid_argument"
    CONFIGURATION_ISSUE = "configuration_issue"
    NETWORK_CONNECTIVITY = "network_connectivity"
    TIMEOUT = "timeout"
    TOOL_UNAVAILABLE = "tool_unavailable"
    UNEXPECTED_OUTPUT = "unexpected_output"
    POLICY_RESTRICTION = "policy_restriction"
    UNKNOWN = "unknown"


_STDERR_HINTS: tuple[tuple[str, FailureClass], ...] = (
    ("permission denied", FailureClass.PERMISSION_ISSUE),
    ("not found", FailureClass.MISSING_EXECUTABLE),
    ("no such file", FailureClass.MISSING_EXECUTABLE),
    ("could not resolve", FailureClass.NETWORK_CONNECTIVITY),
    ("network is unreachable", FailureClass.NETWORK_CONNECTIVITY),
    ("connection refused", FailureClass.NETWORK_CONNECTIVITY),
    ("unsupported platform", FailureClass.UNSUPPORTED_PLATFORM),
    ("incompatible", FailureClass.INCOMPATIBLE_VERSION),
    ("invalid argument", FailureClass.INVALID_ARGUMENT),
    ("dependency", FailureClass.MISSING_DEPENDENCY),
)


class ErrorClassifier:
    def classify(
        self, *, timed_out: bool, policy_denied: bool, exit_code: int | None, stderr: str | None
    ) -> FailureClass:
        if policy_denied:
            return FailureClass.POLICY_RESTRICTION
        if timed_out:
            return FailureClass.TIMEOUT
        text = (stderr or "").lower()
        for hint, category in _STDERR_HINTS:
            if hint in text:
                return category
        if exit_code is not None and exit_code != 0:
            return FailureClass.UNEXPECTED_OUTPUT
        return FailureClass.UNKNOWN


class AdaptationStrategy(StrEnum):
    RETRY = "retry"
    ASK_USER = "ask_user"
    FAIL = "fail"


@dataclass
class AdaptationDecision:
    strategy: AdaptationStrategy
    reason: str


class AdaptationEngine:
    def __init__(self, budget: AgentBudgetManager) -> None:
        self._budget = budget

    def decide(
        self, state: AgentTaskState, *, action_key: str, failure: FailureClass
    ) -> AdaptationDecision:
        signature = f"{action_key}:{failure.value}"
        if state.last_error_signature == signature:
            return AdaptationDecision(
                strategy=AdaptationStrategy.FAIL,
                reason=f"Repeated identical failure ({failure.value}) — stopping instead of "
                "looping.",
            )
        if failure.value in _NEVER_RETRY_CATEGORIES:
            return AdaptationDecision(
                strategy=AdaptationStrategy.FAIL,
                reason=f"'{failure.value}' is not retryable; the same input would fail the "
                "same way.",
            )
        try:
            self._budget.check_retry_budget(state, action_key)
        except Exception:  # noqa: BLE001 - budget signals via exception; translate to a decision
            return AdaptationDecision(
                strategy=AdaptationStrategy.FAIL, reason="Retry budget exhausted for this action."
            )
        if failure in (FailureClass.MISSING_DEPENDENCY, FailureClass.TOOL_UNAVAILABLE):
            return AdaptationDecision(
                strategy=AdaptationStrategy.ASK_USER,
                reason=f"'{failure.value}' likely needs a different tool/capability choice.",
            )
        return AdaptationDecision(
            strategy=AdaptationStrategy.RETRY, reason=f"'{failure.value}' may be transient."
        )
