"""SelfHealingEngine: ties DiagnosisEngine + HealingPlanner + history
together into a single `heal()` entry point the AgentOrchestrator can
call after a failed action.

    FAILED ACTION
      -> DiagnosisEngine.diagnose  (deterministic root-cause analysis)
      -> HealingHistoryStore lookup (was this tried before?)
      -> HealingPlanner.propose    (deterministic strategy selection)
      -> HealingAttempt recorded, returned to caller

The engine NEVER applies a strategy itself — it only proposes one.
Applying it (re-running the action, installing a dependency, escalating)
remains the AgentOrchestrator's job, going through the same policy/
approval boundaries as every other action.
"""

from dataclasses import dataclass
from uuid import UUID

from services.self_healing.diagnosis import DiagnosisEngine, FailureSignals
from services.self_healing.history import HealingHistoryStore, InMemoryHealingHistoryStore
from services.self_healing.models import (
    Diagnosis,
    HealingAttempt,
    HealingOutcome,
    HealingStrategy,
)
from services.self_healing.planner import HealingPlanner


@dataclass
class HealingProposal:
    diagnosis: Diagnosis
    strategy: HealingStrategy
    attempt: HealingAttempt


class SelfHealingEngine:
    def __init__(
        self,
        *,
        diagnosis: DiagnosisEngine | None = None,
        planner: HealingPlanner | None = None,
        history: HealingHistoryStore | None = None,
    ) -> None:
        self._diagnosis = diagnosis or DiagnosisEngine()
        self._planner = planner or HealingPlanner()
        self._history = history or InMemoryHealingHistoryStore()

    def heal(
        self,
        *,
        task_id: UUID,
        action_id: UUID | None,
        signals: FailureSignals,
    ) -> HealingProposal:
        diagnosis = self._diagnosis.diagnose(signals)

        prior = self._history.attempts_for_task(task_id)
        prior_categories = [
            a.diagnosis.error_category for a in prior if a.diagnosis is not None
        ]
        retries_used = sum(
            1
            for a in prior
            if a.diagnosis
            and a.diagnosis.error_category == diagnosis.error_category
        )

        strategy = self._planner.propose(
            diagnosis, retries_used=retries_used, prior_categories=prior_categories
        )

        attempt = HealingAttempt(
            task_id=task_id,
            action_id=action_id,
            diagnosis=diagnosis,
            strategy=strategy,
            outcome=HealingOutcome.PENDING,
            note=f"Proposed {strategy.kind.value} for {diagnosis.error_category}.",
        )
        self._history.record(attempt)
        return HealingProposal(diagnosis=diagnosis, strategy=strategy, attempt=attempt)

    def record_outcome(self, attempt_id: UUID, outcome: HealingOutcome, note: str = "") -> None:
        self._history.update_outcome(attempt_id, outcome, note)
