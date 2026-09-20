"""AgentBudgetManager: hard, configurable ceilings the orchestrator
checks before every action/model-call/installation. When a budget is
exhausted the task stops safely (phase -> BLOCKED with a clear reason),
never silently keeps going and never crashes."""

from dataclasses import dataclass
from datetime import UTC, datetime

from services.agent_orchestrator.errors import BudgetExceededError
from services.agent_orchestrator.models import AgentTaskState


@dataclass(frozen=True)
class AgentBudgetConfig:
    max_task_duration_seconds: float = 1800.0
    max_actions: int = 40
    max_retries_per_action: int = 2
    max_tool_installations: int = 3
    max_model_calls: int = 60
    max_output_chars: int = 200_000
    max_context_chars: int = 20_000
    max_concurrent_tasks: int = 5


class AgentBudgetManager:
    def __init__(self, config: AgentBudgetConfig | None = None) -> None:
        self.config = config or AgentBudgetConfig()

    def check_action_budget(self, state: AgentTaskState) -> None:
        if state.action_count >= self.config.max_actions:
            raise BudgetExceededError(
                f"Maximum action budget reached ({self.config.max_actions})."
            )
        if state.started_at is not None:
            elapsed = (datetime.now(UTC) - state.started_at).total_seconds()
            if elapsed >= self.config.max_task_duration_seconds:
                raise BudgetExceededError(
                    f"Maximum task duration reached ({self.config.max_task_duration_seconds}s)."
                )

    def check_model_call_budget(self, state: AgentTaskState) -> None:
        if state.model_call_count >= self.config.max_model_calls:
            raise BudgetExceededError(
                f"Maximum model call budget reached ({self.config.max_model_calls})."
            )

    def check_installation_budget(self, state: AgentTaskState) -> None:
        if state.installation_count >= self.config.max_tool_installations:
            raise BudgetExceededError(
                f"Maximum tool installation budget reached ({self.config.max_tool_installations})."
            )

    def check_retry_budget(self, state: AgentTaskState, action_key: str) -> None:
        retries = state.retry_count_by_action.get(action_key, 0)
        if retries >= self.config.max_retries_per_action:
            raise BudgetExceededError(
                f"Maximum retries reached for '{action_key}' "
                f"({self.config.max_retries_per_action})."
            )

    def status(self, state: AgentTaskState) -> dict:
        return {
            "actionsUsed": state.action_count,
            "actionsLimit": self.config.max_actions,
            "modelCallsUsed": state.model_call_count,
            "modelCallsLimit": self.config.max_model_calls,
            "installationsUsed": state.installation_count,
            "installationsLimit": self.config.max_tool_installations,
        }
