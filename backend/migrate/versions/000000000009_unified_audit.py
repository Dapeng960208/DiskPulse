"""Add immutable unified audit events.

Revision ID: 000000000009
Revises: 000000000008
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000009"
down_revision: str = "000000000008"
branch_labels: None = None
depends_on: None = None


def _dialect_name() -> str:
    return op.get_context().dialect.name


def _create_immutability_triggers() -> None:
    dialect = _dialect_name()
    if dialect == "sqlite":
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit_events are append-only'); END"
        ))
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit_events are append-only'); END"
        ))
    elif dialect == "postgresql":
        op.execute(sa.text(
            "CREATE FUNCTION disallow_audit_event_mutation() RETURNS trigger AS $$ "
            "BEGIN RAISE EXCEPTION 'audit_events are append-only'; END; $$ LANGUAGE plpgsql"
        ))
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events "
            "FOR EACH ROW EXECUTE FUNCTION disallow_audit_event_mutation()"
        ))
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events "
            "FOR EACH ROW EXECUTE FUNCTION disallow_audit_event_mutation()"
        ))
    elif dialect == "mysql":
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events "
            "FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_events are append-only'"
        ))
        op.execute(sa.text(
            "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events "
            "FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_events are append-only'"
        ))


def _drop_immutability_triggers() -> None:
    dialect = _dialect_name()
    if dialect == "postgresql":
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_audit_events_no_update ON audit_events"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_audit_events_no_delete ON audit_events"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS disallow_audit_event_mutation()"))
    elif dialect in {"sqlite", "mysql"}:
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_audit_events_no_update"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_audit_events_no_delete"))


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operation_id", sa.String(length=36), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=True),
        sa.Column("before_summary", sa.JSON(), nullable=True),
        sa.Column("after_summary", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.CheckConstraint("phase IN ('attempt', 'result')", name="ck_audit_event_phase"),
        sa.CheckConstraint("outcome IN ('success', 'denied', 'failure')", name="ck_audit_event_outcome"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_project_occurred_id", "audit_events", ["project_id", "occurred_at", "id"])
    op.create_index("ix_audit_events_actor_occurred_id", "audit_events", ["actor_user_id", "occurred_at", "id"])
    op.create_index("ix_audit_events_operation_occurred", "audit_events", ["operation_id", "occurred_at"])
    _create_immutability_triggers()


def downgrade() -> None:
    _drop_immutability_triggers()
    op.drop_index("ix_audit_events_operation_occurred", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_occurred_id", table_name="audit_events")
    op.drop_index("ix_audit_events_project_occurred_id", table_name="audit_events")
    op.drop_table("audit_events")
