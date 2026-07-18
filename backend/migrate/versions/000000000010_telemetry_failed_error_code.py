"""Permit classified error codes on failed telemetry runs.

Revision ID: 000000000010
Revises: 000000000009
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000010"
down_revision: str = "000000000009"
branch_labels: None = None
depends_on: None = None


TERMINAL_CONSTRAINT = "ck_telemetry_run_terminal_fields"
OLD_TERMINAL_CONDITION = (
    "(outcome IS NULL AND finished_at IS NULL AND data_state IS NULL AND "
    "records_written IS NULL AND error_code IS NULL) OR "
    "(outcome IS NOT NULL AND finished_at IS NOT NULL AND ((outcome = 'success' "
    "AND data_state IS NOT NULL AND records_written IS NOT NULL AND error_code IS NULL) OR "
    "(outcome IN ('failed', 'skipped') AND data_state IS NULL "
    "AND records_written IS NULL AND error_code IS NULL)))"
)
NEW_TERMINAL_CONDITION = (
    "(outcome IS NULL AND finished_at IS NULL AND data_state IS NULL AND "
    "records_written IS NULL AND error_code IS NULL) OR "
    "(outcome IS NOT NULL AND finished_at IS NOT NULL AND ((outcome = 'success' "
    "AND data_state IS NOT NULL AND records_written IS NOT NULL AND error_code IS NULL) OR "
    "(outcome = 'failed' AND data_state IS NULL AND records_written IS NULL "
    "AND error_code IS NOT NULL) OR (outcome = 'skipped' AND data_state IS NULL "
    "AND records_written IS NULL AND error_code IS NULL)))"
)


def _sqlite_telemetry_table(*, terminal_condition: str) -> sa.Table:
    metadata = sa.MetaData()
    table = sa.Table(
        "telemetry_collection_runs",
        metadata,
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
        sa.CheckConstraint(
            "scope_type IN ('cluster', 'scheduler')", name="ck_telemetry_run_scope_type"
        ),
        sa.CheckConstraint(
            "component IN ('capacity', 'vendor_events', 'performance')",
            name="ck_telemetry_run_component",
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('success', 'failed', 'skipped')",
            name="ck_telemetry_run_outcome",
        ),
        sa.CheckConstraint(
            "data_state IS NULL OR data_state IN ('data', 'empty', 'unsupported')",
            name="ck_telemetry_run_data_state",
        ),
        sa.CheckConstraint(
            "error_code IS NULL OR error_code IN "
            "('vendor_auth', 'vendor_timeout', 'postgres', 'questdb', 'unknown')",
            name="ck_telemetry_run_error_code",
        ),
        sa.CheckConstraint(
            "(scope_type = 'cluster' AND scope_key <> '') OR "
            "(scope_type = 'scheduler' AND scope_key = 'scheduler' "
            "AND storage_cluster_id IS NULL)",
            name="ck_telemetry_run_scope",
        ),
        sa.CheckConstraint(terminal_condition, name=TERMINAL_CONSTRAINT),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id",
            "attempt",
            "component",
            "scope_key",
            name="uq_telemetry_run_task_attempt_scope",
        ),
    )
    sa.Index(
        "ix_telemetry_run_component_cluster_finished",
        table.c.component,
        table.c.storage_cluster_id,
        sa.text("finished_at DESC"),
    )
    sa.Index("ix_telemetry_run_created_at", table.c.created_at)
    return table


def _replace_terminal_constraint(condition: str, *, copy_from: sa.Table | None = None) -> None:
    with op.batch_alter_table(
        "telemetry_collection_runs",
        recreate="always" if copy_from is not None else "auto",
        copy_from=copy_from,
    ) as batch_op:
        batch_op.drop_constraint(TERMINAL_CONSTRAINT, type_="check")
        batch_op.create_check_constraint(TERMINAL_CONSTRAINT, condition)


def upgrade() -> None:
    # Review fix: existing r8/r9 databases must retain failed telemetry error codes too.
    if op.get_context().dialect.name == "sqlite":
        _replace_terminal_constraint(
            NEW_TERMINAL_CONDITION,
            copy_from=_sqlite_telemetry_table(terminal_condition=OLD_TERMINAL_CONDITION),
        )
        return
    _replace_terminal_constraint(NEW_TERMINAL_CONDITION)


def downgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        _replace_terminal_constraint(
            OLD_TERMINAL_CONDITION,
            copy_from=_sqlite_telemetry_table(terminal_condition=NEW_TERMINAL_CONDITION),
        )
        return
    _replace_terminal_constraint(OLD_TERMINAL_CONDITION)
