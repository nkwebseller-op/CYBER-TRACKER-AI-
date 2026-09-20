"""Add installation tables (Tool Installation & Environment Preparation)

Additive only — creates three new tables and one new enum type. Touches
nothing from 0001_add_tools_table.

Revision ID: 0002_add_installation_tables
Revises: 0001_add_tools_table
Create Date: (Phase 11 — Tool Installation & Environment Preparation)
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_add_installation_tables"
down_revision = "0001_add_tools_table"
branch_labels = None
depends_on = None

_INSTALLATION_STATE = sa.Enum(
    "DISCOVERED",
    "REVIEWING",
    "DEPENDENCIES_CHECKING",
    "WAITING_FOR_APPROVAL",
    "PREPARING",
    "INSTALLING",
    "VERIFYING",
    "INSTALLED",
    "FAILED",
    "BLOCKED",
    "CANCELLED",
    "ROLLBACK_REQUIRED",
    name="installation_state",
)


def upgrade() -> None:
    bind = op.get_bind()
    _INSTALLATION_STATE.create(bind, checkfirst=True)

    op.create_table(
        "installation_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("tool_id", sa.Uuid(), sa.ForeignKey("tools.id"), nullable=False),
        sa.Column("target_id", sa.Uuid(), sa.ForeignKey("targets.id"), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("requested_by", sa.String(255), nullable=True),
        sa.Column(
            "state", _INSTALLATION_STATE, nullable=False, server_default="DISCOVERED"
        ),
        sa.Column("plan", JSONB, nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("verification", JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    op.create_table(
        "installation_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "request_id", sa.Uuid(), sa.ForeignKey("installation_requests.id"), nullable=False
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error_category", sa.String(100), nullable=True),
    )

    op.create_table(
        "installed_tools",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("tool_id", sa.Uuid(), sa.ForeignKey("tools.id"), nullable=False),
        sa.Column(
            "installation_request_id",
            sa.Uuid(),
            sa.ForeignKey("installation_requests.id"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("package_manager", sa.String(50), nullable=False),
        sa.Column("installed_version", sa.String(100), nullable=True),
        sa.Column("verification", JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("installed_tools")
    op.drop_table("installation_attempts")
    op.drop_table("installation_requests")
    _INSTALLATION_STATE.drop(op.get_bind(), checkfirst=True)
