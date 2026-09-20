"""Terminal Engine API.

    Chat/Task Planner -> [this API] -> Policy Engine -> Terminal Engine
    -> Platform Adapter -> Controlled Process -> Result -> Audit Log

There is no endpoint that accepts raw shell text or an AI-supplied
authorization verdict. `POST /execute` only ever accepts a `taskId`,
`sessionId`, `targetId`, and a reviewed `actionType`; this route is the
one place that loads the Target, asks the real PolicyEngine for a
verdict, and — only if ALLOWed or explicitly approved — resolves a vetted
command template before calling the Terminal Engine. A DENY or an
unregistered action type never reaches the engine at all.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from services.policy.engine import ActionRequest, PolicyEngine, PolicyVerdict, TargetScope
from services.terminal.command_templates import ACTION_RISK_TIERS, resolve_command
from services.terminal.engine import TerminalEngine
from services.terminal.errors import TerminalEngineError
from services.terminal.models import TerminalCommandRequest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.terminal_engine import get_terminal_engine
from app.db.models import Target
from app.db.session import get_db
from app.schemas.terminal import (
    CommandResultResponse,
    CreateSessionRequest,
    ExecuteRequest,
    SessionResponse,
)

router = APIRouter(prefix="/terminal", tags=["terminal"])
_policy_engine = PolicyEngine()


def _session_response(session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        platform=session.platform,
        status=session.status,
        created_at=session.created_at,
        last_activity_at=session.last_activity_at,
        working_directory=session.working_directory,
        task_id=session.task_id,
    )


def _result_response(result) -> CommandResultResponse:
    return CommandResultResponse(
        command_id=result.command_id,
        session_id=result.session_id,
        status=result.status,
        platform=result.platform,
        started_at=result.started_at,
        completed_at=result.completed_at,
        duration_seconds=result.duration_seconds,
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        stdout_truncated=result.stdout_truncated,
        stderr_truncated=result.stderr_truncated,
        error_message=result.error_message,
    )


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    request: CreateSessionRequest, engine: TerminalEngine = Depends(get_terminal_engine)
) -> SessionResponse:
    try:
        session = engine.create_session(
            task_id=request.task_id, working_directory=request.working_directory
        )
    except TerminalEngineError as exc:
        detail = {"code": exc.code, "message": str(exc)}
        raise HTTPException(status_code=400, detail=detail) from exc
    return _session_response(session)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID, engine: TerminalEngine = Depends(get_terminal_engine)
) -> SessionResponse:
    try:
        session = engine.get_status(session_id)
    except TerminalEngineError as exc:
        detail = {"code": exc.code, "message": str(exc)}
        raise HTTPException(status_code=404, detail=detail) from exc
    return _session_response(session)


@router.post("/sessions/{session_id}/terminate", response_model=SessionResponse)
async def terminate_session(
    session_id: UUID, engine: TerminalEngine = Depends(get_terminal_engine)
) -> SessionResponse:
    try:
        session = engine.close_session(session_id)
    except TerminalEngineError as exc:
        detail = {"code": exc.code, "message": str(exc)}
        raise HTTPException(status_code=404, detail=detail) from exc
    return _session_response(session)


@router.get("/sessions/{session_id}/output", response_model=CommandResultResponse | None)
async def get_session_output(
    session_id: UUID, engine: TerminalEngine = Depends(get_terminal_engine)
) -> CommandResultResponse | None:
    # Confirms the session exists (raises 404 otherwise) before looking up
    # its last result, so an unknown session id doesn't quietly return null.
    engine.get_status(session_id)
    result = engine.get_last_result(session_id)
    return _result_response(result) if result else None


@router.post("/execute", response_model=CommandResultResponse)
async def execute(
    request: ExecuteRequest,
    engine: TerminalEngine = Depends(get_terminal_engine),
    db: AsyncSession = Depends(get_db),
) -> CommandResultResponse:
    target = await db.get(Target, request.target_id)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "target_not_found", "message": "The requested target does not exist."},
        )

    risk_tier = ACTION_RISK_TIERS.get(request.action_type)
    if risk_tier is None:
        message = f"Action type '{request.action_type}' is not a reviewed, executable action."
        raise HTTPException(
            status_code=403,
            detail={"code": "action_not_registered", "message": message},
        )

    target_scope = TargetScope(
        id=target.id, is_active=target.is_active, expires_at=target.expires_at
    )
    decision = _policy_engine.evaluate(
        ActionRequest(
            action_id=uuid4(),
            action_type=request.action_type,
            risk_tier=risk_tier,
            target=target_scope,
        )
    )

    if decision.verdict == PolicyVerdict.DENY:
        raise HTTPException(
            status_code=403,
            detail={"code": "policy_denied", "message": "; ".join(decision.reasons)},
        )
    if decision.verdict == PolicyVerdict.REQUIRE_APPROVAL and not request.approved:
        raise HTTPException(
            status_code=202,
            detail={
                "code": "approval_required",
                "message": "This action requires explicit human approval before it can run.",
            },
        )

    command = resolve_command(request.action_type)
    if command is None:
        # Should be unreachable given the ACTION_RISK_TIERS check above, but
        # never fall back to trusting client-supplied argv if it happens.
        raise HTTPException(
            status_code=500,
            detail={
                "code": "no_command_template",
                "message": "No executable template is registered for this action.",
            },
        )

    terminal_request = TerminalCommandRequest(
        session_id=request.session_id,
        command=command,
        authorization_context=decision,
        task_id=request.task_id,
        timeout_seconds=request.timeout_seconds,
        approved_by_user=request.approved,
    )

    try:
        result = await engine.execute(terminal_request)
    except TerminalEngineError as exc:
        detail = {"code": exc.code, "message": str(exc)}
        raise HTTPException(status_code=409, detail=detail) from exc

    return _result_response(result)
