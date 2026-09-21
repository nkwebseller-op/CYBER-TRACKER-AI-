"""HealingHistory: an in-process record of past diagnosis/strategy/outcome
triples, used for two things:

1. Loop detection — a task that has already tried strategy X for
   category Y and failed once shouldn't propose the same strategy again
   for the same category without new evidence.
2. Confidence adjustment — categories that have succeeded before via a
   particular strategy are ranked slightly higher on their next
   occurrence.

Deliberately in-memory and per-process — no separate "learning DB" or
model training. A proper long-term store belongs to a later phase and
would live behind this Protocol.
"""

from typing import Protocol
from uuid import UUID

from services.self_healing.models import HealingAttempt, HealingOutcome


class HealingHistoryStore(Protocol):
    def record(self, attempt: HealingAttempt) -> None: ...
    def attempts_for_task(self, task_id: UUID) -> list[HealingAttempt]: ...
    def category_history(self, task_id: UUID, category: str) -> list[HealingAttempt]: ...
    def update_outcome(self, attempt_id: UUID, outcome: HealingOutcome, note: str) -> None: ...


class InMemoryHealingHistoryStore:
    def __init__(self) -> None:
        self._attempts: list[HealingAttempt] = []

    def record(self, attempt: HealingAttempt) -> None:
        self._attempts.append(attempt)

    def attempts_for_task(self, task_id: UUID) -> list[HealingAttempt]:
        return [a for a in self._attempts if a.task_id == task_id]

    def category_history(self, task_id: UUID, category: str) -> list[HealingAttempt]:
        return [
            a
            for a in self._attempts
            if a.task_id == task_id and a.diagnosis and a.diagnosis.error_category == category
        ]

    def update_outcome(self, attempt_id: UUID, outcome: HealingOutcome, note: str = "") -> None:
        for attempt in self._attempts:
            if attempt.id == attempt_id:
                attempt.outcome = outcome
                if note:
                    attempt.note = f"{attempt.note} | {note}" if attempt.note else note
                return

    def success_rate_for_strategy(self, kind: str) -> float:
        matching = [
            a for a in self._attempts if a.strategy and a.strategy.kind.value == kind
        ]
        if not matching:
            return 0.0
        succeeded = sum(1 for a in matching if a.outcome == HealingOutcome.SUCCEEDED)
        return succeeded / len(matching)
