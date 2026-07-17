"""Add project memberships and remove the retired PT user field.

Revision ID: 000000000008
Revises: 000000000007
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000008"
down_revision: str = "000000000007"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.create_table(
        "project_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="reader"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('reader', 'editor', 'project_admin')", name="ck_project_membership_role"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_membership_user"),
    )
    op.create_index("ix_project_membership_user_project", "project_memberships", ["user_id", "project_id"])
    op.create_index("ix_project_membership_project_role", "project_memberships", ["project_id", "role"])

    context = op.get_context()
    if not context.as_sql:
        projects = sa.table(
            "projects",
            sa.column("id", sa.Integer()),
            sa.column("in_charge_user_id", sa.Integer()),
        )
        memberships = sa.table(
            "project_memberships",
            sa.column("project_id", sa.Integer()),
            sa.column("user_id", sa.Integer()),
            sa.column("role", sa.String()),
        )
        rows = op.get_bind().execute(
            sa.select(projects.c.id, projects.c.in_charge_user_id).where(
                projects.c.in_charge_user_id.is_not(None)
            )
        ).all()
        if rows:
            op.get_bind().execute(
                sa.insert(memberships),
                [
                    {"project_id": project_id, "user_id": user_id, "role": "project_admin"}
                    for project_id, user_id in rows
                ],
            )

    if context.as_sql and context.dialect.name == "sqlite":
        op.execute(sa.text("ALTER TABLE projects DROP COLUMN pt_user_id"))
    else:
        with op.batch_alter_table("projects") as batch_op:
            batch_op.drop_column("pt_user_id")


def downgrade() -> None:
    context = op.get_context()
    if context.as_sql and context.dialect.name == "sqlite":
        op.execute(sa.text("ALTER TABLE projects ADD COLUMN pt_user_id INTEGER"))
    else:
        with op.batch_alter_table("projects") as batch_op:
            batch_op.add_column(sa.Column("pt_user_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_projects_pt_user_id_users",
                "users",
                ["pt_user_id"],
                ["id"],
                ondelete="SET NULL",
            )

    op.drop_index("ix_project_membership_project_role", table_name="project_memberships")
    op.drop_index("ix_project_membership_user_project", table_name="project_memberships")
    op.drop_table("project_memberships")
