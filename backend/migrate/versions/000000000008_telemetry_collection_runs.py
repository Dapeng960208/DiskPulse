"""Add telemetry collection run ledger.

Revision ID: 000000000008
Revises: 000000000007
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000008"
down_revision: str = "000000000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telemetry_collection_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.String(length=128), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("scope_key", sa.String(length=64), nullable=False),
        sa.Column("storage_cluster_id", sa.Integer(), nullable=True),
        sa.Column("component", sa.String(length=32), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("data_state", sa.String(length=16), nullable=True),
        sa.Column("records_written", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt >= 1", name="ck_telemetry_run_attempt"),
        sa.CheckConstraint("scope_type IN ('cluster', 'scheduler')", name="ck_telemetry_run_scope_type"),
        sa.CheckConstraint("component IN ('capacity', 'vendor_events', 'performance')", name="ck_telemetry_run_component"),
        sa.CheckConstraint("outcome IS NULL OR outcome IN ('success', 'failed', 'skipped')", name="ck_telemetry_run_outcome"),
        sa.CheckConstraint("data_state IS NULL OR data_state IN ('data', 'empty', 'unsupported')", name="ck_telemetry_run_data_state"),
        sa.CheckConstraint("error_code IS NULL OR error_code IN ('vendor_auth', 'vendor_timeout', 'postgres', 'questdb', 'unknown')", name="ck_telemetry_run_error_code"),
        sa.CheckConstraint("(scope_type = 'cluster' AND scope_key <> '') OR (scope_type = 'scheduler' AND scope_key = 'scheduler' AND storage_cluster_id IS NULL)", name="ck_telemetry_run_scope"),
        sa.CheckConstraint("outcome IS NULL OR (finished_at IS NOT NULL AND ((outcome = 'success' AND data_state IS NOT NULL AND records_written IS NOT NULL AND error_code IS NULL) OR (outcome IN ('failed', 'skipped') AND data_state IS NULL AND records_written IS NULL AND error_code IS NULL)))", name="ck_telemetry_run_terminal_fields"),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "attempt", "component", "scope_key", name="uq_telemetry_run_task_attempt_scope"),
    )
    op.create_index("ix_telemetry_run_component_cluster_finished", "telemetry_collection_runs", ["component", "storage_cluster_id", sa.text("finished_at DESC")], unique=False)
    op.create_index("ix_telemetry_run_created_at", "telemetry_collection_runs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_telemetry_run_created_at", table_name="telemetry_collection_runs")
    op.drop_index("ix_telemetry_run_component_cluster_finished", table_name="telemetry_collection_runs")
    op.drop_table("telemetry_collection_runs")
