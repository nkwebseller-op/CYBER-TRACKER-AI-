"""Add tools table (Trusted Tool Registry)

This is the first migration file in this project — earlier phases relied
on `Base.metadata.create_all()` for local development rather than a
tracked migration. Rather than retroactively fabricate a baseline
migration for tables this phase never touches, this migration is scoped
to exactly the new `tools` table Phase 10 adds; it is purely additive
(new table + new enum types) and never alters or drops anything that
already exists.

Revision ID: 0001_add_tools_table
Revises:
Create Date: (Phase 10 — Tool Discovery & Trusted Tool Registry)
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "0001_add_tools_table"
down_revision = None
branch_labels = None
depends_on = None

_TOOL_CATEGORY = sa.Enum(
    "network_diagnostics",
    "web_api_testing",
    "vulnerability_assessment",
    "dns_domain_analysis",
    "infrastructure_diagnostics",
    "cloud_security",
    "mobile_security",
    "wireless_diagnostics",
    "packet_traffic_analysis",
    "log_analysis",
    "system_diagnostics",
    "defensive_monitoring",
    "osint",
    "developer_utilities",
    name="tool_category",
)

_TOOL_SOURCE_TYPE = sa.Enum(
    "official_website",
    "official_github",
    "official_package_registry",
    "other_reputable",
    "unknown",
    name="tool_source_type",
)

_TOOL_TRUST_STATUS = sa.Enum(
    "unknown",
    "discovered",
    "under_review",
    "verified",
    "approved",
    "blocked",
    "deprecated",
    name="tool_trust_status",
)

_TOOL_APPROVAL_REQUIREMENT = sa.Enum(
    "none", "user_approval", "admin_approval", name="tool_approval_requirement"
)

# risk_tier already exists as a Postgres enum type from Phase 1's
# planned_actions table — reused here via checkfirst rather than redefined.
_RISK_TIER = sa.Enum("low", "medium", "high", "critical", name="risk_tier")


def upgrade() -> None:
    bind = op.get_bind()
    _TOOL_CATEGORY.create(bind, checkfirst=True)
    _TOOL_SOURCE_TYPE.create(bind, checkfirst=True)
    _TOOL_TRUST_STATUS.create(bind, checkfirst=True)
    _TOOL_APPROVAL_REQUIREMENT.create(bind, checkfirst=True)
    _RISK_TIER.create(bind, checkfirst=True)

    op.create_table(
        "tools",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", _TOOL_CATEGORY, nullable=False),
        sa.Column("capabilities", JSONB, nullable=False, server_default="[]"),
        sa.Column("supported_platforms", JSONB, nullable=False, server_default="[]"),
        sa.Column("source_type", _TOOL_SOURCE_TYPE, nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("documentation_url", sa.String(2048), nullable=True),
        sa.Column("repository_url", sa.String(2048), nullable=True),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("version", sa.String(100), nullable=True),
        sa.Column("license", sa.String(255), nullable=True),
        sa.Column("installation_method", sa.String(500), nullable=True),
        sa.Column("entrypoint", sa.String(500), nullable=True),
        sa.Column("dependencies", JSONB, nullable=False, server_default="[]"),
        sa.Column("required_permissions", JSONB, nullable=False, server_default="[]"),
        sa.Column("risk_level", _RISK_TIER, nullable=False),
        sa.Column(
            "approval_requirement",
            _TOOL_APPROVAL_REQUIREMENT,
            nullable=False,
            server_default="user_approval",
        ),
        sa.Column(
            "trust_status", _TOOL_TRUST_STATUS, nullable=False, server_default="discovered"
        ),
        sa.Column("verification_report", JSONB, nullable=False, server_default="{}"),
        sa.Column("discovered_version", sa.String(100), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tools_name", "tools", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tools_name", table_name="tools")
    op.drop_table("tools")
    bind = op.get_bind()
    _TOOL_APPROVAL_REQUIREMENT.drop(bind, checkfirst=True)
    _TOOL_TRUST_STATUS.drop(bind, checkfirst=True)
    _TOOL_SOURCE_TYPE.drop(bind, checkfirst=True)
    _TOOL_CATEGORY.drop(bind, checkfirst=True)
    # risk_tier is left in place — it predates this migration and may be
    # used elsewhere (planned_actions.risk_tier).
