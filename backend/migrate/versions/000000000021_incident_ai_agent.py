"""add incident AI agent settings and audit records

Revision ID: 000000000021
Revises: 000000000020
"""
from alembic import op
import sqlalchemy as sa


revision = "000000000021"
down_revision = "000000000020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("ai_urgency", sa.String(length=16), nullable=True))
    op.add_column("incidents", sa.Column("ai_urgency_reason", sa.String(length=1000), nullable=True))
    op.add_column("incidents", sa.Column("ai_assessment", sa.JSON(), nullable=True))
    op.add_column("incidents", sa.Column("ai_analyzed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "incident_ai_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("iops_absolute_floor", sa.Float(), nullable=False, server_default="10"),
        sa.Column("iops_baseline_ratio", sa.Float(), nullable=False, server_default="0.05"),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "incident_ai_model_bindings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settings_id", sa.Integer(), nullable=False),
        sa.Column("ai_model_id", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["settings_id"], ["incident_ai_settings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_model_id"], ["ai_configs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("settings_id", "ai_model_id", name="uq_incident_ai_model_binding"),
        sa.UniqueConstraint("settings_id", "priority", name="uq_incident_ai_model_priority"),
    )
    op.create_table(
        "incident_ai_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("model_snapshot", sa.JSON(), nullable=True),
        sa.Column("attempt_summary", sa.JSON(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("assessment", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_id"], ["ai_configs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_incident_ai_run_idempotency"),
    )
    op.create_index("ix_incident_ai_run_incident_started", "incident_ai_runs", ["incident_id", "started_at"])


def downgrade() -> None:
    op.drop_index("ix_incident_ai_run_incident_started", table_name="incident_ai_runs")
    op.drop_table("incident_ai_runs")
    op.drop_table("incident_ai_model_bindings")
    op.drop_table("incident_ai_settings")
    op.drop_column("incidents", "ai_analyzed_at")
    op.drop_column("incidents", "ai_assessment")
    op.drop_column("incidents", "ai_urgency_reason")
    op.drop_column("incidents", "ai_urgency")
