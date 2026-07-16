"""Remove deprecated global storage and IAM/BPM configuration.

Revision ID: 000000000007
Revises: 000000000006
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000007"
down_revision: str = "000000000006"
branch_labels: None = None
depends_on: None = None

REMOVED_COLUMNS = (
    ("storage_host", sa.String),
    ("storage_port", sa.Integer),
    ("storage_user", sa.String),
    ("storage_password", sa.String),
    ("iam_url", sa.String),
    ("iam_account", sa.String),
    ("iam_password", sa.String),
    ("bpm_api_url", sa.String),
    ("bpm_process_id", sa.Integer),
)


def _is_sqlite_offline() -> bool:
    context = op.get_context()
    return context.as_sql and context.dialect.name == "sqlite"


def upgrade() -> None:
    if _is_sqlite_offline():
        for name, _type in REMOVED_COLUMNS:
            op.execute(sa.text(f"ALTER TABLE storage_conf DROP COLUMN {name}"))
        return

    with op.batch_alter_table("storage_conf") as batch_op:
        for name, _type in REMOVED_COLUMNS:
            batch_op.drop_column(name)


def downgrade() -> None:
    if _is_sqlite_offline():
        for name, type_factory in REMOVED_COLUMNS:
            type_name = "INTEGER" if type_factory is sa.Integer else "VARCHAR(255)"
            op.execute(sa.text(f"ALTER TABLE storage_conf ADD COLUMN {name} {type_name}"))
        return

    with op.batch_alter_table("storage_conf") as batch_op:
        for name, type_factory in REMOVED_COLUMNS:
            column_type = type_factory() if type_factory is sa.Integer else type_factory(255)
            batch_op.add_column(sa.Column(name, column_type, nullable=True))
