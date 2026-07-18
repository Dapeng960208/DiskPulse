# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

import pytest


UTC_NOW = datetime(2026, 7, 18, 8, 0, tzinfo=timezone.utc)


def _asset(project_id: int | None = 1):
    from services.forecastIncidentService import AssetRef

    return AssetRef(
        asset_type="group",
        asset_id="101",
        storage_cluster_id=7,
        project_id=project_id,
        vendor="netapp",
        display_name="project-alpha",
    )


def test_capacity_forecast_requires_30_valid_daily_points_and_80_percent_coverage():
    from services import forecastIncidentService as analytics

    points = [(UTC_NOW - timedelta(days=day), float(day)) for day in range(29)]
    result = analytics.build_capacity_forecast(
        _asset(),
        points=points,
        hard_limit=100.0,
        now=UTC_NOW,
    )

    assert result.status == "insufficient"
    assert "capacity_history_insufficient" in result.data_gaps
    assert result.curve == []


def test_theil_sen_capacity_forecast_returns_30_ordered_quantile_points_and_three_dates():
    from services import forecastIncidentService as analytics

    points = [
        (UTC_NOW - timedelta(days=44 - day), 10.0 + day)
        for day in range(45)
    ]
    result = analytics.build_capacity_forecast(
        _asset(),
        points=points,
        hard_limit=60.0,
        now=UTC_NOW,
    )

    assert result.status == "ready"
    assert len(result.curve) == 30
    assert all(point.p10 <= point.p50 <= point.p90 for point in result.curve)
    assert result.exhaustion_dates.p10 is not None
    assert result.exhaustion_dates.p50 is not None
    assert result.exhaustion_dates.p90 is not None


def test_performance_requires_three_consecutive_robust_z_scores_and_ignores_isolated_spike():
    from services import forecastIncidentService as analytics

    assert analytics.qualifies_performance_anomaly([3.6]) is False
    assert analytics.qualifies_performance_anomaly([3.6, 3.7]) is False
    assert analytics.qualifies_performance_anomaly([3.6, 3.7, 3.8]) is True
    assert analytics.robust_z_score(value=9.0, median=1.0, mad=0.0) == 100.0


def test_diagnosis_uses_fixed_weights_independent_evidence_and_high_confidence_gate():
    from services import forecastIncidentService as analytics

    diagnosis = analytics.build_diagnosis(
        incident_id=1,
        evidences=[
            analytics.DiagnosisEvidence(evidence_type="forecast_exhaustion", evidence_ref="forecast-1", observed_at=UTC_NOW),
            analytics.DiagnosisEvidence(evidence_type="hard_limit_alert", evidence_ref="alert-1", observed_at=UTC_NOW),
            analytics.DiagnosisEvidence(evidence_type="high_usage", evidence_ref="usage-1", observed_at=UTC_NOW),
        ],
        high_confidence_enabled=True,
    )

    candidate = diagnosis.candidates[0]
    assert candidate.category == "capacity_pressure"
    assert candidate.score == 1.0
    assert diagnosis.confidence == "high"


def test_incident_state_machine_rejects_skips_and_allows_system_reopen():
    from services import forecastIncidentService as analytics

    assert analytics.can_transition_incident("open", "acknowledged") is True
    assert analytics.can_transition_incident("open", "investigating") is False
    assert analytics.can_transition_incident("resolved", "open", system_reopen=True) is True


def test_incident_evidence_deduplicates_and_resolved_incident_reopens_within_24_hours(db_session):
    import models
    from services import forecastIncidentService as analytics

    cluster = models.StorageCluster(id=7, name="cluster-7", storage_type="netapp")
    project = models.Project(id=1, name="project-alpha")
    db_session.add_all([cluster, project])
    db_session.commit()

    envelope = analytics.TelemetryEnvelope(
        asset_ref=_asset(),
        source="storage_alert",
        source_ref="netapp:123",
        observed_at=UTC_NOW,
        collected_at=UTC_NOW,
        metric_or_event="vendor_event",
        value={"severity": "critical"},
        quality="good",
    )
    created = analytics.correlate_incident(db_session, envelope, category="device_fault")
    db_session.commit()
    assert created.created is True

    duplicate = analytics.correlate_incident(db_session, envelope, category="device_fault")
    db_session.commit()
    assert duplicate.created is False
    assert duplicate.incident.id == created.incident.id

    created.incident.status = "resolved"
    created.incident.resolved_at = UTC_NOW
    db_session.commit()
    reopened = analytics.correlate_incident(
        db_session,
        envelope.model_copy(update={"source_ref": "netapp:124", "observed_at": UTC_NOW + timedelta(hours=1)}),
        category="device_fault",
    )
    assert reopened.reopened is True
    assert reopened.incident.status == "open"


@pytest.mark.parametrize("next_status", ["investigating", "resolved"])
def test_invalid_state_transition_is_a_conflict(next_status):
    from services import forecastIncidentService as analytics

    with pytest.raises(ValueError, match="invalid incident status transition"):
        analytics.require_incident_transition("open", next_status)


