"""Add AI conversation name obfuscation state.

Revision ID: 000000000024
Revises: 000000000023
"""

from alembic import op
import sqlalchemy as sa


revision = "000000000024"
down_revision = "000000000023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_platform_settings",
        sa.Column("name_obfuscation_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "ai_platform_settings",
        sa.Column("name_obfuscation_epoch", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("ai_conversations", sa.Column("name_obfuscation_epoch", sa.Integer(), nullable=True))
    op.add_column(
        "ai_conversations",
        sa.Column("name_obfuscation_from_message_id", sa.Integer(), nullable=True),
    )
    op.create_table(
        "ai_conversation_name_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=64), nullable=False),
        sa.Column("entity_kind", sa.String(length=32), nullable=False),
        sa.Column("original_value_encrypted", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "epoch", "alias", name="uq_ai_conversation_name_alias"),
    )
    op.create_index(
        "ix_ai_conversation_name_aliases_conversation_id",
        "ai_conversation_name_aliases",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_conversation_name_alias_context",
        "ai_conversation_name_aliases",
        ["conversation_id", "epoch"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_conversation_name_alias_context", table_name="ai_conversation_name_aliases")
    op.drop_index("ix_ai_conversation_name_aliases_conversation_id", table_name="ai_conversation_name_aliases")
    op.drop_table("ai_conversation_name_aliases")
    op.drop_column("ai_conversations", "name_obfuscation_from_message_id")
    op.drop_column("ai_conversations", "name_obfuscation_epoch")
    op.drop_column("ai_platform_settings", "name_obfuscation_epoch")
    op.drop_column("ai_platform_settings", "name_obfuscation_enabled")
