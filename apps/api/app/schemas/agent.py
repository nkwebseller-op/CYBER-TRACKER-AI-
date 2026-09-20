"""Pydantic contracts for the Agent Orchestrator API. No endpoint accepts
raw argv, a shell string, or an unrestricted "run this" instruction —
task creation only takes an objective/target/authorization declaration,
and every subsequent transition (approve/reject/clarify/pause/resume/
cancel) operates on an existing, policy-gated task."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from services.agent_orchestrator.actions import ActionType
from services.agent_orchestrator.models import AgentPhase, ApprovalState, EvidenceKind


class CreateAgentTaskRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=2000)
    user_request: str = Field(alias="userRequest", min_length=1, max_length=2000)
    target: str | None = None
    target_type: str | None = Field(default=None, alias="targetType")
    target_id: UUID | None = Field(default=None, alias="targetId")
    authorization_status: str = Field(default="UNKNOWN", alias="authorizationStatus")
    scope: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class StepRequest(BaseModel):
    target_id: UUID | None = Field(default=None, alias="targetId")
    platform: str = "LINUX"

    model_config = ConfigDict(populate_by_name=True)


class ApproveActionRequest(BaseModel):
    approved_by: str = Field(alias="approvedBy", min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class RejectActionRequest(BaseModel):
    reason: str = Field(min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class ClarificationRequest(BaseModel):
    answer: str = Field(min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class AgentActionResponse(BaseModel):
    id: UUID
    action_type: ActionType = Field(alias="actionType")
    tool: str | None = None
    capability: str | None = None
    requires_approval: bool = Field(alias="requiresApproval")
    approval_state: ApprovalState = Field(alias="approvalState")
    result_summary: str | None = Field(default=None, alias="resultSummary")
    error_category: str | None = Field(default=None, alias="errorCategory")
    confidence: float

    model_config = ConfigDict(populate_by_name=True)


class EvidenceResponse(BaseModel):
    id: UUID
    kind: EvidenceKind
    summary: str

    model_config = ConfigDict(populate_by_name=True)


class AgentTaskResponse(BaseModel):
    id: UUID
    objective: str
    target: str | None = None
    target_type: str | None = Field(default=None, alias="targetType")
    authorization_status: str = Field(alias="authorizationStatus")
    phase: AgentPhase
    actions: list[AgentActionResponse]
    observations: list[EvidenceResponse]
    findings: list[EvidenceResponse]
    errors: list[str]
    selected_tools: list[str] = Field(alias="selectedTools")
    confidence: float
    unknowns: list[str]
    clarification_question: str | None = Field(default=None, alias="clarificationQuestion")
    pending_action_id: UUID | None = Field(default=None, alias="pendingActionId")
    budget: dict
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class AgentEventResponse(BaseModel):
    id: UUID
    event_type: str = Field(alias="eventType")
    data: dict
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)
