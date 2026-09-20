"""SQLAlchemy-backed implementation of `services.tools.registry.ToolRegistry`.

Translates between the framework-independent `services.tools.models`
dataclasses and the `app.db.models.Tool` ORM row — the same persistence-
boundary split used throughout this codebase (services/ never imports
SQLAlchemy or FastAPI). Unit tests use `services.tools.registry.
InMemoryToolRegistry` instead of this class, exactly as terminal/termux
tests use in-memory fakes rather than a live database.
"""

from datetime import UTC, datetime
from uuid import UUID

from services.policy.engine import RiskTier as ServiceRiskTier
from services.tools.errors import DuplicateToolError, ToolNotFoundError
from services.tools.models import (
    SourceProvenance,
    SourceType,
    ToolCategory,
    ToolRecord,
    TrustStatus,
    VerificationReport,
    VerificationResult,
    VerificationStage,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RiskTier as DbRiskTier
from app.db.models import Tool as ToolRow
from app.db.models import ToolCategory as DbToolCategory
from app.db.models import ToolSourceType as DbToolSourceType
from app.db.models import ToolTrustStatus as DbToolTrustStatus


def _report_to_json(report: VerificationReport) -> dict:
    return {
        "results": {stage.value: result.value for stage, result in report.results.items()},
        "notes": {stage.value: note for stage, note in report.notes.items()},
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
    }


def _report_from_json(data: dict | None) -> VerificationReport:
    data = data or {}
    results = {
        VerificationStage(stage): VerificationResult(result)
        for stage, result in (data.get("results") or {}).items()
    }
    notes = dict((data.get("notes") or {}).items())
    notes = {VerificationStage(stage): note for stage, note in notes.items()}
    completed_at = (
        datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
    )
    return VerificationReport(results=results, notes=notes, completed_at=completed_at)


def _row_to_record(row: ToolRow) -> ToolRecord:
    return ToolRecord(
        id=row.id,
        name=row.name,
        display_name=row.display_name,
        description=row.description,
        category=ToolCategory(row.category.value),
        capabilities=tuple(row.capabilities or ()),
        supported_platforms=tuple(row.supported_platforms or ()),
        provenance=SourceProvenance(
            source_type=SourceType(row.source_type.value),
            source_url=row.source_url,
            repository_url=row.repository_url,
            documentation_url=row.documentation_url,
            publisher=row.publisher,
            discovered_version=row.discovered_version,
            discovered_at=row.discovered_at,
        ),
        version=row.version,
        license=row.license,
        installation_method=row.installation_method,
        entrypoint=row.entrypoint,
        dependencies=tuple(row.dependencies or ()),
        required_permissions=tuple(row.required_permissions or ()),
        risk_level=ServiceRiskTier(row.risk_level.value),
        trust_status=TrustStatus(row.trust_status.value),
        verification=_report_from_json(row.verification_report),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _record_to_row(record: ToolRecord) -> ToolRow:
    return ToolRow(
        id=record.id,
        name=record.name,
        display_name=record.display_name,
        description=record.description,
        category=DbToolCategory(record.category.value),
        capabilities=list(record.capabilities),
        supported_platforms=list(record.supported_platforms),
        source_type=DbToolSourceType(record.provenance.source_type.value),
        source_url=record.provenance.source_url,
        documentation_url=record.provenance.documentation_url,
        repository_url=record.provenance.repository_url,
        publisher=record.provenance.publisher,
        discovered_version=record.provenance.discovered_version,
        discovered_at=record.provenance.discovered_at,
        version=record.version,
        license=record.license,
        installation_method=record.installation_method,
        entrypoint=record.entrypoint,
        dependencies=list(record.dependencies),
        required_permissions=list(record.required_permissions),
        risk_level=DbRiskTier(record.risk_level.value),
        trust_status=DbToolTrustStatus(record.trust_status.value),
        verification_report=_report_to_json(record.verification),
    )


class SqlAlchemyToolRegistry:
    """Implements `services.tools.registry.ToolRegistry` against a real
    database session. Constructed per-request via FastAPI's `Depends`,
    the same way every other route gets its `AsyncSession`."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, tool: ToolRecord) -> ToolRecord:
        row = _record_to_row(tool)
        self._db.add(row)
        try:
            await self._db.commit()
        except IntegrityError as exc:
            await self._db.rollback()
            raise DuplicateToolError(f"A tool named '{tool.name}' is already registered.") from exc
        await self._db.refresh(row)
        return _row_to_record(row)

    async def get(self, tool_id: UUID) -> ToolRecord:
        row = await self._db.get(ToolRow, tool_id)
        if row is None:
            raise ToolNotFoundError(f"Tool {tool_id} was not found.")
        return _row_to_record(row)

    async def get_by_name(self, name: str) -> ToolRecord | None:
        result = await self._db.execute(select(ToolRow).where(ToolRow.name == name))
        row = result.scalar_one_or_none()
        return _row_to_record(row) if row else None

    async def list(
        self,
        *,
        category: ToolCategory | None = None,
        platform: str | None = None,
        trust_status: TrustStatus | None = None,
        search: str | None = None,
    ) -> list[ToolRecord]:
        query = select(ToolRow)
        if category is not None:
            query = query.where(ToolRow.category == DbToolCategory(category.value))
        if trust_status is not None:
            query = query.where(ToolRow.trust_status == DbToolTrustStatus(trust_status.value))
        result = await self._db.execute(query)
        rows = list(result.scalars().all())

        records = [_row_to_record(row) for row in rows]
        if platform is not None:
            records = [r for r in records if platform in r.supported_platforms]
        if search:
            needle = search.lower()
            records = [
                r
                for r in records
                if needle in r.name.lower()
                or needle in r.display_name.lower()
                or needle in r.description.lower()
                or any(needle in c.lower() for c in r.capabilities)
            ]
        return records

    async def update_trust_status(self, tool_id: UUID, status: TrustStatus) -> ToolRecord:
        row = await self._db.get(ToolRow, tool_id)
        if row is None:
            raise ToolNotFoundError(f"Tool {tool_id} was not found.")
        row.trust_status = DbToolTrustStatus(status.value)
        row.updated_at = datetime.now(UTC)
        await self._db.commit()
        await self._db.refresh(row)
        return _row_to_record(row)

    async def record_verification(self, tool_id: UUID, report: VerificationReport) -> ToolRecord:
        row = await self._db.get(ToolRow, tool_id)
        if row is None:
            raise ToolNotFoundError(f"Tool {tool_id} was not found.")
        row.verification_report = _report_to_json(report)
        row.updated_at = datetime.now(UTC)
        await self._db.commit()
        await self._db.refresh(row)
        return _row_to_record(row)
