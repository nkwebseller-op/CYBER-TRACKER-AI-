"""Autonomous Agent Orchestrator API.

    POST /api/agent/tasks                    -> create task
    GET  /api/agent/tasks/{id}                -> get task
    GET  /api/agent/tasks                     -> list tasks
    POST /api/agent/tasks/{id}/step           -> advance one action
    POST /api/agent/tasks/{id}/pause
    POST /api/agent/tasks/{id}/resume
    POST /api/agent/tasks/{id}/cancel
    POST /api/agent/tasks/{id}/approve
    POST /api/agent/tasks/{id}/reject
    POST /api/agent/tasks/{id}/clarify
    GET  /api/agent/tasks/{id}/events

There is no endpoint that accepts a command, argv, or arbitrary tool
invocation — every action the agent takes still goes through
AgentPolicyGate -> PolicyEngine -> TerminalEngine/ToolInstallationService,
exactly as directly calling those APIs would; this layer only adds
autonomous *reasoning about which of those already-controlled actions to
take next*, never a new execution surface.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from services.agent_orchestrator.errors import AgentOrchestratorError
from services.agent_orchestrator.events import AgentEventBus
from services.agent_orchestrator.models import AgentTaskState
from services.agent_orchestrator.orchestrator import AgentOrchestrator
from services.policy.engine import TargetScope
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_orchestrator import get_agent_event_bus, get_agent_orchestrator
from app.core.errors import CyberAIError
from app.db.models import Target
from app.db.session import get_db
from app.schemas.agent import (
    AgentEventResponse,
    AgentTaskResponse,
    ApproveActionRequest,
    ClarificationRequest,
    CreateAgentTaskRequest,
    RejectActionRequest,
    StepRequest,
)

router = APIRouter(prefix="/agent", tags=["agent"])

_ERROR_STATUS_BY_CODE = {
    "task_not_found": 404,
    "invalid_state_transition": 409,
    "approval_required": 409,
    "not_waiting_for_approval": 409,
    "budget_exceeded": 409,
    "authorization_required": 403,
    "out_of_scope": 403,
    "invalid_decision": 422,
    "concurrent_task_limit": 429,
}


class AgentOrchestratorHTTPError(CyberAIError):
    def __init__(self, exc: AgentOrchestratorError) -> None:
        super().__init__(str(exc))
        self.code = exc.code.value
        self.status_code = _ERROR_STATUS_BY_CODE.get(exc.code.value, 400)


async def _target_scope(db: AsyncSession, target_id: UUID | None) -> TargetScope | None:
    if target_id is None:
        return None
    target = await db.get(Target, target_id)
    if target is None:
        return None
    return TargetScope(id=target.id, is_active=target.is_active, expires_at=target.expires_at)


def _task_response(state: AgentTaskState, budget_status: dict) -> AgentTaskResponse:
    return AgentTaskResponse.model_validate(
        {
            "id": state.id,
            "objective": state.objective,
            "target": state.target,
            "targetType": state.target_type,
            "authorizationStatus": state.authorization_status,
            "phase": state.phase,
            "actions": [
                {
                    "id": a.id,
                    "actionType": a.action_type,
                    "tool": a.tool,
                    "capability": a.capability,
                    "requiresApproval": a.requires_approval,
                    "approvalState": a.approval_state,
                    "resultSummary": a.result_summary,
                    "errorCategory": a.error_category,
                    "confidence": a.confidence,
                }
                for a in state.actions
            ],
            "observations": [
                {"id": e.id, "kind": e.kind, "summary": e.summary} for e in state.observations
            ],
            "findings": [
                {"id": e.id, "kind": e.kind, "summary": e.summary} for e in state.findings
            ],
            "errors": [e.message for e in state.errors],
            "selectedTools": state.selected_tools,
            "confidence": state.confidence,
            "unknowns": state.unknowns,
            "clarificationQuestion": state.clarification_question,
            "pendingActionId": state.pending_action_id,
            "budget": budget_status,
            "createdAt": state.created_at,
            "updatedAt": state.updated_at,
        }
    )


@router.post("/tasks", response_model=AgentTaskResponse, status_code=201)
async def create_task(
    request: CreateAgentTaskRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
) -> AgentTaskResponse:
    authorization_status = request.authorization_status
    if request.target_id is not None:
        scope = await _target_scope(db, request.target_id)
        if scope is not None and scope.is_authorized_now():
            authorization_status = "AUTHORIZED"
        elif scope is not None:
            authorization_status = "NOT_AUTHORIZED"

    try:
        state = await orchestrator.create_task(
            objective=request.objective,
            user_request=request.user_request,
            target=request.target,
            target_type=request.target_type,
            target_id=request.target_id,
            authorization_status=authorization_status,
            scope=request.scope,
        )
    except AgentOrchestratorError as exc:
        raise AgentOrchestratorHTTPError(exc) from exc
    return _task_response(state, orchestrator.budget_status(state))


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
async def get_task(
    task_id: UUID, orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator)
) -> AgentTaskResponse:
    try:
        state = await orchestrator.get_task(task_id)
    except AgentOrchestratorError as exc:
        raise AgentOrchestratorHTTPError(exc) from exc
    return _task_response(state, orchestrator.budget_status(state))


@router.get("/tasks", response_model=list[AgentTaskResponse])
async def list_tasks(
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
) -> list[AgentTaskResponse]:
    states = await orchestrator.list_tasks()
    return [_task_response(s, orchestrator.budget_status(s)) for s in states]


@router.post("/tasks/{task_id}/step", response_model=AgentTaskResponse)
async def step_task(
    task_id: UUID,
    request: StepRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
) -> AgentTaskResponse:
    target_scope = await _target_scope(db, request.target_id)
    try:
        state = await orchestrator.step(
            task_id, target_scope=target_scope, platform=request.platform
        )
    except AgentOrchestratorError as exc:
        raise AgentOrchestratorHTTPError(exc) from exc
    return _task_response(state, orchestrator.budget_status(state))


@router.post("/tasks/{task_id}/pause", response_model=AgentTaskResponse)
async def pause_task(
    task_id: UUID, orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator)
) -> AgentTaskResponse:
    try:
        state = await orchestrator.pause(task_id)
    except AgentOrchestratorError as exc:
        raise AgentOrchestratorHTTPError(exc) from exc
    return _task_response(state, orchestrator.budget_status(state))


@router.post("/tasks/{task_id}/resume", response_model=AgentTaskResponse)
async def resume_task(
    task_id: UUID, orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator)
) -> AgentTaskResponse:
    try:
        state = await orchestrator.resume(task_id)
    except AgentOrchestratorError as exc:
        raise AgentOrchestratorHTTPError(exc) from exc
    return _task_response(state, orchestrator.budget_status(state))


@router.post("/tasks/{task_id}/cancel", response_model=AgentTaskResponse)
async def cancel_task(
    task_id: UUID, orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator)
) -> AgentTaskResponse:
    try:
        state = await orchestrator.cancel(task_id)
    except AgentOrchestratorError as exc:
        raise AgentOrchestratorHTTPError(exc) from exc
    return _task_response(state, orchestrator.budget_status(state))


@router.post("/tasks/{task_id}/approve", response_model=AgentTaskResponse)
async def approve_task_action(
    task_id: UUID,
    request: ApproveActionRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
) -> AgentTaskResponse:
    try:
        state = await orchestrator.approve_action(task_id, approved_by=request.approved_by)
    except AgentOrchestratorError as exc:
        raise AgentOrchestratorHTTPError(exc) from exc
    return _task_response(state, orchestrator.budget_status(state))


@router.post("/tasks/{task_id}/reject", response_model=AgentTaskResponse)
async def reject_task_action(
    task_id: UUID,
    request: RejectActionRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
) -> AgentTaskResponse:
    try:
        state = await orchestrator.reject_action(task_id, reason=request.reason)
    except AgentOrchestratorError as exc:
        raise AgentOrchestratorHTTPError(exc) from exc
    return _task_response(state, orchestrator.budget_status(state))


@router.post("/tasks/{task_id}/clarify", response_model=AgentTaskResponse)
async def clarify_task(
    task_id: UUID,
    request: ClarificationRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
) -> AgentTaskResponse:
    try:
        state = await orchestrator.provide_clarification(task_id, request.answer)
    except AgentOrchestratorError as exc:
        raise AgentOrchestratorHTTPError(exc) from exc
    return _task_response(state, orchestrator.budget_status(state))


@router.get("/tasks/{task_id}/events", response_model=list[AgentEventResponse])
async def get_task_events(
    task_id: UUID, event_bus: AgentEventBus = Depends(get_agent_event_bus)
) -> list[AgentEventResponse]:
    events = event_bus.events_for(task_id)
    return [
        AgentEventResponse.model_validate(
            {
                "id": e.id,
                "eventType": e.event_type,
                "data": e.data,
                "createdAt": e.created_at,
            }
        )
        for e in events
    ]
