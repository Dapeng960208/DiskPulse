"""Add per-cluster Isilon session cache settings.

Revision ID: 000000000005
Revises: 000000000004
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000005"
down_revision: str = "000000000004"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    with op.batch_alter_table("storage_clusters") as batch_op:
        batch_op.add_column(
            sa.Column(
                "isilon_session_cache_mode",
                sa.String(length=16),
                nullable=False,
                server_default="none",
            )
        )
        batch_op.add_column(
            sa.Column(
                "isilon_session_cache_path",
                sa.String(length=1024),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("storage_clusters") as batch_op:
        batch_op.drop_column("isilon_session_cache_path")
        batch_op.drop_column("isilon_session_cache_mode")
