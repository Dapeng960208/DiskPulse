"""Add AI model capabilities, platform defaults and message reasoning.

Revision ID: 000000000022
Revises: 000000000021
"""

from alembic import op
import sqlalchemy as sa


revision = "000000000022"
down_revision = "000000000021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_configs",
        sa.Column("capability_cache", sa.Text(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "ai_configs",
        sa.Column("capability_status", sa.String(length=20), nullable=False, server_default="unknown"),
    )
    op.add_column("ai_configs", sa.Column("capability_error", sa.Text(), nullable=True))
    op.add_column("ai_configs", sa.Column("capability_updated_at", sa.DateTime(), nullable=True))
    op.add_column(
        "ai_messages",
        sa.Column("reasoning", sa.String(length=20), nullable=False, server_default="auto"),
    )
    op.create_table(
        "ai_platform_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("default_chat_model_id", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["default_chat_model_id"],
            ["ai_configs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_platform_settings_default_chat_model_id",
        "ai_platform_settings",
        ["default_chat_model_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_platform_settings_default_chat_model_id",
        table_name="ai_platform_settings",
    )
    op.drop_table("ai_platform_settings")
    op.drop_column("ai_messages", "reasoning")
    op.drop_column("ai_configs", "capability_updated_at")
    op.drop_column("ai_configs", "capability_error")
    op.drop_column("ai_configs", "capability_status")
    op.drop_column("ai_configs", "capability_cache")