def test_incident_api_filters_before_pagination_and_enforces_project_roles(
    db_session, api_client_factory
):
    import models
    from routers import forecast_incidents
    from utils.security import issue_token

    db_session.add_all(
        [
            models.User(id=2, rd_username="reader"),
            models.User(id=3, rd_username="editor"),
            models.Project(id=1, name="project-alpha"),
            models.Project(id=2, name="project-beta"),
            models.ProjectMembership(project_id=1, user_id=2, role="reader"),
            models.ProjectMembership(project_id=1, user_id=3, role="editor"),
            models.StorageCluster(id=7, name="cluster-7", storage_type="netapp"),
            models.Incident(
                id=1,
                correlation_key="cluster-7:group:101:device_fault",
                correlation_bucket_at=UTC_NOW,
                asset_type="group",
                asset_id="101",
                storage_cluster_id=7,
                project_id=1,
                vendor="netapp",
                display_name="visible",
                category="device_fault",
                opened_at=UTC_NOW,
                last_evidence_at=UTC_NOW,
            ),
            models.Incident(
                id=2,
                correlation_key="cluster-7:group:102:device_fault",
                correlation_bucket_at=UTC_NOW,
                asset_type="group",
                asset_id="102",
                storage_cluster_id=7,
                project_id=2,
                vendor="netapp",
                display_name="hidden",
                category="device_fault",
                opened_at=UTC_NOW,
                last_evidence_at=UTC_NOW,
            ),
        ]
    )
    db_session.commit()

    reader = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(2)}"},
    )
    response = reader.get("/storage-pulse/api/v1/incidents", params={"page": 1, "size": 20})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["content"][0]["id"] == 1
    assert reader.patch("/storage-pulse/api/v1/incidents/1", json={"status": "acknowledged"}).status_code == 403

    editor = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(3)}"},
    )
    updated = editor.patch("/storage-pulse/api/v1/incidents/1", json={"status": "acknowledged"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "acknowledged"
    db_session.expire_all()
    assert db_session.query(models.AuditEvent).filter(models.AuditEvent.action == "incident.update").count() == 1


def test_forecast_incident_migration_compiles_and_upgrades_sqlite():
    import importlib.util
    import io
    from pathlib import Path

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration_path = Path(__file__).resolve().parents[1] / "migrate" / "versions" / "000000000010_forecast_incidents.py"
    spec = importlib.util.spec_from_file_location("forecast_incident_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    for dialect_name in ("sqlite", "postgresql", "mysql"):
        output = io.StringIO()
        migration.op = Operations(MigrationContext.configure(dialect_name=dialect_name, opts={"as_sql": True, "output_buffer": output}))
        migration.upgrade()
        sql = output.getvalue().lower()
        assert "capacity_forecasts" in sql
        assert "incident_evidence" in sql
        assert "diagnoses" in sql

    with sa.create_engine("sqlite://").begin() as connection:
        connection.execute(sa.text("CREATE TABLE storage_clusters (id INTEGER PRIMARY KEY)"))
        connection.execute(sa.text("CREATE TABLE projects (id INTEGER PRIMARY KEY)"))
        connection.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = sa.inspect(connection)
        assert {
            "telemetry_quality_snapshots",
            "capacity_forecasts",
            "anomaly_observations",
            "incidents",
            "incident_evidence",
            "incident_timeline",
            "maintenance_windows",
            "diagnoses",
        } <= set(inspector.get_table_names())
        migration.downgrade()
        inspector.clear_cache()
        assert "incidents" not in inspector.get_table_names()


def test_incident_notification_defaults_to_administrators_and_requires_explicit_other_audiences():
    from services import incidentNotificationService as notifications

    default_recipients = notifications.resolve_recipient_usernames(
        {"enabled": True},
        administrators=("alice",),
        project_owner="owner",
        project_members=("reader",),
    )
    assert default_recipients == ("alice",)

    configured_recipients = notifications.resolve_recipient_usernames(
        {
            "enabled": True,
            "notify_project_owner": True,
            "notify_project_members": True,
            "extra_usernames": ["extra", "alice"],
        },
        administrators=("alice",),
        project_owner="owner",
        project_members=("reader",),
    )
    assert configured_recipients == ("alice", "owner", "reader", "extra")


def test_quality_snapshot_is_derived_and_never_promotes_a_new_last_success_authority():
    from services import forecastIncidentService as analytics

    snapshot = analytics.evaluate_telemetry_quality(
        component="performance",
        latest_success_at=UTC_NOW - timedelta(seconds=631),
        latest_point_at=UTC_NOW - timedelta(minutes=5),
        observed_points=80,
        expected_points=100,
        now=UTC_NOW,
    )
    assert snapshot.status == "stale"
    assert snapshot.coverage_ratio == 0.8
    assert snapshot.authoritative_last_success_at is None
    assert "telemetry_stale" in snapshot.data_gaps
