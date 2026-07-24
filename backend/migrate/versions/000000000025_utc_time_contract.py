"""Make future business instants timezone-aware and add the user presentation timezone.

Revision ID: 000000000025
Revises: 000000000024

This forward migration is intentionally approved only for an empty development
database.  It does not claim to repair or reinterpret historical wall times.
"""

from alembic import op
import sqlalchemy as sa


revision = "000000000025"
down_revision = "000000000024"
branch_labels = None
depends_on = None


LEGACY_INSTANT_COLUMNS = (
    ("users", "updated_at"),
    ("projects", "updated_at"),
    ("project_memberships", "created_at"),
    ("project_memberships", "updated_at"),
    ("audit_events", "occurred_at"),
    ("storage_clusters", "created_at"),
    ("storage_clusters", "updated_at"),
    ("aggregates", "updated_at"),
    ("volumes", "updated_at"),
    ("qtrees", "updated_at"),
    ("groups", "updated_at"),
    ("storage_usages", "access_time"),
    ("storage_usages", "modify_time"),
    ("storage_usages", "change_time"),
    ("storage_usages", "birth_time"),
    ("storage_usages", "updated_at"),
    ("storage_alerts", "next_attempt_at"),
    ("storage_alerts", "notified_at"),
    ("storage_alerts", "updated_at"),
    ("vendor_event_definitions", "created_at"),
    ("vendor_event_definitions", "updated_at"),
    ("storage_alert_states", "last_observed_at"),
    ("storage_alert_states", "last_notified_at"),
    ("storage_back_up_records", "start_time"),
    ("storage_back_up_records", "end_time"),
    ("large_files", "updated_at"),
    ("large_files", "created_at"),
    ("ai_configs", "capability_updated_at"),
    ("ai_configs", "created_at"),
    ("ai_configs", "updated_at"),
    ("ai_conversations", "created_at"),
    ("ai_conversations", "updated_at"),
    ("ai_messages", "created_at"),
    ("ai_messages", "updated_at"),
    ("ai_platform_settings", "created_at"),
    ("ai_platform_settings", "updated_at"),
    ("ai_conversation_name_aliases", "created_at"),
    ("ai_conversation_name_aliases", "updated_at"),
    ("ai_audit_logs", "started_at"),
    ("ai_audit_logs", "finished_at"),
    ("ai_audit_logs", "created_at"),
    ("ai_audit_logs", "updated_at"),
    ("capacity_forecasts", "training_start"),
    ("capacity_forecasts", "training_end"),
    ("capacity_forecasts", "created_at"),
    ("capacity_prediction_settings", "updated_at"),
    ("capacity_prediction_candidates", "created_at"),
    ("capacity_prediction_candidate_forecasts", "forecast_start"),
    ("capacity_prediction_candidate_forecasts", "created_at"),
    ("capacity_prediction_evaluations", "window_start"),
    ("capacity_prediction_evaluations", "window_end"),
    ("capacity_prediction_evaluations", "created_at"),
    ("capacity_prediction_plans", "effective_at"),
    ("capacity_prediction_plans", "created_at"),
    ("anomaly_observations", "observed_at"),
    ("anomaly_observations", "evidence_window_start"),
    ("anomaly_observations", "evidence_window_end"),
    ("anomaly_observations", "created_at"),
    ("diagnoses", "created_at"),
    ("incidents", "opened_at"),
    ("incidents", "resolved_at"),
    ("incidents", "silenced_until"),
    ("incidents", "created_at"),
    ("incidents", "updated_at"),
    ("incidents", "correlation_bucket_at"),
    ("incidents", "last_evidence_at"),
    ("incidents", "ai_analyzed_at"),
    ("incident_timeline", "occurred_at"),
    ("incident_evidence", "observed_at"),
    ("incident_evidence", "created_at"),
    ("incident_correlation_states", "last_evidence_at"),
    ("incident_correlation_states", "updated_at"),
    ("maintenance_windows", "starts_at"),
    ("maintenance_windows", "ends_at"),
    ("maintenance_windows", "created_at"),
    ("incident_ai_settings", "updated_at"),
    ("incident_ai_runs", "started_at"),
    ("incident_ai_runs", "completed_at"),
    ("telemetry_collection_runs", "started_at"),
    ("telemetry_collection_runs", "finished_at"),
    ("telemetry_collection_runs", "created_at"),
    ("telemetry_quality_snapshots", "calculated_at"),
    ("telemetry_quality_snapshots", "latest_point_at"),
)


def _require_empty_development_database() -> None:
    """Refuse the intentionally destructive type migration when data exists."""
    context = op.get_context()
    if context.as_sql:
        return

    bind = op.get_bind()
    populated_tables = []
    for table_name in dict.fromkeys(table for table, _column in LEGACY_INSTANT_COLUMNS):
        has_rows = bind.execute(
            sa.text(f'SELECT EXISTS (SELECT 1 FROM "{table_name}" LIMIT 1)')
        ).scalar()
        if has_rows:
            populated_tables.append(table_name)

    if populated_tables:
        sample = ", ".join(populated_tables[:5])
        raise RuntimeError(
            "UTC time contract migration requires an empty development database; "
            f"found rows in: {sample}. Clear and rebuild the development database first."
        )


def _configure_postgresql_ddl_timeouts() -> None:
    """Bound lock waits so a development migration cannot appear indefinitely hung."""
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("SET LOCAL statement_timeout = '5min'")


def _alter_instants(*, timezone: bool) -> None:
    bind = op.get_bind()
    target_type = sa.DateTime(timezone=timezone)
    if bind.dialect.name == "postgresql":
        target = "TIMESTAMP WITH TIME ZONE" if timezone else "TIMESTAMP WITHOUT TIME ZONE"
        for table_name, column_name in LEGACY_INSTANT_COLUMNS:
            op.execute(
                sa.text(
                    f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" '
                    f"TYPE {target} USING \"{column_name}\" AT TIME ZONE 'UTC'"
                )
            )
        return

    # Offline SQL compilation cannot reflect SQLite tables for batch mode.
    # Runtime SQLite upgrades still use batch mode below; this path exists for
    # the cross-dialect migration compile gate only.
    if op.get_context().as_sql:
        for table_name, column_name in LEGACY_INSTANT_COLUMNS:
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.DateTime(),
                type_=target_type,
            )
        return

    # SQLite's development schema must be rebuilt by Alembic; PostgreSQL gets
    # the explicit UTC cast above.  Other supported dialects compile this form.
    for table_name, column_name in LEGACY_INSTANT_COLUMNS:
        with op.batch_alter_table(table_name) as batch:
            batch.alter_column(
                column_name,
                existing_type=sa.DateTime(),
                type_=target_type,
            )


def upgrade() -> None:
    _configure_postgresql_ddl_timeouts()
    _require_empty_development_database()
    op.add_column("users", sa.Column("time_zone", sa.String(length=64), nullable=True))
    _alter_instants(timezone=True)


def downgrade() -> None:
    _configure_postgresql_ddl_timeouts()
    _require_empty_development_database()
    _alter_instants(timezone=False)
    op.drop_column("users", "time_zone")
