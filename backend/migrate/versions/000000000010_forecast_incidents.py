"""Add forecast, anomaly, incident, and diagnosis storage.

Revision ID: 000000000010
Revises: 000000000009
"""

from alembic import op
import sqlalchemy as sa


revision: str = "000000000010"
down_revision: str = "000000000009"
branch_labels: None = None
depends_on: None = None


def _asset_columns() -> list[sa.Column]:
    return [
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.String(length=128), nullable=False),
        sa.Column("storage_cluster_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("vendor", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "telemetry_quality_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        *_asset_columns(),
        sa.Column("period", sa.String(length=32), nullable=False),
        sa.Column("latest_point_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("coverage_ratio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("data_gaps", sa.JSON(), nullable=False),
        sa.Column("quality_status", sa.String(length=24), nullable=False, server_default="insufficient"),
        sa.Column("algorithm_version", sa.String(length=64), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_type", "asset_id", "period", "algorithm_version", "calculated_at", name="uq_telemetry_quality_snapshot_version"),
    )
    op.create_index("ix_telemetry_quality_project_period_calculated", "telemetry_quality_snapshots", ["project_id", "period", "calculated_at"])
    op.create_index("ix_telemetry_quality_cluster_asset_period", "telemetry_quality_snapshots", ["storage_cluster_id", "asset_type", "asset_id", "period"])

    op.create_table(
        "capacity_forecasts",
        sa.Column("id", sa.Integer(), nullable=False),
        *_asset_columns(),
        sa.Column("training_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("training_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hard_limit", sa.Float(), nullable=False),
        sa.Column("curve", sa.JSON(), nullable=False),
        sa.Column("exhaustion_dates", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=64), nullable=False),
        sa.Column("input_quality", sa.JSON(), nullable=False),
        sa.Column("backtest_mape", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_type", "asset_id", "training_end", "algorithm_version", name="uq_capacity_forecast_asset_training_version"),
    )
    op.create_index("ix_capacity_forecast_project_created", "capacity_forecasts", ["project_id", "created_at"])
    op.create_index("ix_capacity_forecast_cluster_asset_created", "capacity_forecasts", ["storage_cluster_id", "asset_type", "asset_id", "created_at"])

    op.create_table(
        "anomaly_observations",
        sa.Column("id", sa.Integer(), nullable=False),
        *_asset_columns(),
        sa.Column("metric", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("seasonal_baseline", sa.Float(), nullable=False),
        sa.Column("mad", sa.Float(), nullable=False),
        sa.Column("robust_z_score", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("evidence_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("input_quality", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_ref", "metric", "algorithm_version", name="uq_anomaly_source_metric_version"),
    )
    op.create_index("ix_anomaly_project_observed", "anomaly_observations", ["project_id", "observed_at"])
    op.create_index("ix_anomaly_cluster_asset_metric_observed", "anomaly_observations", ["storage_cluster_id", "asset_type", "asset_id", "metric", "observed_at"])

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("correlation_key", sa.String(length=512), nullable=False),
        sa.Column("correlation_bucket_at", sa.DateTime(timezone=True), nullable=False),
        *_asset_columns(),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="warning"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("assigned_user_id", sa.Integer(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_evidence_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("silenced_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("silence_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("correlation_key", "correlation_bucket_at", name="uq_incident_correlation_bucket"),
        sa.CheckConstraint("status IN ('open', 'acknowledged', 'investigating', 'mitigated', 'resolved')", name="ck_incident_status"),
        sa.CheckConstraint("category IN ('capacity_pressure', 'device_fault', 'performance_contention', 'telemetry_blindspot')", name="ck_incident_category"),
    )
    op.create_index("ix_incident_project_status_updated", "incidents", ["project_id", "status", "updated_at"])
    op.create_index("ix_incident_cluster_asset_updated", "incidents", ["storage_cluster_id", "asset_type", "asset_id", "updated_at"])
    op.create_index("ix_incident_correlation_resolved", "incidents", ["correlation_key", "resolved_at"])

    op.create_table(
        "incident_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_gaps", sa.JSON(), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_ref", name="uq_incident_evidence_source_ref"),
    )
    op.create_index("ix_incident_evidence_incident_observed", "incident_evidence", ["incident_id", "observed_at"])

    op.create_table(
        "incident_timeline",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("from_status", sa.String(length=16), nullable=True),
        sa.Column("to_status", sa.String(length=16), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incident_timeline_incident_occurred", "incident_timeline", ["incident_id", "occurred_at", "id"])

    op.create_table(
        "maintenance_windows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("storage_cluster_id", sa.Integer(), nullable=True),
        sa.Column("asset_type", sa.String(length=32), nullable=True),
        sa.Column("asset_id", sa.String(length=128), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["storage_cluster_id"], ["storage_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_project_window", "maintenance_windows", ["project_id", "starts_at", "ends_at"])

    op.create_table(
        "diagnoses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=64), nullable=False),
        sa.Column("candidates", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("data_gaps", sa.JSON(), nullable=False),
        sa.Column("evidence_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_id", "algorithm_version", "evidence_digest", name="uq_diagnosis_incident_version_digest"),
    )
    op.create_index("ix_diagnosis_incident_created", "diagnoses", ["incident_id", "created_at"])


def downgrade() -> None:
    for table in (
        "diagnoses",
        "maintenance_windows",
        "incident_timeline",
        "incident_evidence",
        "incidents",
        "anomaly_observations",
        "capacity_forecasts",
        "telemetry_quality_snapshots",
    ):
        op.drop_table(table)
