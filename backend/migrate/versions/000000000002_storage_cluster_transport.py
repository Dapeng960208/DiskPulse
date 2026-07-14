"""Add per-cluster storage protocol and TLS verification settings.

Revision ID: 000000000002
Revises: 000000000001
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000002"
down_revision: str = "000000000001"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.add_column(
        "storage_clusters",
        sa.Column(
            "protocol",
            sa.String(length=8),
            nullable=False,
            server_default="https",
        ),
    )
    op.add_column(
        "storage_clusters",
        sa.Column(
            "tls_verify",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    storage_clusters = sa.table(
        "storage_clusters",
        sa.column("tls_verify", sa.Boolean()),
    )
    op.execute(storage_clusters.update().values(tls_verify=sa.false()))


def downgrade() -> None:
    context = op.get_context()
    if context.dialect.name == "sqlite" and not context.as_sql:
        with op.batch_alter_table("storage_clusters") as batch_op:
            batch_op.drop_column("tls_verify")
            batch_op.drop_column("protocol")
        return

    op.drop_column("storage_clusters", "tls_verify")
    op.drop_column("storage_clusters", "protocol")
