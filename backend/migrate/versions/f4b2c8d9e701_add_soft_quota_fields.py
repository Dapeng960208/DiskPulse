"""add soft quota fields

Revision ID: f4b2c8d9e701
Revises: a1d670c60836
Create Date: 2026-06-30 12:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4b2c8d9e701"
down_revision: Union[str, Sequence[str], None] = "a1d670c60836"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = ("projects", "volumes", "qtrees", "groups", "storage_usages")


def upgrade() -> None:
    for table_name in TABLES:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("soft_limit", sa.Float(), nullable=True))
            batch_op.add_column(sa.Column("soft_use_ratio", sa.Float(), nullable=True))


def downgrade() -> None:
    for table_name in reversed(TABLES):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("soft_use_ratio")
            batch_op.drop_column("soft_limit")
