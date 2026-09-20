"""ORM models for the Phase 1 data foundation.

Every execution-relevant row (PlannedAction, PolicyDecisionRecord,
ExecutionRecord, AuditLogEntry) is append-only from the application's point
of view: rows are created and later have status fields updated, but nothing
in the API layer deletes them. That's what makes the audit trail meaningful.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SecurityDomain(StrEnum):
    WEB = "web"
    API = "api"
    NETWORK = "network"
    SERVER_CONFIG = "server_config"
    CLOUD = "cloud"
    WIRELESS = "wireless"
    MOBILE = "mobile"
    VULNERABILITY = "vulnerability"
    RECONNAISSANCE = "reconnaissance"
    DEFENSIVE = "defensive"
    OTHER = "other"


class RiskTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyVerdict(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RECOVERING = "recovering"
    CANCELLED = "cancelled"


class ScopeType(StrEnum):
    DOMAIN = "domain"
    IP_RANGE = "ip_range"
    HOST = "host"
    APPLICATION = "application"
    CLOUD_ACCOUNT = "cloud_account"


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")


class UserSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    user: Mapped["User"] = relationship(back_populates="sessions")
    tasks: Mapped[list["Task"]] = relationship(back_populates="session")


class Target(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An explicitly authorized scope entry. Nothing may be executed against
    a target that does not have valid, non-expired authorization evidence."""

    __tablename__ = "targets"

    name: Mapped[str] = mapped_column(String(255))
    scope_type: Mapped[ScopeType] = mapped_column(SAEnum(ScopeType, name="scope_type"))
    scope_value: Mapped[str] = mapped_column(String(500))
    authorization_evidence: Mapped[str] = mapped_column(Text)
    authorized_by: Mapped[str] = mapped_column(String(255))
    authorized_at: Mapped[datetime]
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    tasks: Mapped[list["Task"]] = relationship(back_populates="target")


class Task(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A planned unit of work: one natural-language objective decomposed by
    the Task Planner, scoped to a single Target."""

    __tablename__ = "tasks"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_sessions.id"))
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("targets.id"))
    objective: Mapped[str] = mapped_column(Text)
    domain: Mapped[SecurityDomain] = mapped_column(SAEnum(SecurityDomain, name="security_domain"))
    status: Mapped[str] = mapped_column(String(50), default="planned")

    session: Mapped["UserSession"] = relationship(back_populates="tasks")
    target: Mapped["Target"] = relationship(back_populates="tasks")
    actions: Mapped[list["PlannedActionRecord"]] = relationship(back_populates="task")


class PlannedActionRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured action proposed by the AI orchestrator. Mirrors
    packages/shared-types/schemas/planned-action.schema.json."""

    __tablename__ = "planned_actions"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"))
    action_type: Mapped[str] = mapped_column(String(255))
    domain: Mapped[SecurityDomain] = mapped_column(SAEnum(SecurityDomain, name="security_domain"))
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("targets.id"))
    risk_tier: Mapped[RiskTier] = mapped_column(SAEnum(RiskTier, name="risk_tier"))
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped["Task"] = relationship(back_populates="actions")
    decisions: Mapped[list["PolicyDecisionRecord"]] = relationship(back_populates="action")
    executions: Mapped[list["ExecutionRecord"]] = relationship(back_populates="action")


class PolicyDecisionRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Mirrors packages/shared-types/schemas/policy-decision.schema.json."""

    __tablename__ = "policy_decisions"

    action_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("planned_actions.id"))
    verdict: Mapped[PolicyVerdict] = mapped_column(SAEnum(PolicyVerdict, name="policy_verdict"))
    reasons: Mapped[list[str]] = mapped_column(JSONB, default=list)
    requires_approval: Mapped[bool] = mapped_column(default=False)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    action: Mapped["PlannedActionRecord"] = relationship(back_populates="decisions")


class ExecutionRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Mirrors packages/shared-types/schemas/execution-result.schema.json."""

    __tablename__ = "executions"

    action_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("planned_actions.id"))
    adapter: Mapped[str] = mapped_column(String(50))
    status: Mapped[ExecutionStatus] = mapped_column(
        SAEnum(ExecutionStatus, name="execution_status"), default=ExecutionStatus.PENDING
    )
    exit_code: Mapped[int | None] = mapped_column(nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    action: Mapped["PlannedActionRecord"] = relationship(back_populates="executions")


class AuditLogEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Append-only audit trail. One row per meaningful state transition
    anywhere in the pipeline (decision made, approval granted, execution
    started/finished, recovery attempted)."""

    __tablename__ = "audit_log_entries"

    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_sessions.id"), nullable=True
    )
    actor: Mapped[str] = mapped_column(String(100))
    event_type: Mapped[str] = mapped_column(String(100))
    subject_type: Mapped[str] = mapped_column(String(100))
    subject_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)


class Report(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "reports"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"))
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class ToolCategory(StrEnum):
    NETWORK_DIAGNOSTICS = "network_diagnostics"
    WEB_API_TESTING = "web_api_testing"
    VULNERABILITY_ASSESSMENT = "vulnerability_assessment"
    DNS_DOMAIN_ANALYSIS = "dns_domain_analysis"
    INFRASTRUCTURE_DIAGNOSTICS = "infrastructure_diagnostics"
    CLOUD_SECURITY = "cloud_security"
    MOBILE_SECURITY = "mobile_security"
    WIRELESS_DIAGNOSTICS = "wireless_diagnostics"
    PACKET_TRAFFIC_ANALYSIS = "packet_traffic_analysis"
    LOG_ANALYSIS = "log_analysis"
    SYSTEM_DIAGNOSTICS = "system_diagnostics"
    DEFENSIVE_MONITORING = "defensive_monitoring"
    OSINT = "osint"
    DEVELOPER_UTILITIES = "developer_utilities"


class ToolSourceType(StrEnum):
    OFFICIAL_WEBSITE = "official_website"
    OFFICIAL_GITHUB = "official_github"
    OFFICIAL_PACKAGE_REGISTRY = "official_package_registry"
    OTHER_REPUTABLE = "other_reputable"
    UNKNOWN = "unknown"


class ToolTrustStatus(StrEnum):
    UNKNOWN = "unknown"
    DISCOVERED = "discovered"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    APPROVED = "approved"
    BLOCKED = "blocked"
    DEPRECATED = "deprecated"


class ToolApprovalRequirement(StrEnum):
    NONE = "none"
    USER_APPROVAL = "user_approval"
    ADMIN_APPROVAL = "admin_approval"


class Tool(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A Trusted Tool Registry entry — discovery/verification metadata
    only. This table never stores a downloadable binary or grants
    execution: `entrypoint`/`installation_method` are descriptive, and
    actually running anything registered here still goes through the
    unchanged TerminalEngine + PolicyEngine (see services/tools/policy.py
    for why trust status alone is never authorization)."""

    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[ToolCategory] = mapped_column(SAEnum(ToolCategory, name="tool_category"))
    capabilities: Mapped[list[str]] = mapped_column(JSONB, default=list)
    supported_platforms: Mapped[list[str]] = mapped_column(JSONB, default=list)

    source_type: Mapped[ToolSourceType] = mapped_column(
        SAEnum(ToolSourceType, name="tool_source_type")
    )
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    documentation_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    repository_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)

    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    installation_method: Mapped[str | None] = mapped_column(String(500), nullable=True)
    entrypoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dependencies: Mapped[list[str]] = mapped_column(JSONB, default=list)
    required_permissions: Mapped[list[str]] = mapped_column(JSONB, default=list)

    risk_level: Mapped[RiskTier] = mapped_column(SAEnum(RiskTier, name="risk_tier"))
    approval_requirement: Mapped[ToolApprovalRequirement] = mapped_column(
        SAEnum(ToolApprovalRequirement, name="tool_approval_requirement"),
        default=ToolApprovalRequirement.USER_APPROVAL,
    )
    trust_status: Mapped[ToolTrustStatus] = mapped_column(
        SAEnum(ToolTrustStatus, name="tool_trust_status"), default=ToolTrustStatus.DISCOVERED
    )
    verification_report: Mapped[dict] = mapped_column(JSONB, default=dict)
    discovered_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    findings: Mapped[list["Finding"]] = relationship(back_populates="report")


class Finding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "findings"

    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id"))
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[RiskTier] = mapped_column(SAEnum(RiskTier, name="finding_severity"))
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)

    report: Mapped["Report"] = relationship(back_populates="findings")
