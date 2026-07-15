"""Add the DiskPulse AI model, conversation, message, and audit tables.

Revision ID: 000000000003
Revises: 000000000002
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000003"
down_revision: str = "000000000002"
branch_labels: None = None
depends_on: None = None

_AI_COLUMNS = {
    "ai_configs": {
        "id", "name", "description", "provider", "base_url", "api_key_encrypted",
        "model", "enabled", "enable_chat", "temperature", "max_tokens",
        "system_prompt", "created_by", "updated_by", "created_at", "updated_at",
    },
    "ai_conversations": {"id", "user_id", "model_id", "title", "created_at", "updated_at"},
    "ai_messages": {"id", "conversation_id", "role", "content", "created_at", "updated_at"},
    "ai_audit_logs": {
        "id", "model_id", "conversation_id", "user_id", "source", "source_ref",
        "request_payload", "response_payload", "tool_call_count", "tool_failed_count",
        "detail_payload", "status", "error_message", "trace_id", "started_at",
        "finished_at", "created_at", "updated_at",
    },
}


def _adopt_precreated_schema() -> bool:
    try:
        inspector = sa.inspect(op.get_bind())
    except sa.exc.NoInspectionAvailable:
        return False

    present = set(inspector.get_table_names()) & set(_AI_COLUMNS)
    if not present:
        return False
    if present != set(_AI_COLUMNS):
        raise RuntimeError("partial AI schema exists; restore or remove it before upgrading")

    for table_name, expected in _AI_COLUMNS.items():
        actual = {column["name"] for column in inspector.get_columns(table_name)}
        if actual != expected:
            raise RuntimeError(f"existing {table_name} schema does not match migration 000000000003")
    return True


def upgrade() -> None:
    if _adopt_precreated_schema():
        return

    op.create_table(
        "ai_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enable_chat", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("temperature", sa.Numeric(3, 2), nullable=False, server_default="0.3"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="2048"),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_ai_configs_name"),
    )
    op.create_index("ix_ai_configs_name", "ai_configs", ["name"])

    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["model_id"], ["ai_configs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])
    op.create_index("ix_ai_conversations_model_id", "ai_conversations", ["model_id"])

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])

    op.create_table(
        "ai_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_ref", sa.String(length=200), nullable=True),
        sa.Column("request_payload", sa.Text(), nullable=False),
        sa.Column("response_payload", sa.Text(), nullable=False),
        sa.Column("tool_call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detail_payload", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_id"], ["ai_configs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("model_id", "conversation_id", "user_id", "source", "status", "trace_id"):
        op.create_index(f"ix_ai_audit_logs_{column}", "ai_audit_logs", [column])
    op.create_index("ix_ai_audit_started_id", "ai_audit_logs", ["started_at", "id"])


def downgrade() -> None:
    op.drop_table("ai_audit_logs")
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
    op.drop_table("ai_configs")
