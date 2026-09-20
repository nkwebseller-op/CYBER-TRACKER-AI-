"""SQLAlchemy-backed implementation of
`services.agent_orchestrator.registry.AgentTaskRegistry` — same
persistence-boundary split as every other app/db/*_repository.py:
services/ never imports SQLAlchemy, apps/api translates to/from the ORM
at this one seam. The full `AgentTaskState` is serialized as JSON on
`AgentTaskRecord.state_snapshot`; that snapshot is what makes a task
resumable after a restart — `_row_to_state` reconstructs the exact same
dataclass tree `AgentOrchestrator` was working with.
"""

from datetime import UTC, datetime
from uuid import UUID

from services.agent_orchestrator.actions import ActionType
from services.agent_orchestrator.errors import TaskNotFoundError
from services.agent_orchestrator.models import (
    AgentAction,
    AgentError,
    AgentPhase,
    AgentTaskState,
    ApprovalState,
    CancellationState,
    Evidence,
    EvidenceKind,
    RecoveryAttempt,
    Subtask,
    SubtaskStatus,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentPhaseDb
from app.db.models import AgentTaskRecord as TaskRow


def _dt(value: str | None):
    return datetime.fromisoformat(value) if value else None


def _evidence_to_json(e: Evidence) -> dict:
    return {
        "id": str(e.id),
        "kind": e.kind.value,
        "summary": e.summary,
        "sourceActionId": str(e.source_action_id) if e.source_action_id else None,
        "createdAt": e.created_at.isoformat(),
    }


def _evidence_from_json(data: dict) -> Evidence:
    return Evidence(
        id=UUID(data["id"]),
        kind=EvidenceKind(data["kind"]),
        summary=data["summary"],
        source_action_id=UUID(data["sourceActionId"]) if data.get("sourceActionId") else None,
        created_at=_dt(data["createdAt"]),
    )


def _action_to_json(a: AgentAction) -> dict:
    return {
        "id": str(a.id),
        "actionType": a.action_type.value,
        "target": a.target,
        "capability": a.capability,
        "tool": a.tool,
        "parameters": a.parameters,
        "requiresApproval": a.requires_approval,
        "approvalState": a.approval_state.value,
        "expectedResult": a.expected_result,
        "verificationRequirement": a.verification_requirement,
        "reasoningSummary": a.reasoning_summary,
        "confidence": a.confidence,
        "resultSummary": a.result_summary,
        "errorCategory": a.error_category,
        "createdAt": a.created_at.isoformat(),
        "completedAt": a.completed_at.isoformat() if a.completed_at else None,
    }


def _action_from_json(data: dict) -> AgentAction:
    return AgentAction(
        id=UUID(data["id"]),
        action_type=ActionType(data["actionType"]),
        target=data.get("target"),
        capability=data.get("capability"),
        tool=data.get("tool"),
        parameters=data.get("parameters") or {},
        requires_approval=data.get("requiresApproval", False),
        approval_state=ApprovalState(data.get("approvalState", "NOT_REQUIRED")),
        expected_result=data.get("expectedResult", ""),
        verification_requirement=data.get("verificationRequirement", ""),
        reasoning_summary=data.get("reasoningSummary", ""),
        confidence=data.get("confidence", 0.0),
        result_summary=data.get("resultSummary"),
        error_category=data.get("errorCategory"),
        created_at=_dt(data["createdAt"]),
        completed_at=_dt(data.get("completedAt")),
    )


def _subtask_to_json(s: Subtask) -> dict:
    return {
        "id": str(s.id),
        "description": s.description,
        "category": s.category,
        "status": s.status.value,
        "dependsOn": [str(d) for d in s.depends_on],
    }


def _subtask_from_json(data: dict) -> Subtask:
    return Subtask(
        id=UUID(data["id"]),
        description=data.get("description", ""),
        category=data.get("category", ""),
        status=SubtaskStatus(data.get("status", "PENDING")),
        depends_on=tuple(UUID(d) for d in data.get("dependsOn", [])),
    )


def _error_to_json(e: AgentError) -> dict:
    return {
        "id": str(e.id),
        "actionId": str(e.action_id) if e.action_id else None,
        "category": e.category,
        "message": e.message,
        "createdAt": e.created_at.isoformat(),
    }


def _error_from_json(data: dict) -> AgentError:
    return AgentError(
        id=UUID(data["id"]),
        action_id=UUID(data["actionId"]) if data.get("actionId") else None,
        category=data.get("category", "unknown"),
        message=data.get("message", ""),
        created_at=_dt(data["createdAt"]),
    )


def _recovery_to_json(r: RecoveryAttempt) -> dict:
    return {
        "id": str(r.id),
        "actionId": str(r.action_id),
        "errorCategory": r.error_category,
        "strategy": r.strategy,
        "outcome": r.outcome,
        "createdAt": r.created_at.isoformat(),
    }


def _recovery_from_json(data: dict) -> RecoveryAttempt:
    return RecoveryAttempt(
        id=UUID(data["id"]),
        action_id=UUID(data["actionId"]),
        error_category=data["errorCategory"],
        strategy=data["strategy"],
        outcome=data.get("outcome", "pending"),
        created_at=_dt(data["createdAt"]),
    )


def state_to_snapshot(state: AgentTaskState) -> dict:
    return {
        "id": str(state.id),
        "objective": state.objective,
        "userRequest": state.user_request,
        "target": state.target,
        "targetType": state.target_type,
        "authorizationStatus": state.authorization_status,
        "targetId": str(state.target_id) if state.target_id else None,
        "scope": state.scope,
        "phase": state.phase.value,
        "currentSubtaskId": str(state.current_subtask_id) if state.current_subtask_id else None,
        "subtasks": [_subtask_to_json(s) for s in state.subtasks],
        "selectedTools": state.selected_tools,
        "toolCapabilities": state.tool_capabilities,
        "installationState": state.installation_state,
        "executionState": state.execution_state,
        "actions": [_action_to_json(a) for a in state.actions],
        "observations": [_evidence_to_json(e) for e in state.observations],
        "findings": [_evidence_to_json(e) for e in state.findings],
        "evidence": [_evidence_to_json(e) for e in state.evidence],
        "outputs": state.outputs,
        "errors": [_error_to_json(e) for e in state.errors],
        "recoveryAttempts": [_recovery_to_json(r) for r in state.recovery_attempts],
        "verificationResults": state.verification_results,
        "confidence": state.confidence,
        "assumptions": state.assumptions,
        "unknowns": state.unknowns,
        "nextAction": state.next_action,
        "approvalState": state.approval_state.value,
        "pendingActionId": str(state.pending_action_id) if state.pending_action_id else None,
        "cancellationState": state.cancellation_state.value,
        "clarificationQuestion": state.clarification_question,
        "actionCount": state.action_count,
        "modelCallCount": state.model_call_count,
        "installationCount": state.installation_count,
        "retryCountByAction": state.retry_count_by_action,
        "lastErrorSignature": state.last_error_signature,
        "createdAt": state.created_at.isoformat(),
        "updatedAt": state.updated_at.isoformat(),
        "startedAt": state.started_at.isoformat() if state.started_at else None,
        "completedAt": state.completed_at.isoformat() if state.completed_at else None,
    }


def snapshot_to_state(data: dict) -> AgentTaskState:
    return AgentTaskState(
        id=UUID(data["id"]),
        objective=data["objective"],
        user_request=data.get("userRequest", ""),
        target=data.get("target"),
        target_type=data.get("targetType"),
        authorization_status=data.get("authorizationStatus", "UNKNOWN"),
        target_id=UUID(data["targetId"]) if data.get("targetId") else None,
        scope=data.get("scope") or [],
        phase=AgentPhase(data["phase"]),
        current_subtask_id=UUID(data["currentSubtaskId"]) if data.get("currentSubtaskId") else None,
        subtasks=[_subtask_from_json(s) for s in data.get("subtasks", [])],
        selected_tools=data.get("selectedTools") or [],
        tool_capabilities=data.get("toolCapabilities") or {},
        installation_state=data.get("installationState") or {},
        execution_state=data.get("executionState", "idle"),
        actions=[_action_from_json(a) for a in data.get("actions", [])],
        observations=[_evidence_from_json(e) for e in data.get("observations", [])],
        findings=[_evidence_from_json(e) for e in data.get("findings", [])],
        evidence=[_evidence_from_json(e) for e in data.get("evidence", [])],
        outputs=data.get("outputs") or [],
        errors=[_error_from_json(e) for e in data.get("errors", [])],
        recovery_attempts=[_recovery_from_json(r) for r in data.get("recoveryAttempts", [])],
        verification_results=data.get("verificationResults") or {},
        confidence=data.get("confidence", 0.0),
        assumptions=data.get("assumptions") or [],
        unknowns=data.get("unknowns") or [],
        next_action=data.get("nextAction"),
        approval_state=ApprovalState(data.get("approvalState", "NOT_REQUIRED")),
        pending_action_id=UUID(data["pendingActionId"]) if data.get("pendingActionId") else None,
        cancellation_state=CancellationState(data.get("cancellationState", "NONE")),
        clarification_question=data.get("clarificationQuestion"),
        action_count=data.get("actionCount", 0),
        model_call_count=data.get("modelCallCount", 0),
        installation_count=data.get("installationCount", 0),
        retry_count_by_action=data.get("retryCountByAction") or {},
        last_error_signature=data.get("lastErrorSignature"),
        created_at=_dt(data["createdAt"]),
        updated_at=_dt(data["updatedAt"]),
        started_at=_dt(data.get("startedAt")),
        completed_at=_dt(data.get("completedAt")),
    )


def _row_to_state(row: TaskRow) -> AgentTaskState:
    return snapshot_to_state(row.state_snapshot)


class SqlAlchemyAgentTaskRegistry:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, state: AgentTaskState) -> AgentTaskState:
        row = TaskRow(
            id=state.id,
            objective=state.objective,
            target=state.target,
            target_id=state.target_id,
            phase=AgentPhaseDb(state.phase.value),
            state_snapshot=state_to_snapshot(state),
        )
        self._db.add(row)
        await self._db.commit()
        await self._db.refresh(row)
        return _row_to_state(row)

    async def get(self, task_id: UUID) -> AgentTaskState:
        row = await self._db.get(TaskRow, task_id)
        if row is None:
            raise TaskNotFoundError(f"Agent task {task_id} was not found.")
        return _row_to_state(row)

    async def save(self, state: AgentTaskState) -> AgentTaskState:
        row = await self._db.get(TaskRow, state.id)
        if row is None:
            raise TaskNotFoundError(f"Agent task {state.id} was not found.")
        row.phase = AgentPhaseDb(state.phase.value)
        row.state_snapshot = state_to_snapshot(state)
        row.updated_at = datetime.now(UTC)
        await self._db.commit()
        await self._db.refresh(row)
        return _row_to_state(row)

    async def list_all(self) -> list[AgentTaskState]:
        result = await self._db.execute(select(TaskRow))
        return [_row_to_state(r) for r in result.scalars().all()]

    async def count_active(self) -> int:
        terminal = {"CANCELLED", "COMPLETED", "FAILED", "BLOCKED"}
        rows = (await self._db.execute(select(TaskRow))).scalars().all()
        return sum(1 for r in rows if r.phase.value not in terminal)
