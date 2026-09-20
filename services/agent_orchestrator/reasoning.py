"""AgentReasoner: the only place the orchestrator talks to an AI provider.

Wraps the existing `services.agent.providers.base.AIProvider` — the same
abstraction the chat pipeline uses — rather than introducing a second AI
integration. Sends a bounded, structured context block (never the raw
Python state object, never unbounded history) and validates the response
against `AgentDecision` before returning it. A provider error or a
validation failure both come back as `AgentReasoningError`; neither one
ever reaches execution.
"""

from dataclasses import dataclass

from services.agent.providers.base import AIProvider, AIProviderError, Message
from services.agent_orchestrator.ai_schemas import (
    AGENT_DECISION_SCHEMA,
    AgentDecision,
    AgentDecisionValidationError,
    parse_agent_decision,
)
from services.agent_orchestrator.models import AgentTaskState

SYSTEM_INSTRUCTION = (
    "You are the reasoning engine for Cyber AI System's autonomous security "
    "agent. You NEVER execute anything directly — you only propose ONE next "
    "structured action from the fixed action-type list you are given. You "
    "never invent a target outside the authorized scope you are shown. You "
    "never claim an objective is verified without evidence. You never "
    "fabricate tool capabilities. If required information is missing, "
    "propose ASK_USER or CLARIFY instead of guessing."
)

_MAX_CONTEXT_CHARS = 20_000
_MAX_RECENT_ACTIONS = 8
_MAX_RECENT_EVIDENCE = 8


class AgentReasoningError(RuntimeError):
    pass


@dataclass
class ReasoningContext:
    available_capabilities: list[str]
    platform: str | None
    policy_constraints: list[str]
    budget_remaining: dict


def build_agent_context_block(state: AgentTaskState, context: ReasoningContext) -> str:
    """A deliberately bounded, structured summary — never a dump of the
    full state object, and never the model's own prior hidden reasoning
    (only the operational `reasoning_summary` already stored per action)."""
    recent_actions = state.actions[-_MAX_RECENT_ACTIONS:]
    recent_evidence = (state.observations + state.findings)[-_MAX_RECENT_EVIDENCE:]

    lines = [
        f"Objective: {state.objective}",
        f"Authorized target: {state.target or 'UNKNOWN'} (type: {state.target_type or 'UNKNOWN'})",
        f"Authorization status: {state.authorization_status}",
        f"Scope: {', '.join(state.scope) or 'none declared'}",
        f"Current phase: {state.phase.value}",
        f"Platform: {context.platform or 'unknown'}",
        f"Available capabilities: {', '.join(context.available_capabilities) or 'none known'}",
        f"Policy constraints: {', '.join(context.policy_constraints) or 'none additional'}",
        f"Budget remaining: {context.budget_remaining}",
        f"Completed actions ({len(state.actions)} total, most recent {len(recent_actions)}):",
    ]
    for action in recent_actions:
        lines.append(
            f"  - {action.action_type.value} tool={action.tool} "
            f"result={action.result_summary or 'pending'}"
        )
    lines.append(f"Recent evidence ({len(recent_evidence)}):")
    for item in recent_evidence:
        lines.append(f"  - [{item.kind.value}] {item.summary}")
    if state.errors:
        lines.append(f"Errors so far: {[e.category for e in state.errors[-5:]]}")
    if state.unknowns:
        lines.append(f"Unresolved unknowns: {state.unknowns}")

    text = "\n".join(lines)
    if len(text) > _MAX_CONTEXT_CHARS:
        text = text[:_MAX_CONTEXT_CHARS] + "\n...[truncated]"
    return text


class AgentReasoner:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def decide(self, state: AgentTaskState, context: ReasoningContext) -> AgentDecision:
        context_block = build_agent_context_block(state, context)
        messages = [
            Message(role="system", content=SYSTEM_INSTRUCTION),
            Message(
                role="user",
                content=(
                    "Current task context:\n```\n" + context_block + "\n```\n"
                    "Propose exactly one next structured action as JSON matching the "
                    "required schema."
                ),
            ),
        ]
        try:
            result = await self._provider.generate_structured(
                messages, schema=AGENT_DECISION_SCHEMA, temperature=0.1
            )
        except AIProviderError as exc:
            raise AgentReasoningError(f"AI provider failed: {exc}") from exc

        try:
            return parse_agent_decision(result.data)
        except AgentDecisionValidationError as exc:
            raise AgentReasoningError(str(exc)) from exc
