import pytest
from services.agent_orchestrator.budget import AgentBudgetConfig, AgentBudgetManager
from services.agent_orchestrator.errors import BudgetExceededError
from services.agent_orchestrator.models import AgentTaskState


def test_action_budget_raises_when_exhausted():
    budget = AgentBudgetManager(AgentBudgetConfig(max_actions=2))
    state = AgentTaskState(objective="x", action_count=2)
    with pytest.raises(BudgetExceededError):
        budget.check_action_budget(state)


def test_action_budget_allows_within_limit():
    budget = AgentBudgetManager(AgentBudgetConfig(max_actions=5))
    state = AgentTaskState(objective="x", action_count=2)
    budget.check_action_budget(state)  # must not raise


def test_model_call_budget_raises_when_exhausted():
    budget = AgentBudgetManager(AgentBudgetConfig(max_model_calls=1))
    state = AgentTaskState(objective="x", model_call_count=1)
    with pytest.raises(BudgetExceededError):
        budget.check_model_call_budget(state)


def test_installation_budget_raises_when_exhausted():
    budget = AgentBudgetManager(AgentBudgetConfig(max_tool_installations=1))
    state = AgentTaskState(objective="x", installation_count=1)
    with pytest.raises(BudgetExceededError):
        budget.check_installation_budget(state)


def test_retry_budget_raises_when_exhausted():
    budget = AgentBudgetManager(AgentBudgetConfig(max_retries_per_action=1))
    state = AgentTaskState(objective="x", retry_count_by_action={"RUN_DIAGNOSTIC": 1})
    with pytest.raises(BudgetExceededError):
        budget.check_retry_budget(state, "RUN_DIAGNOSTIC")


def test_task_duration_budget_raises_when_exceeded():
    from datetime import UTC, datetime, timedelta

    budget = AgentBudgetManager(AgentBudgetConfig(max_task_duration_seconds=1))
    state = AgentTaskState(objective="x", started_at=datetime.now(UTC) - timedelta(seconds=10))
    with pytest.raises(BudgetExceededError):
        budget.check_action_budget(state)


def test_status_reports_usage_and_limits():
    budget = AgentBudgetManager(AgentBudgetConfig(max_actions=10, max_model_calls=5))
    state = AgentTaskState(objective="x", action_count=3, model_call_count=2)
    status = budget.status(state)
    assert status["actionsUsed"] == 3
    assert status["actionsLimit"] == 10
    assert status["modelCallsUsed"] == 2
