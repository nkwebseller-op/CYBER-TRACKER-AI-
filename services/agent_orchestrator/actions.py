"""Structured action vocabulary. The AI never chooses anything outside
this enum — a value the model returns that isn't one of these is a
validation failure (see services/agent_orchestrator/ai_schemas.py), not a
new capability the orchestrator improvises."""

from enum import StrEnum


class ActionType(StrEnum):
    DISCOVER_TARGET = "DISCOVER_TARGET"
    CHECK_ENVIRONMENT = "CHECK_ENVIRONMENT"
    RESEARCH_TOOL = "RESEARCH_TOOL"
    INSTALL_TOOL = "INSTALL_TOOL"
    RUN_DIAGNOSTIC = "RUN_DIAGNOSTIC"
    COLLECT_INFORMATION = "COLLECT_INFORMATION"
    ANALYZE_OUTPUT = "ANALYZE_OUTPUT"
    VERIFY_FINDING = "VERIFY_FINDING"
    GENERATE_REPORT = "GENERATE_REPORT"
    ASK_USER = "ASK_USER"
    WAIT_FOR_APPROVAL = "WAIT_FOR_APPROVAL"
    COMPLETE_TASK = "COMPLETE_TASK"


# Action types that can never, by themselves, cause an OS-level side
# effect — they're always safe to evaluate without a fresh policy check
# (RUN_DIAGNOSTIC and INSTALL_TOOL always go through PolicyEngine /
# ToolInstallationService regardless, but these never even attempt to).
READ_ONLY_ACTION_TYPES = frozenset(
    {
        ActionType.DISCOVER_TARGET,
        ActionType.CHECK_ENVIRONMENT,
        ActionType.RESEARCH_TOOL,
        ActionType.ANALYZE_OUTPUT,
        ActionType.VERIFY_FINDING,
        ActionType.GENERATE_REPORT,
        ActionType.ASK_USER,
        ActionType.WAIT_FOR_APPROVAL,
        ActionType.COMPLETE_TASK,
    }
)

# Action types that reach a system that can change state and therefore
# always require the real PolicyEngine / ToolInstallationService gate.
EXECUTION_ACTION_TYPES = frozenset({ActionType.RUN_DIAGNOSTIC, ActionType.INSTALL_TOOL})
