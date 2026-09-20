"""Structured error hierarchy for the Agent Orchestrator — same pattern as
every other services/ package."""

from enum import StrEnum


class AgentErrorCode(StrEnum):
    TASK_NOT_FOUND = "task_not_found"
    INVALID_STATE_TRANSITION = "invalid_state_transition"
    APPROVAL_REQUIRED = "approval_required"
    NOT_WAITING_FOR_APPROVAL = "not_waiting_for_approval"
    BUDGET_EXCEEDED = "budget_exceeded"
    AUTHORIZATION_REQUIRED = "authorization_required"
    OUT_OF_SCOPE = "out_of_scope"
    INVALID_DECISION = "invalid_decision"
    CONCURRENT_TASK_LIMIT = "concurrent_task_limit"
    CANCELLED = "cancelled"


class AgentOrchestratorError(RuntimeError):
    def __init__(self, code: AgentErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class TaskNotFoundError(AgentOrchestratorError):
    def __init__(self, message: str) -> None:
        super().__init__(AgentErrorCode.TASK_NOT_FOUND, message)


class InvalidStateTransitionError(AgentOrchestratorError):
    def __init__(self, message: str) -> None:
        super().__init__(AgentErrorCode.INVALID_STATE_TRANSITION, message)


class NotWaitingForApprovalError(AgentOrchestratorError):
    def __init__(self, message: str) -> None:
        super().__init__(AgentErrorCode.NOT_WAITING_FOR_APPROVAL, message)


class BudgetExceededError(AgentOrchestratorError):
    def __init__(self, message: str) -> None:
        super().__init__(AgentErrorCode.BUDGET_EXCEEDED, message)


class OutOfScopeError(AgentOrchestratorError):
    def __init__(self, message: str) -> None:
        super().__init__(AgentErrorCode.OUT_OF_SCOPE, message)


class InvalidDecisionError(AgentOrchestratorError):
    def __init__(self, message: str) -> None:
        super().__init__(AgentErrorCode.INVALID_DECISION, message)


class ConcurrentTaskLimitError(AgentOrchestratorError):
    def __init__(self, message: str) -> None:
        super().__init__(AgentErrorCode.CONCURRENT_TASK_LIMIT, message)
