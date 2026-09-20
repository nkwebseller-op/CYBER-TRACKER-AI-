"""Add agent orchestrator tables (Autonomous Security Agent Intelligence)

Additive only — three new tables and one new enum type. Touches nothing
from 0001/0002.

Revision ID: 0003_add_agent_tables
Revises: 0002_add_installation_tables
Create Date: (Phase 12 — Autonomous Security Agent Intelligence)
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_add_agent_tables"
down_revision = "0002_add_installation_tables"
branch_labels = None
depends_on = None

_AGENT_PHASE = sa.Enum(
    "CREATED",
    "UNDERSTANDING",
    "RESEARCHING",
    "PLANNING",
    "WAITING_FOR_AUTHORIZATION",
    "WAITING_FOR_APPROVAL",
    "PREPARING",
    "EXECUTING",
    "OBSERVING",
    "ANALYZING",
    "VERIFYING",
    "RECOVERING",
    "PAUSED",
    "CANCELLED",
    "COMPLETED",
    "FAILED",
    "BLOCKED",
    name="agent_phase",
)


def upgrade() -> None:
    bind = op.get_bind()
    _AGENT_PHASE.create(bind, checkfirst=True)

    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("target", sa.String(500), nullable=True),
        sa.Column("target_id", sa.Uuid(), sa.ForeignKey("targets.id"), nullable=True),
        sa.Column("phase", _AGENT_PHASE, nullable=False, server_default="CREATED"),
        sa.Column("state_snapshot", JSONB, nullable=False, server_default="{}"),
    )

    op.create_table(
        "agent_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("agent_tasks.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("data", JSONB, nullable=False, server_default="{}"),
    )

    op.create_table(
        "agent_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("agent_tasks.id"), nullable=False),
        sa.Column("action_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("decided_by", sa.String(255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("agent_approvals")
    op.drop_table("agent_events")
    op.drop_table("agent_tasks")
    _AGENT_PHASE.drop(op.get_bind(), checkfirst=True)
