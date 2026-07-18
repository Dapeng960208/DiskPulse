"""add capacity prediction governance

Revision ID: 000000000013
Revises: 000000000012
"""
from alembic import op
import sqlalchemy as sa


revision = "000000000013"
down_revision = "000000000012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "capacity_prediction_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "capacity_prediction_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity_delta", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("asset_type IN ('group', 'storage_usage')", name="ck_capacity_prediction_plan_asset_type"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capacity_prediction_plan_asset_effective", "capacity_prediction_plans", ["asset_type", "asset_id", "effective_at"])
    op.create_index("ix_capacity_prediction_plan_project_effective", "capacity_prediction_plans", ["project_id", "effective_at"])
    op.create_table(
        "capacity_prediction_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ai_model_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["ai_model_id"], ["ai_configs.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("version", name="uq_capacity_prediction_candidate_version"),
    )
    op.create_table(
        "capacity_prediction_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("baseline_mape", sa.Float(), nullable=False),
        sa.Column("candidate_mape", sa.Float(), nullable=False),
        sa.Column("risk_coverage_ok", sa.Boolean(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["capacity_prediction_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_id",
            "window_start",
            "window_end",
            name="uq_capacity_prediction_evaluation_window",
        ),
    )
    op.create_index("ix_capacity_prediction_eval_candidate_created", "capacity_prediction_evaluations", ["candidate_id", "created_at"])
    op.create_table(
        "capacity_prediction_candidate_forecasts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("forecast_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("baseline_curve", sa.JSON(), nullable=False),
        sa.Column("curve", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("fallback_reason", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("asset_type IN ('group', 'storage_usage')", name="ck_capacity_prediction_candidate_forecast_asset_type"),
        sa.CheckConstraint("source IN ('ai_candidate', 'baseline_fallback')", name="ck_capacity_prediction_candidate_forecast_source"),
        sa.ForeignKeyConstraint(["candidate_id"], ["capacity_prediction_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", "asset_type", "asset_id", "forecast_start", name="uq_capacity_prediction_candidate_forecast"),
    )
    op.create_index(
        "ix_capacity_prediction_candidate_forecast_asset_start",
        "capacity_prediction_candidate_forecasts",
        ["asset_type", "asset_id", "forecast_start"],
    )


def downgrade():
    op.drop_index("ix_capacity_prediction_candidate_forecast_asset_start", table_name="capacity_prediction_candidate_forecasts")
    op.drop_table("capacity_prediction_candidate_forecasts")
    op.drop_index("ix_capacity_prediction_eval_candidate_created", table_name="capacity_prediction_evaluations")
    op.drop_table("capacity_prediction_evaluations")
    op.drop_table("capacity_prediction_candidates")
    op.drop_index("ix_capacity_prediction_plan_project_effective", table_name="capacity_prediction_plans")
    op.drop_index("ix_capacity_prediction_plan_asset_effective", table_name="capacity_prediction_plans")
    op.drop_table("capacity_prediction_plans")
    op.drop_table("capacity_prediction_settings")
