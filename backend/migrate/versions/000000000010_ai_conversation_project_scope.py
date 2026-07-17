"""Add optional project scope to AI conversations.

Revision ID: 000000000010
Revises: 000000000009
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000010"
down_revision: str = "000000000009"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    context = op.get_context()
    if context.as_sql and context.dialect.name == "sqlite":
        op.execute(sa.text("ALTER TABLE ai_conversations ADD COLUMN project_id INTEGER"))
    else:
        with op.batch_alter_table("ai_conversations") as batch_op:
            batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_ai_conversations_project_id_projects",
                "projects",
                ["project_id"],
                ["id"],
                ondelete="SET NULL",
            )
    op.create_index(
        "ix_ai_conversations_project_user_updated",
        "ai_conversations",
        ["project_id", "user_id", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_conversations_project_user_updated", table_name="ai_conversations")
    context = op.get_context()
    if context.as_sql and context.dialect.name == "sqlite":
        op.execute(sa.text("ALTER TABLE ai_conversations DROP COLUMN project_id"))
    else:
        with op.batch_alter_table("ai_conversations") as batch_op:
            batch_op.drop_column("project_id")
