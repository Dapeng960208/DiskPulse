"""Backfill project reader memberships for user directory owners.

Revision ID: 000000000014
Revises: 000000000013
"""

from alembic import op
import sqlalchemy as sa


revision = "000000000014"
down_revision = "000000000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    groups = sa.table(
        "groups",
        sa.column("id", sa.Integer()),
        sa.column("project_id", sa.Integer()),
    )
    storage_usages = sa.table(
        "storage_usages",
        sa.column("group_id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
    )
    memberships = sa.table(
        "project_memberships",
        sa.column("project_id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
        sa.column("role", sa.String(length=16)),
    )

    existing = sa.exists(
        sa.select(sa.literal(1)).where(
            memberships.c.project_id == groups.c.project_id,
            memberships.c.user_id == storage_usages.c.user_id,
        )
    )
    directory_users = (
        sa.select(
            groups.c.project_id,
            storage_usages.c.user_id,
            sa.literal_column("'reader'"),
        )
        .select_from(
            storage_usages.join(groups, groups.c.id == storage_usages.c.group_id)
        )
        .where(
            groups.c.project_id.is_not(None),
            storage_usages.c.user_id.is_not(None),
            ~existing,
        )
        .distinct()
    )
    op.execute(
        sa.insert(memberships).from_select(
            ["project_id", "user_id", "role"],
            directory_users,
        )
    )


def downgrade() -> None:
    # Data-only grants may have been changed manually after upgrade; do not revoke them.
    pass
