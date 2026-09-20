"""Structured AI response contracts.

These mirror apps/web/src/types/chat.ts (TaskIntent/TaskPlan) exactly so
the backend and frontend agree on shape without a code-generation step —
see packages/shared-types/README.md for why that's a deliberate,
documented manual sync rather than automatic codegen at this stage.

`AIResponse` is what GeminiProvider.generate_structured is asked to
produce (as JSON, via GEMINI_RESPONSE_SCHEMA) and what the chat pipeline
validates before it ever reaches the frontend. Nothing here is passed to
an execution layer — see services/policy/engine.py for why "structured
output from the AI" and "an executable action" remain two different
things until a human approves and a real Target/action registry exists.
"""

from enum import StrEnum

from pydantic import BaseModel, Field, ValidationError

__all__ = [
    "TargetType",
    "AuthorizationState",
    "RiskLevel",
    "ApprovalRequirement",
    "MissingInfoField",
    "TaskIntent",
    "WorkflowStageKey",
    "WorkflowStageStatus",
    "WorkflowStage",
    "TaskPlanStatus",
    "TaskPlan",
    "AIResponse",
    "GEMINI_RESPONSE_SCHEMA",
    "AIResponseValidationError",
    "parse_ai_response",
]


class TargetType(StrEnum):
    WEB_APPLICATION = "web_application"
    API = "api"
    SERVER = "server"
    CLOUD_RESOURCE = "cloud_resource"
    MOBILE_DEVICE = "mobile_device"
    WIRELESS_DEVICE = "wireless_device"
    NETWORK_ASSET = "network_asset"
    UNKNOWN = "unknown"


class AuthorizationState(StrEnum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ApprovalRequirement(StrEnum):
    NO_APPROVAL_REQUIRED = "NO_APPROVAL_REQUIRED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class MissingInfoField(StrEnum):
    TARGET = "target"
    AUTHORIZATION = "authorization"
    SCOPE = "scope"
    ENVIRONMENT = "environment"


class TaskIntent(BaseModel):
    id: str
    objective: str
    target: str
    target_type: TargetType = Field(alias="targetType")
    requested_action: str = Field(alias="requestedAction")
    constraints: list[str] = Field(default_factory=list)
    authorization_status: AuthorizationState = Field(alias="authorizationStatus")
    risk_level: RiskLevel = Field(alias="riskLevel")
    requires_approval: ApprovalRequirement = Field(alias="requiresApproval")
    missing_information: list[MissingInfoField] = Field(alias="missingInformation")

    model_config = {"populate_by_name": True}


class WorkflowStageKey(StrEnum):
    UNDERSTAND = "UNDERSTAND"
    RESEARCH = "RESEARCH"
    SELECT = "SELECT"
    APPROVE = "APPROVE"
    PREPARE = "PREPARE"
    RUN = "RUN"
    ANALYZE = "ANALYZE"
    REPORT = "REPORT"


class WorkflowStageStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class WorkflowStage(BaseModel):
    key: WorkflowStageKey
    label: str
    status: WorkflowStageStatus


class TaskPlanStatus(StrEnum):
    WAITING_FOR_INFORMATION = "WAITING_FOR_INFORMATION"
    AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"


class TaskPlan(BaseModel):
    id: str
    conversation_id: str = Field(alias="conversationId")
    task_intent: TaskIntent = Field(alias="taskIntent")
    workflow: list[WorkflowStage]
    status: TaskPlanStatus
    created_at: str = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class AIResponse(BaseModel):
    """The exact JSON shape GeminiProvider.generate_structured is asked to
    produce for a chat turn. `message` is the only free-form field —
    everything else is programmatically consumed, never parsed out of
    prose."""

    message: str
    task_intent: TaskIntent = Field(alias="taskIntent")
    task_plan: TaskPlan = Field(alias="taskPlan")
    authorization_status: AuthorizationState = Field(alias="authorizationStatus")
    risk_level: RiskLevel = Field(alias="riskLevel")
    requires_approval: ApprovalRequirement = Field(alias="requiresApproval")
    missing_information: list[MissingInfoField] = Field(alias="missingInformation")
    next_action: str = Field(alias="nextAction")

    model_config = {"populate_by_name": True}


class AIResponseValidationError(ValueError):
    """Raised when a provider's structured output fails validation. The
    caller must treat this as `AIProviderErrorCode.INVALID_RESPONSE` — never
    forward the raw payload to a client or an execution layer."""


def parse_ai_response(payload: dict) -> AIResponse:
    try:
        return AIResponse.model_validate(payload)
    except ValidationError as exc:
        raise AIResponseValidationError(f"AI response failed schema validation: {exc}") from exc


# A Gemini `response_schema` (OpenAPI 3.0 subset, per the google-genai SDK)
# mirroring AIResponse. Kept as a plain dict — see google.genai.types.Schema
# for the accepted shape — so nothing here depends on pydantic's own JSON
# Schema export (which uses different keywords Gemini doesn't understand).
_TASK_INTENT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "id": {"type": "STRING"},
        "objective": {"type": "STRING"},
        "target": {"type": "STRING"},
        "targetType": {"type": "STRING", "enum": [t.value for t in TargetType]},
        "requestedAction": {"type": "STRING"},
        "constraints": {"type": "ARRAY", "items": {"type": "STRING"}},
        "authorizationStatus": {"type": "STRING", "enum": [s.value for s in AuthorizationState]},
        "riskLevel": {"type": "STRING", "enum": [r.value for r in RiskLevel]},
        "requiresApproval": {"type": "STRING", "enum": [a.value for a in ApprovalRequirement]},
        "missingInformation": {
            "type": "ARRAY",
            "items": {"type": "STRING", "enum": [m.value for m in MissingInfoField]},
        },
    },
    "required": [
        "id",
        "objective",
        "target",
        "targetType",
        "requestedAction",
        "authorizationStatus",
        "riskLevel",
        "requiresApproval",
        "missingInformation",
    ],
}

_WORKFLOW_STAGE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "key": {"type": "STRING", "enum": [k.value for k in WorkflowStageKey]},
        "label": {"type": "STRING"},
        "status": {"type": "STRING", "enum": [s.value for s in WorkflowStageStatus]},
    },
    "required": ["key", "label", "status"],
}

_TASK_PLAN_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "id": {"type": "STRING"},
        "conversationId": {"type": "STRING"},
        "taskIntent": _TASK_INTENT_SCHEMA,
        "workflow": {"type": "ARRAY", "items": _WORKFLOW_STAGE_SCHEMA},
        "status": {"type": "STRING", "enum": [s.value for s in TaskPlanStatus]},
        "createdAt": {"type": "STRING"},
    },
    "required": ["id", "conversationId", "taskIntent", "workflow", "status", "createdAt"],
}

GEMINI_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "message": {"type": "STRING"},
        "taskIntent": _TASK_INTENT_SCHEMA,
        "taskPlan": _TASK_PLAN_SCHEMA,
        "authorizationStatus": {"type": "STRING", "enum": [s.value for s in AuthorizationState]},
        "riskLevel": {"type": "STRING", "enum": [r.value for r in RiskLevel]},
        "requiresApproval": {"type": "STRING", "enum": [a.value for a in ApprovalRequirement]},
        "missingInformation": {
            "type": "ARRAY",
            "items": {"type": "STRING", "enum": [m.value for m in MissingInfoField]},
        },
        "nextAction": {"type": "STRING"},
    },
    "required": [
        "message",
        "taskIntent",
        "taskPlan",
        "authorizationStatus",
        "riskLevel",
        "requiresApproval",
        "missingInformation",
        "nextAction",
    ],
}
