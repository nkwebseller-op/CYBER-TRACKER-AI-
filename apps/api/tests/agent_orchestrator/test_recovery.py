from services.agent_orchestrator.budget import AgentBudgetConfig, AgentBudgetManager
from services.agent_orchestrator.models import AgentTaskState
from services.agent_orchestrator.recovery import (
    AdaptationEngine,
    AdaptationStrategy,
    ErrorClassifier,
    FailureClass,
)


def test_classify_permission_denied():
    classifier = ErrorClassifier()
    result = classifier.classify(
        timed_out=False, policy_denied=False, exit_code=1, stderr="Permission denied"
    )
    assert result == FailureClass.PERMISSION_ISSUE


def test_classify_timeout():
    classifier = ErrorClassifier()
    result = classifier.classify(timed_out=True, policy_denied=False, exit_code=None, stderr=None)
    assert result == FailureClass.TIMEOUT


def test_classify_policy_denied_takes_priority():
    classifier = ErrorClassifier()
    result = classifier.classify(
        timed_out=True, policy_denied=True, exit_code=1, stderr="Permission denied"
    )
    assert result == FailureClass.POLICY_RESTRICTION


def test_classify_missing_executable():
    classifier = ErrorClassifier()
    result = classifier.classify(
        timed_out=False, policy_denied=False, exit_code=127, stderr="command not found"
    )
    assert result == FailureClass.MISSING_EXECUTABLE


def test_classify_unknown_when_nothing_matches():
    classifier = ErrorClassifier()
    result = classifier.classify(timed_out=False, policy_denied=False, exit_code=0, stderr=None)
    assert result == FailureClass.UNKNOWN


def test_adaptation_retries_transient_failure():
    engine = AdaptationEngine(AgentBudgetManager(AgentBudgetConfig(max_retries_per_action=3)))
    state = AgentTaskState(objective="x")
    decision = engine.decide(state, action_key="RUN_DIAGNOSTIC", failure=FailureClass.TIMEOUT)
    assert decision.strategy == AdaptationStrategy.RETRY


def test_adaptation_never_retries_policy_restriction():
    engine = AdaptationEngine(AgentBudgetManager())
    state = AgentTaskState(objective="x")
    decision = engine.decide(
        state, action_key="RUN_DIAGNOSTIC", failure=FailureClass.POLICY_RESTRICTION
    )
    assert decision.strategy == AdaptationStrategy.FAIL


def test_adaptation_stops_on_repeated_identical_failure():
    engine = AdaptationEngine(AgentBudgetManager(AgentBudgetConfig(max_retries_per_action=5)))
    state = AgentTaskState(objective="x", last_error_signature="RUN_DIAGNOSTIC:timeout")
    decision = engine.decide(state, action_key="RUN_DIAGNOSTIC", failure=FailureClass.TIMEOUT)
    assert decision.strategy == AdaptationStrategy.FAIL


def test_adaptation_asks_user_for_missing_dependency():
    engine = AdaptationEngine(AgentBudgetManager())
    state = AgentTaskState(objective="x")
    decision = engine.decide(
        state, action_key="INSTALL_TOOL", failure=FailureClass.MISSING_DEPENDENCY
    )
    assert decision.strategy == AdaptationStrategy.ASK_USER


def test_adaptation_fails_when_retry_budget_exhausted():
    engine = AdaptationEngine(AgentBudgetManager(AgentBudgetConfig(max_retries_per_action=0)))
    state = AgentTaskState(objective="x")
    decision = engine.decide(state, action_key="RUN_DIAGNOSTIC", failure=FailureClass.TIMEOUT)
    assert decision.strategy == AdaptationStrategy.FAIL
