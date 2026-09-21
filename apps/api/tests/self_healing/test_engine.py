from uuid import uuid4

from services.self_healing.diagnosis import FailureSignals
from services.self_healing.engine import SelfHealingEngine
from services.self_healing.history import InMemoryHealingHistoryStore
from services.self_healing.models import HealingOutcome, HealingStrategyKind


def test_heal_returns_diagnosis_and_strategy():
    engine = SelfHealingEngine()
    proposal = engine.heal(
        task_id=uuid4(),
        action_id=uuid4(),
        signals=FailureSignals(stderr="E: Unable to locate package dig"),
    )
    assert proposal.diagnosis.error_category == "missing_package"
    assert proposal.strategy.kind == HealingStrategyKind.INSTALL_MISSING_DEPENDENCY


def test_healing_history_records_attempts():
    history = InMemoryHealingHistoryStore()
    engine = SelfHealingEngine(history=history)
    task_id = uuid4()
    engine.heal(task_id=task_id, action_id=None, signals=FailureSignals(timed_out=True))
    engine.heal(task_id=task_id, action_id=None, signals=FailureSignals(stderr="permission denied"))
    assert len(history.attempts_for_task(task_id)) == 2


def test_repeated_category_stops_after_abandoning():
    history = InMemoryHealingHistoryStore()
    engine = SelfHealingEngine(history=history)
    task_id = uuid4()
    engine.heal(
        task_id=task_id, action_id=None, signals=FailureSignals(stderr="command not found: nmap")
    )
    proposal = engine.heal(
        task_id=task_id, action_id=None, signals=FailureSignals(stderr="command not found: nmap")
    )
    assert proposal.strategy.kind == HealingStrategyKind.ABANDON


def test_record_outcome_updates_history():
    history = InMemoryHealingHistoryStore()
    engine = SelfHealingEngine(history=history)
    task_id = uuid4()
    proposal = engine.heal(
        task_id=task_id, action_id=None, signals=FailureSignals(stderr="Network is unreachable")
    )
    engine.record_outcome(proposal.attempt.id, HealingOutcome.SUCCEEDED, note="Retry worked")
    stored = history.attempts_for_task(task_id)[0]
    assert stored.outcome == HealingOutcome.SUCCEEDED
    assert "Retry worked" in stored.note


def test_success_rate_tracked_across_attempts():
    history = InMemoryHealingHistoryStore()
    engine = SelfHealingEngine(history=history)
    for _ in range(3):
        proposal = engine.heal(
            task_id=uuid4(),
            action_id=None,
            signals=FailureSignals(stderr="Network is unreachable"),
        )
        engine.record_outcome(proposal.attempt.id, HealingOutcome.SUCCEEDED)
    rate = history.success_rate_for_strategy("retry_with_backoff")
    assert rate == 1.0


def test_never_leaks_secrets_into_diagnosis_supporting_signals():
    """A stderr line containing a secret-shaped token should still be
    diagnosed without echoing the secret verbatim into the supporting
    signals — the pattern matched is stored, not the raw payload."""
    engine = SelfHealingEngine()
    proposal = engine.heal(
        task_id=uuid4(),
        action_id=None,
        signals=FailureSignals(
            stderr="AUTH_TOKEN=sk-abcdefghijklmnopqrstuvwx invalid argument"
        ),
    )
    # supporting signals contain the pattern and the *matched substring*
    # (which for invalid_argument is just "invalid argument"), never the
    # full stderr.
    for signal in proposal.diagnosis.supporting_signals:
        assert "sk-abcdefghijklmnopqrstuvwx" not in signal
