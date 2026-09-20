"""Structured AI decision contract for the autonomous agent loop — same
pattern as services/agent/schemas.py's AIResponse: this is exactly what
AIProvider.generate_structured is asked to produce, and it is validated
before a single field of it is trusted. A malformed or missing field
never reaches `services.agent_orchestrator.orchestrator` — it is treated
as a provider error and the step is retried/aborted, never guessed at.

The model is never shown raw application state — only the bounded
summary services.agent_orchestrator.reasoning.build_agent_context_block
constructs — and its own hidden reasoning never reaches storage or the
UI: `reasoning_summary` is a short operational note, not a chain of
thought, and the caller is responsible for keeping it that way (bounded
length, no verbatim model internals).
"""

from enum import StrEnum

from pydantic import BaseModel, Field, ValidationError

from services.agent_orchestrator.actions import ActionType

__all__ = [
    "AgentDecision",
    "AgentDecisionValidationError",
    "AGENT_DECISION_SCHEMA",
    "parse_agent_decision",
]


class AgentIntent(StrEnum):
    CONTINUE = "CONTINUE"
    CLARIFY = "CLARIFY"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


class AgentDecision(BaseModel):
    reasoning_summary: str = Field(alias="reasoningSummary", max_length=500)
    intent: AgentIntent
    next_action: str = Field(alias="nextAction", max_length=300)
    action_type: ActionType = Field(alias="actionType")
    required_capability: str | None = Field(default=None, alias="requiredCapability")
    tool: str | None = None
    arguments: dict = Field(default_factory=dict)
    requires_approval: bool = Field(alias="requiresApproval")
    missing_information: list[str] = Field(default_factory=list, alias="missingInformation")
    expected_evidence: list[str] = Field(default_factory=list, alias="expectedEvidence")
    verification_plan: list[str] = Field(default_factory=list, alias="verificationPlan")
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = {"populate_by_name": True}


class AgentDecisionValidationError(ValueError):
    """Raised when the model's structured output fails schema validation.
    The caller must never forward the raw payload to execution — see
    services/agent_orchestrator/orchestrator.py, which treats this the
    same as any other provider failure (classified, bounded-retried,
    never silently ignored)."""


def parse_agent_decision(payload: dict) -> AgentDecision:
    try:
        return AgentDecision.model_validate(payload)
    except ValidationError as exc:
        raise AgentDecisionValidationError(
            f"Agent decision failed schema validation: {exc}"
        ) from exc


AGENT_DECISION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "reasoningSummary": {"type": "STRING"},
        "intent": {"type": "STRING", "enum": [i.value for i in AgentIntent]},
        "nextAction": {"type": "STRING"},
        "actionType": {"type": "STRING", "enum": [a.value for a in ActionType]},
        "requiredCapability": {"type": "STRING"},
        "tool": {"type": "STRING"},
        "arguments": {"type": "OBJECT"},
        "requiresApproval": {"type": "BOOLEAN"},
        "missingInformation": {"type": "ARRAY", "items": {"type": "STRING"}},
        "expectedEvidence": {"type": "ARRAY", "items": {"type": "STRING"}},
        "verificationPlan": {"type": "ARRAY", "items": {"type": "STRING"}},
        "confidence": {"type": "NUMBER"},
    },
    "required": [
        "reasoningSummary",
        "intent",
        "nextAction",
        "actionType",
        "requiresApproval",
        "confidence",
    ],
}
