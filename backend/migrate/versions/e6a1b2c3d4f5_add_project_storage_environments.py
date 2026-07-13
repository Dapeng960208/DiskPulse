"""add project storage environments

Revision ID: e6a1b2c3d4f5
Revises: f4b2c8d9e701
Create Date: 2026-07-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6a1b2c3d4f5"
down_revision: Union[str, Sequence[str], None] = "f4b2c8d9e701"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_storage_environments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("storage_cluster_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("limit", sa.Float(), nullable=True),
        sa.Column("soft_limit", sa.Float(), nullable=True),
        sa.Column("used", sa.Float(), nullable=True),
        sa.Column("use_ratio", sa.Float(), nullable=True),
        sa.Column("soft_use_ratio", sa.Float(), nullable=True),
        sa.Column(
            "collection_status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("last_collected_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_project_storage_environment_project",
        ),
        sa.ForeignKeyConstraint(
            ["storage_cluster_id"],
            ["storage_clusters.id"],
            name="fk_project_storage_environment_cluster",
        ),
        sa.UniqueConstraint(
            "project_id",
            "name",
            name="uq_project_storage_environment_project_name",
        ),
        sa.UniqueConstraint(
            "project_id",
            "storage_cluster_id",
            name="uq_project_storage_environment_project_cluster",
        ),
        sa.CheckConstraint(
            "collection_status IN ('pending', 'success', 'failed')",
            name="ck_project_storage_environment_collection_status",
        ),
    )
    op.create_index(
        "ix_project_storage_environment_project_active_id",
        "project_storage_environments",
        ["project_id", "is_active", "id"],
        unique=False,
    )
    op.create_index(
        "ix_project_storage_environment_cluster_project",
        "project_storage_environments",
        ["storage_cluster_id", "project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_storage_environment_project_collection_active",
        "project_storage_environments",
        ["project_id", "collection_status", "is_active"],
        unique=False,
    )

    with op.batch_alter_table("groups") as batch_op:
        batch_op.add_column(
            sa.Column("project_environment_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(sa.Column("volume_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_group_project_storage_environment",
            "project_storage_environments",
            ["project_environment_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_group_volume", "volumes", ["volume_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("groups") as batch_op:
        batch_op.drop_constraint(
            "fk_group_project_storage_environment", type_="foreignkey"
        )
        batch_op.drop_constraint("fk_group_volume", type_="foreignkey")
        batch_op.drop_column("volume_id")
        batch_op.drop_column("project_environment_id")

    op.drop_index(
        "ix_project_storage_environment_project_collection_active",
        table_name="project_storage_environments",
    )
    op.drop_index(
        "ix_project_storage_environment_cluster_project",
        table_name="project_storage_environments",
    )
    op.drop_index(
        "ix_project_storage_environment_project_active_id",
        table_name="project_storage_environments",
    )
    op.drop_table("project_storage_environments")
