"""SQLAlchemy-backed implementation of
`services.installation.registry.InstallationRegistry` — same
persistence-boundary split as app/db/tool_repository.py: services/ never
imports SQLAlchemy, apps/api translates to/from the ORM at this one
seam.
"""

from datetime import UTC, datetime
from uuid import UUID

from services.installation.errors import InstallationNotFoundError
from services.installation.models import (
    InstallationAttempt,
    InstallationPlan,
    InstallationRequest,
    InstallationVerification,
)
from services.installation.models import (
    InstallationState as ServiceInstallationState,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InstallationAttemptRecord, InstalledTool
from app.db.models import InstallationRequestRecord as RequestRow
from app.db.models import InstallationState as DbInstallationState


def _plan_to_json(plan: InstallationPlan | None) -> dict | None:
    if plan is None:
        return None
    return {
        "toolId": str(plan.tool_id),
        "toolName": plan.tool_name,
        "platform": plan.platform,
        "architecture": plan.architecture,
        "version": plan.version,
        "packageManager": plan.package_manager.value,
        "dependencies": [
            {"name": d.name, "status": d.status.value, "note": d.note} for d in plan.dependencies
        ],
        "prerequisites": plan.prerequisites,
        "requiredPermissions": plan.required_permissions,
        "installationSteps": [
            {
                "description": s.description,
                "packageManager": s.package_manager.value,
                "actionType": s.action_type,
                "packageName": s.package_name,
                "version": s.version,
            }
            for s in plan.installation_steps
        ],
        "verificationSteps": plan.verification_steps,
        "riskLevel": plan.risk_level.value,
        "approvalRequired": plan.approval_required,
        "estimatedChanges": plan.estimated_changes,
        "rollbackInformation": plan.rollback_information,
        "generatedAt": plan.generated_at.isoformat(),
    }


def _verification_to_json(verification: InstallationVerification | None) -> dict | None:
    if verification is None:
        return None
    return {
        "executableFound": verification.executable_found,
        "versionOutput": verification.version_output,
        "checks": verification.checks,
        "verified": verification.verified,
    }


def _verification_from_json(data: dict | None) -> InstallationVerification | None:
    if not data:
        return None
    return InstallationVerification(
        executable_found=data.get("executableFound"),
        version_output=data.get("versionOutput"),
        checks=data.get("checks") or {},
        verified=data.get("verified", False),
    )


def _row_to_request(row: RequestRow) -> InstallationRequest:
    request = InstallationRequest(
        id=row.id,
        tool_id=row.tool_id,
        target_id=row.target_id,
        session_id=row.session_id,
        requested_by=row.requested_by,
        state=ServiceInstallationState(row.state.value),
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        rejection_reason=row.rejection_reason,
        verification=_verification_from_json(row.verification),
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
    request.attempts = [
        InstallationAttempt(
            attempt_number=a.attempt_number,
            started_at=a.started_at,
            completed_at=a.completed_at,
            exit_code=a.exit_code,
            stdout=a.stdout,
            stderr=a.stderr,
            duration_seconds=a.duration_seconds,
            error_category=a.error_category,
        )
        for a in sorted(row.attempts, key=lambda a: a.attempt_number)
    ]
    # `plan` is stored as JSON for display/audit purposes; reconstructing
    # a full InstallationPlan dataclass from it isn't needed by any
    # current caller (the service holds the live plan in memory for the
    # duration of a request), so the round-trip intentionally stops here.
    return request


class SqlAlchemyInstallationRegistry:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, request: InstallationRequest) -> InstallationRequest:
        row = RequestRow(
            id=request.id,
            tool_id=request.tool_id,
            target_id=request.target_id,
            session_id=request.session_id,
            requested_by=request.requested_by,
            state=DbInstallationState(request.state.value),
            plan=_plan_to_json(request.plan),
            approved_by=request.approved_by,
            approved_at=request.approved_at,
            rejection_reason=request.rejection_reason,
            verification=_verification_to_json(request.verification),
            error_message=request.error_message,
        )
        self._db.add(row)
        await self._db.commit()
        await self._db.refresh(row)
        return _row_to_request(row)

    async def get(self, request_id: UUID) -> InstallationRequest:
        row = await self._db.get(RequestRow, request_id)
        if row is None:
            raise InstallationNotFoundError(f"Installation request {request_id} was not found.")
        return _row_to_request(row)

    async def save(self, request: InstallationRequest) -> InstallationRequest:
        row = await self._db.get(RequestRow, request.id)
        if row is None:
            raise InstallationNotFoundError(f"Installation request {request.id} was not found.")

        row.session_id = request.session_id
        row.state = DbInstallationState(request.state.value)
        row.plan = _plan_to_json(request.plan)
        row.approved_by = request.approved_by
        row.approved_at = request.approved_at
        row.rejection_reason = request.rejection_reason
        row.verification = _verification_to_json(request.verification)
        row.error_message = request.error_message
        row.updated_at = datetime.now(UTC)

        existing_attempts = {a.attempt_number for a in row.attempts}
        for attempt in request.attempts:
            if attempt.attempt_number in existing_attempts:
                continue
            self._db.add(
                InstallationAttemptRecord(
                    request_id=row.id,
                    attempt_number=attempt.attempt_number,
                    started_at=attempt.started_at,
                    completed_at=attempt.completed_at,
                    exit_code=attempt.exit_code,
                    stdout=attempt.stdout,
                    stderr=attempt.stderr,
                    duration_seconds=attempt.duration_seconds,
                    error_category=attempt.error_category,
                )
            )

        if request.state == ServiceInstallationState.INSTALLED:
            existing = await self._db.execute(
                select(InstalledTool).where(InstalledTool.installation_request_id == row.id)
            )
            if existing.scalar_one_or_none() is None and request.plan is not None:
                self._db.add(
                    InstalledTool(
                        tool_id=request.tool_id,
                        installation_request_id=row.id,
                        platform=request.plan.platform,
                        package_manager=request.plan.package_manager.value,
                        installed_version=request.plan.version,
                        verification=_verification_to_json(request.verification) or {},
                    )
                )

        await self._db.commit()
        await self._db.refresh(row)
        return _row_to_request(row)

    async def list_for_tool(self, tool_id: UUID) -> list[InstallationRequest]:
        result = await self._db.execute(select(RequestRow).where(RequestRow.tool_id == tool_id))
        return [_row_to_request(r) for r in result.scalars().all()]

    async def list_installed(self) -> list[InstallationRequest]:
        result = await self._db.execute(
            select(RequestRow).where(RequestRow.state == DbInstallationState.INSTALLED)
        )
        return [_row_to_request(r) for r in result.scalars().all()]

    async def list_all(self) -> list[InstallationRequest]:
        result = await self._db.execute(select(RequestRow))
        return [_row_to_request(r) for r in result.scalars().all()]
