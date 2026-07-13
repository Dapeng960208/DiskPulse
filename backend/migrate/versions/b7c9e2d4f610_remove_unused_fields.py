"""remove confirmed unused fields

Revision ID: b7c9e2d4f610
Revises: e6a1b2c3d4f5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b7c9e2d4f610"
down_revision: Union[str, Sequence[str], None] = "e6a1b2c3d4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.drop_column("status")
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("ncpus")
        batch_op.drop_column("max_jobs")
        batch_op.drop_column("cpuf")
        batch_op.drop_column("max_mem")
        batch_op.drop_column("mem")
        batch_op.drop_column("mem_reserved")
        batch_op.drop_column("slot")
        batch_op.drop_column("slot_reserved")
        batch_op.drop_column("run_jobs")
        batch_op.drop_column("ssusp_jobs")
        batch_op.drop_column("ususp_jobs")
        batch_op.drop_column("pend_jobs")

    with op.batch_alter_table("storage_back_up_records") as batch_op:
        batch_op.drop_column("is_deleted")

    with op.batch_alter_table("storage_conf") as batch_op:
        batch_op.drop_column("questdb_host")
        batch_op.drop_column("questdb_port")
        batch_op.drop_column("questdb_user")
        batch_op.drop_column("questdb_password")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("run_jobs")
        batch_op.drop_column("ssusp_jobs")
        batch_op.drop_column("pend_jobs")
        batch_op.drop_column("done_jobs")
        batch_op.drop_column("exit_jobs")


def downgrade() -> None:
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("ncpus", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("max_jobs", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("cpuf", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("max_mem", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("mem", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("mem_reserved", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("slot", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("slot_reserved", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("run_jobs", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("ssusp_jobs", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("ususp_jobs", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("pend_jobs", sa.Integer(), nullable=True))

    with op.batch_alter_table("storage_back_up_records") as batch_op:
        batch_op.add_column(sa.Column("is_deleted", sa.Boolean(), nullable=True))

    with op.batch_alter_table("storage_conf") as batch_op:
        batch_op.add_column(sa.Column("questdb_host", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("questdb_port", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("questdb_user", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("questdb_password", sa.String(), nullable=True))

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("run_jobs", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("ssusp_jobs", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("pend_jobs", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("done_jobs", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("exit_jobs", sa.Integer(), nullable=True))
