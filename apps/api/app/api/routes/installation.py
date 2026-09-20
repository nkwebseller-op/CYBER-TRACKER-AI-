"""Tool Installation & Environment Preparation API.

    GET  /api/installations/readiness       -> 11-point readiness checklist
    POST /api/installations                 -> generate plan + create request
    POST /api/installations/{id}/approve    -> explicit human approval
    POST /api/installations/{id}/reject
    POST /api/installations/{id}/start      -> runs through TerminalEngine
    POST /api/installations/{id}/cancel
    GET  /api/installations/{id}
    GET  /api/installations                 -> history
    GET  /api/installations/installed       -> installed tools

There is no endpoint that accepts raw argv, a shell string, or a URL to
fetch-and-run — every install/verify command is built exclusively by
services.terminal.command_templates from a tool already APPROVED in the
Trusted Tool Registry, and every execution goes through the unchanged
TerminalEngine -> PolicyEngine -> PlatformAdapter pipeline.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from services.installation.errors import InstallationError
from services.installation.models import InstallationRequest
from services.installation.service import ToolInstallationService
from services.policy.engine import TargetScope
from services.terminal.engine import TerminalEngine
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.installation import get_installation_service
from app.core.terminal_engine import get_terminal_engine
from app.db.models import Target
from app.db.session import get_db
from app.schemas.installation import (
    ApproveInstallationRequest,
    InstallationRequestResponse,
    ReadinessResponse,
    RejectInstallationRequest,
    RequestInstallationRequest,
    StartInstallationRequest,
)

router = APIRouter(prefix="/installations", tags=["installations"])

_ERROR_STATUS_BY_CODE = {
    "installation_not_found": 404,
    "tool_not_approved": 403,
    "unsupported_platform": 400,
    "package_manager_unavailable": 400,
    "policy_denied": 403,
    "approval_required": 409,
    "invalid_state_transition": 409,
    "retry_limit_exceeded": 409,
}


def _http_error(exc: InstallationError) -> HTTPException:
    status_code = _ERROR_STATUS_BY_CODE.get(exc.code.value, 400)
    detail = {"code": exc.code.value, "message": str(exc)}
    return HTTPException(status_code=status_code, detail=detail)


async def _target_scope(db: AsyncSession, target_id: UUID) -> TargetScope:
    target = await db.get(Target, target_id)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "target_not_found", "message": "The requested target does not exist."},
        )
    return TargetScope(id=target.id, is_active=target.is_active, expires_at=target.expires_at)


def _request_response(request: InstallationRequest) -> InstallationRequestResponse:
    return InstallationRequestResponse.model_validate(
        {
            "id": request.id,
            "toolId": request.tool_id,
            "targetId": request.target_id,
            "state": request.state,
            "plan": _plan_dict(request) if request.plan else None,
            "approvedBy": request.approved_by,
            "approvedAt": request.approved_at,
            "rejectionReason": request.rejection_reason,
            "attempts": [
                {
                    "attemptNumber": a.attempt_number,
                    "startedAt": a.started_at,
                    "completedAt": a.completed_at,
                    "exitCode": a.exit_code,
                    "stdout": a.stdout,
                    "stderr": a.stderr,
                    "durationSeconds": a.duration_seconds,
                    "errorCategory": a.error_category,
                }
                for a in request.attempts
            ],
            "verification": (
                {
                    "executableFound": request.verification.executable_found,
                    "versionOutput": request.verification.version_output,
                    "checks": request.verification.checks,
                    "verified": request.verification.verified,
                }
                if request.verification
                else None
            ),
            "errorMessage": request.error_message,
            "createdAt": request.created_at,
            "updatedAt": request.updated_at,
        }
    )


def _plan_dict(request: InstallationRequest) -> dict:
    plan = request.plan
    return {
        "toolId": plan.tool_id,
        "toolName": plan.tool_name,
        "platform": plan.platform,
        "architecture": plan.architecture,
        "version": plan.version,
        "packageManager": plan.package_manager,
        "dependencies": [
            {
                "name": d.name,
                "requiredVersion": d.required_version,
                "foundVersion": d.found_version,
                "status": d.status.value,
                "note": d.note,
            }
            for d in plan.dependencies
        ],
        "prerequisites": plan.prerequisites,
        "requiredPermissions": plan.required_permissions,
        "installationSteps": [
            {
                "description": s.description,
                "packageManager": s.package_manager,
                "actionType": s.action_type,
                "packageName": s.package_name,
                "version": s.version,
            }
            for s in plan.installation_steps
        ],
        "verificationSteps": plan.verification_steps,
        "riskLevel": plan.risk_level,
        "approvalRequired": plan.approval_required,
        "estimatedChanges": plan.estimated_changes,
        "rollbackInformation": plan.rollback_information,
    }


@router.get("/readiness", response_model=ReadinessResponse)
async def check_readiness(
    tool_id: UUID,
    target_id: UUID,
    platform: str,
    db: AsyncSession = Depends(get_db),
    service: ToolInstallationService = Depends(get_installation_service),
) -> ReadinessResponse:
    target_scope = await _target_scope(db, target_id)
    report = await service.check_readiness(tool_id, target_scope=target_scope, platform=platform)
    return ReadinessResponse(
        ready=report.ready,
        checks=[
            {"name": c.name, "status": c.status, "detail": c.detail, "critical": c.critical}
            for c in report.checks
        ],
    )


@router.post("", response_model=InstallationRequestResponse, status_code=201)
async def request_installation(
    request: RequestInstallationRequest,
    db: AsyncSession = Depends(get_db),
    service: ToolInstallationService = Depends(get_installation_service),
) -> InstallationRequestResponse:
    target_scope = await _target_scope(db, request.target_id)
    created = await service.request_installation(
        request.tool_id,
        target_scope=target_scope,
        platform=request.platform,
        requested_by=request.requested_by,
    )
    return _request_response(created)


@router.get("/installed", response_model=list[InstallationRequestResponse])
async def list_installed(
    service: ToolInstallationService = Depends(get_installation_service),
) -> list[InstallationRequestResponse]:
    installed = await service.list_installed()
    return [_request_response(r) for r in installed]


@router.get("", response_model=list[InstallationRequestResponse])
async def list_installations(
    service: ToolInstallationService = Depends(get_installation_service),
) -> list[InstallationRequestResponse]:
    all_requests = await service.list_installations()
    return [_request_response(r) for r in all_requests]


@router.get("/{request_id}", response_model=InstallationRequestResponse)
async def get_installation(
    request_id: UUID, service: ToolInstallationService = Depends(get_installation_service)
) -> InstallationRequestResponse:
    try:
        found = await service.get_request(request_id)
    except InstallationError as exc:
        raise _http_error(exc) from exc
    return _request_response(found)


@router.post("/{request_id}/approve", response_model=InstallationRequestResponse)
async def approve_installation(
    request_id: UUID,
    body: ApproveInstallationRequest,
    service: ToolInstallationService = Depends(get_installation_service),
) -> InstallationRequestResponse:
    try:
        updated = await service.approve(request_id, approved_by=body.approved_by)
    except InstallationError as exc:
        raise _http_error(exc) from exc
    return _request_response(updated)


@router.post("/{request_id}/reject", response_model=InstallationRequestResponse)
async def reject_installation(
    request_id: UUID,
    body: RejectInstallationRequest,
    service: ToolInstallationService = Depends(get_installation_service),
) -> InstallationRequestResponse:
    try:
        updated = await service.reject(request_id, reason=body.reason)
    except InstallationError as exc:
        raise _http_error(exc) from exc
    return _request_response(updated)


@router.post("/{request_id}/start", response_model=InstallationRequestResponse)
async def start_installation(
    request_id: UUID,
    body: StartInstallationRequest,
    db: AsyncSession = Depends(get_db),
    service: ToolInstallationService = Depends(get_installation_service),
    engine: TerminalEngine = Depends(get_terminal_engine),
) -> InstallationRequestResponse:
    target_scope = await _target_scope(db, body.target_id)
    session = engine.create_session(task_id=f"install-{request_id}")
    try:
        updated = await service.start_installation(
            request_id, engine=engine, session_id=session.id, target_scope=target_scope
        )
    except InstallationError as exc:
        raise _http_error(exc) from exc
    return _request_response(updated)


@router.post("/{request_id}/cancel", response_model=InstallationRequestResponse)
async def cancel_installation(
    request_id: UUID,
    service: ToolInstallationService = Depends(get_installation_service),
    engine: TerminalEngine = Depends(get_terminal_engine),
) -> InstallationRequestResponse:
    try:
        updated = await service.cancel(request_id, engine)
    except InstallationError as exc:
        raise _http_error(exc) from exc
    return _request_response(updated)
