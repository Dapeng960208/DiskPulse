"""Add inherited storage alert rules and delivery outbox.

Revision ID: 000000000006
Revises: 000000000005
"""

from alembic import op
import json
import sqlalchemy as sa


revision: str = "000000000006"
down_revision: str = "000000000005"
branch_labels: None = None
depends_on: None = None

DEFAULT_RULE = {
    "quota_basis": "hard",
    "important": {"threshold": 80, "repeat_hours": 24},
    "serious": {"threshold": 90, "repeat_hours": 6},
    "emergency": {"threshold": 95, "repeat_hours": 1},
}


def _is_sqlite_offline() -> bool:
    context = op.get_context()
    return context.as_sql and context.dialect.name == "sqlite"


def _sqlite_execute(statement: str) -> None:
    # Alembic treats colons in textual SQL as bind parameters unless escaped.
    op.execute(sa.text(statement.replace(":", r"\:")))


def _sqlite_offline_upgrade() -> None:
    rule = json.dumps(DEFAULT_RULE, separators=(",", ":")).replace("'", "''")
    statements = (
        f"ALTER TABLE storage_conf ADD COLUMN storage_alert_rule JSON NOT NULL DEFAULT '{rule}'",
        "ALTER TABLE projects ADD COLUMN storage_alert_rule JSON",
        "UPDATE projects SET is_alert = TRUE WHERE status = 1",
        "ALTER TABLE groups ADD COLUMN storage_alert_rule JSON",
        "ALTER TABLE groups ADD COLUMN alert_cc_user_ids JSON NOT NULL DEFAULT '[]'",
        """CREATE TABLE storage_alert_states (
            id INTEGER NOT NULL PRIMARY KEY,
            target_type VARCHAR(32) NOT NULL,
            target_id INTEGER NOT NULL,
            rule_signature VARCHAR(64) NOT NULL,
            consecutive_breach_count INTEGER DEFAULT '0' NOT NULL,
            current_level VARCHAR(16),
            last_use_ratio FLOAT,
            last_observed_at DATETIME,
            last_notified_at DATETIME,
            CONSTRAINT uq_storage_alert_state_target UNIQUE (target_type, target_id)
        )""",
        "CREATE INDEX ix_storage_alert_state_target ON storage_alert_states (target_type, target_id)",
        "ALTER TABLE storage_alerts ADD COLUMN event_type VARCHAR(16) DEFAULT 'trigger' NOT NULL",
        "ALTER TABLE storage_alerts ADD COLUMN quota_basis VARCHAR(8) DEFAULT 'hard' NOT NULL",
        "ALTER TABLE storage_alerts ADD COLUMN delivery_status VARCHAR(16) DEFAULT 'legacy' NOT NULL",
        "ALTER TABLE storage_alerts ADD COLUMN recipient_usernames JSON",
        "ALTER TABLE storage_alerts ADD COLUMN delivery_attempts INTEGER DEFAULT '0' NOT NULL",
        "ALTER TABLE storage_alerts ADD COLUMN next_attempt_at DATETIME",
        "ALTER TABLE storage_alerts ADD COLUMN notified_at DATETIME",
        "ALTER TABLE storage_alerts ADD COLUMN delivery_error VARCHAR(512)",
        "CREATE INDEX ix_storage_alert_delivery_due ON storage_alerts (delivery_status, next_attempt_at)",
    )
    for statement in statements:
        _sqlite_execute(statement)


def _sqlite_offline_downgrade() -> None:
    statements = (
        "DROP INDEX ix_storage_alert_delivery_due",
        "ALTER TABLE storage_alerts DROP COLUMN delivery_error",
        "ALTER TABLE storage_alerts DROP COLUMN notified_at",
        "ALTER TABLE storage_alerts DROP COLUMN next_attempt_at",
        "ALTER TABLE storage_alerts DROP COLUMN delivery_attempts",
        "ALTER TABLE storage_alerts DROP COLUMN recipient_usernames",
        "ALTER TABLE storage_alerts DROP COLUMN delivery_status",
        "ALTER TABLE storage_alerts DROP COLUMN quota_basis",
        "ALTER TABLE storage_alerts DROP COLUMN event_type",
        "DROP INDEX ix_storage_alert_state_target",
        "DROP TABLE storage_alert_states",
        "ALTER TABLE groups DROP COLUMN alert_cc_user_ids",
        "ALTER TABLE groups DROP COLUMN storage_alert_rule",
        "ALTER TABLE projects DROP COLUMN storage_alert_rule",
        "ALTER TABLE storage_conf DROP COLUMN storage_alert_rule",
    )
    for statement in statements:
        _sqlite_execute(statement)


