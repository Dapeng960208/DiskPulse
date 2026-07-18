"""Persist vendor performance identities for storage-space monitoring.

Revision ID: 000000000012
Revises: 000000000011
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000012"
down_revision: str = "000000000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("volumes") as batch_op:
        batch_op.add_column(sa.Column("performance_object_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("volumes") as batch_op:
        batch_op.drop_column("performance_object_id")