def _backfill_json(table_name, column_name, value) -> None:
    context = op.get_context()
    if context.as_sql:
        payload = json.dumps(value, separators=(",", ":")).replace(":", r"\:").replace("'", "''")
        op.execute(
            sa.text(
                f"UPDATE {table_name} SET {column_name} = '{payload}' "
                f"WHERE {column_name} IS NULL"
            )
        )
        return
    table = sa.table(table_name, sa.column(column_name, sa.JSON()))
    op.get_bind().execute(
        table.update().where(table.c[column_name].is_(None)).values({column_name: value})
    )


def upgrade() -> None:
    if _is_sqlite_offline():
        _sqlite_offline_upgrade()
        return
    with op.batch_alter_table("storage_conf") as batch_op:
        batch_op.add_column(
            sa.Column(
                "storage_alert_rule",
                sa.JSON(),
                nullable=True,
            )
        )
    _backfill_json("storage_conf", "storage_alert_rule", DEFAULT_RULE)
    with op.batch_alter_table("storage_conf") as batch_op:
        batch_op.alter_column(
            "storage_alert_rule", existing_type=sa.JSON(), nullable=False
        )
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("storage_alert_rule", sa.JSON(), nullable=True))
        batch_op.alter_column("is_alert", existing_type=sa.Boolean(), server_default=sa.true())
    op.execute(sa.text("UPDATE projects SET is_alert = TRUE WHERE status = 1"))
    with op.batch_alter_table("groups") as batch_op:
        batch_op.add_column(sa.Column("storage_alert_rule", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("alert_cc_user_ids", sa.JSON(), nullable=True))
    _backfill_json("groups", "alert_cc_user_ids", [])
    with op.batch_alter_table("groups") as batch_op:
        batch_op.alter_column(
            "alert_cc_user_ids", existing_type=sa.JSON(), nullable=False
        )

    op.create_table(
        "storage_alert_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("rule_signature", sa.String(length=64), nullable=False),
        sa.Column("consecutive_breach_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_level", sa.String(length=16), nullable=True),
        sa.Column("last_use_ratio", sa.Float(), nullable=True),
        sa.Column("last_observed_at", sa.DateTime(), nullable=True),
        sa.Column("last_notified_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_type", "target_id", name="uq_storage_alert_state_target"),
    )
    op.create_index(
        "ix_storage_alert_state_target",
        "storage_alert_states",
        ["target_type", "target_id"],
        unique=False,
    )

    with op.batch_alter_table("storage_alerts") as batch_op:
        batch_op.add_column(
            sa.Column("event_type", sa.String(length=16), nullable=False, server_default="trigger")
        )
        batch_op.add_column(
            sa.Column("quota_basis", sa.String(length=8), nullable=False, server_default="hard")
        )
        batch_op.add_column(
            sa.Column("delivery_status", sa.String(length=16), nullable=False, server_default="legacy")
        )
        batch_op.add_column(sa.Column("recipient_usernames", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("next_attempt_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("notified_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("delivery_error", sa.String(length=512), nullable=True))
        batch_op.create_index(
            "ix_storage_alert_delivery_due",
            ["delivery_status", "next_attempt_at"],
            unique=False,
        )


def downgrade() -> None:
    if _is_sqlite_offline():
        _sqlite_offline_downgrade()
        return
    with op.batch_alter_table("storage_alerts") as batch_op:
        batch_op.drop_index("ix_storage_alert_delivery_due")
        for column in (
            "delivery_error",
            "notified_at",
            "next_attempt_at",
            "delivery_attempts",
            "recipient_usernames",
            "delivery_status",
            "quota_basis",
            "event_type",
        ):
            batch_op.drop_column(column)
    op.drop_index("ix_storage_alert_state_target", table_name="storage_alert_states")
    op.drop_table("storage_alert_states")
    with op.batch_alter_table("groups") as batch_op:
        batch_op.drop_column("alert_cc_user_ids")
        batch_op.drop_column("storage_alert_rule")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column("is_alert", existing_type=sa.Boolean(), server_default=None)
        batch_op.drop_column("storage_alert_rule")
    with op.batch_alter_table("storage_conf") as batch_op:
        batch_op.drop_column("storage_alert_rule")
