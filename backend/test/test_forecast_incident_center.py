# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
        telemetry_runs = migration._sqlite_telemetry_table(
            terminal_condition=migration.OLD_TELEMETRY_TERMINAL_CONDITION
        )
        sa.Table(
            "storage_clusters",
            telemetry_runs.metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
        )
        telemetry_runs.create(connection)
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


def test_forecast_incident_migration_consolidates_telemetry_fix_into_one_revision():
    versions = Path(__file__).resolve().parents[1] / "migrate" / "versions"
    migration_path = versions / "000000000010_forecast_incidents.py"
    source = migration_path.read_text(encoding="utf-8")

    assert [item.name for item in versions.glob("000000000010_*.py")] == [
        "000000000010_forecast_incidents.py"
    ]
    assert "ck_telemetry_run_terminal_fields" in source


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


def test_matching_maintenance_window_suppresses_new_incident_without_losing_raw_evidence(db_session):
    import models
    from services import forecastIncidentService as analytics

    db_session.add_all(
        [
            models.StorageCluster(id=7, name="cluster-7", storage_type="netapp"),
            models.Project(id=1, name="project-alpha"),
            models.MaintenanceWindow(
                project_id=1,
                storage_cluster_id=7,
                asset_type="group",
                asset_id="101",
                starts_at=UTC_NOW - timedelta(minutes=5),
                ends_at=UTC_NOW + timedelta(minutes=5),
                reason="planned maintenance",
            ),
        ]
    )
    db_session.commit()

    result = analytics.correlate_incident(
        db_session,
        analytics.TelemetryEnvelope(
            asset_ref=_asset(),
            source="storage_alert",
            source_ref="netapp:maintenance-window",
            observed_at=UTC_NOW,
            collected_at=UTC_NOW,
            metric_or_event="severe_vendor_event",
            value={"severity": "critical"},
            quality="good",
        ),
        category="device_fault",
    )

    assert result.suppressed is True
    assert result.incident is None
    assert db_session.query(models.Incident).count() == 0


def test_persisted_diagnosis_is_versioned_and_idempotent_for_same_evidence_digest(db_session):
    import models
    from services import forecastIncidentService as analytics

    db_session.add_all(
        [
            models.StorageCluster(id=7, name="cluster-7", storage_type="netapp"),
            models.Project(id=1, name="project-alpha"),
            models.Incident(
                correlation_key="7:group:101:capacity_pressure",
                correlation_bucket_at=UTC_NOW,
                asset_type="group",
                asset_id="101",
                storage_cluster_id=7,
                project_id=1,
                vendor="netapp",
                display_name="project-alpha",
                category="capacity_pressure",
                opened_at=UTC_NOW,
                last_evidence_at=UTC_NOW,
            ),
        ]
    )
    db_session.commit()
    incident = db_session.query(models.Incident).one()
    db_session.add_all(
        [
            models.IncidentEvidence(
                incident_id=incident.id,
                source="forecast",
                source_ref="forecast:1",
                evidence_type="forecast_exhaustion",
                observed_at=UTC_NOW,
                evidence_hash="a" * 64,
            ),
            models.IncidentEvidence(
                incident_id=incident.id,
                source="storage_alert",
                source_ref="alert:1",
                evidence_type="hard_limit_alert",
                observed_at=UTC_NOW,
                evidence_hash="b" * 64,
            ),
        ]
    )
    db_session.commit()

    first = analytics.persist_incident_diagnosis(
        db_session, incident_id=incident.id, high_confidence_enabled=True
    )
    second = analytics.persist_incident_diagnosis(
        db_session, incident_id=incident.id, high_confidence_enabled=True
    )

    assert first.id == second.id
    assert first.confidence == "high"
    assert db_session.query(models.Diagnosis).count() == 1


def test_incident_notification_only_triggers_for_create_reopen_or_severity_escalation():
    from services import incidentNotificationService as notifications

    assert notifications.should_send_incident_notification(
        created=True, reopened=False, severity_escalated=False
    ) is True
    assert notifications.should_send_incident_notification(
        created=False, reopened=True, severity_escalated=False
    ) is True
    assert notifications.should_send_incident_notification(
        created=False, reopened=False, severity_escalated=True
    ) is True
    assert notifications.should_send_incident_notification(
        created=False, reopened=False, severity_escalated=False
    ) is False


def test_expired_incident_silence_does_not_suppress_a_new_severity_notification(monkeypatch):
    from types import SimpleNamespace

    from services import incidentNotificationService as notifications

    monkeypatch.setattr(
        notifications,
        "incident_notification_config",
        lambda: {
            "enabled": True,
            "notify_administrators": True,
            "notify_project_owner": False,
            "notify_project_members": False,
            "extra_usernames": (),
            "feishu_enabled": False,
            "email_enabled": False,
        },
    )
    monkeypatch.setattr(notifications, "base_config", {"super_admin_usernames": ("admin",)})
    monkeypatch.setattr(notifications, "_project_recipients", lambda db, project_id: (None, ()))

    recipients = notifications.notify_incident(
        None,
        SimpleNamespace(
            project_id=1,
            silenced_until=datetime.now(timezone.utc) - timedelta(minutes=1),
        ),
        event="severity_escalated",
    )

    assert recipients == ("admin",)


def test_workload_adapter_only_returns_aggregated_time_window_asset_evidence():
    from services.workloadStorageAdapter import WorkloadRun, aggregate_workload_evidence

    evidence = aggregate_workload_evidence(
        [
            WorkloadRun(
                scheduler="slurm",
                project_id=1,
                hostname="compute-01",
                started_at=UTC_NOW,
                ended_at=UTC_NOW + timedelta(minutes=7),
                asset_ref=_asset(),
                raw_path="/never/persisted/path",
                job_id="98765",
            ),
        ]
    )

    assert evidence == [
        {
            "scheduler": "slurm",
            "project_id": 1,
            "hostname": "compute-01",
            "asset_ref": _asset().model_dump(),
            "window_start": UTC_NOW,
            "active_job_count": 1,
        },
        {
            "scheduler": "slurm",
            "project_id": 1,
            "hostname": "compute-01",
            "asset_ref": _asset().model_dump(),
            "window_start": UTC_NOW + timedelta(minutes=5),
            "active_job_count": 1,
        },
    ]


def test_restricted_ai_diagnosis_rejects_unknown_evidence_and_uses_deterministic_fallback():
    from services.incidentAiService import render_restricted_diagnosis

    diagnosis = {
        "incident_id": 7,
        "confidence": "medium",
        "candidates": [
            {
                "category": "device_fault",
                "score": 0.5,
                "evidence_refs": ["vendor:1"],
                "data_gaps": ["asset_mapping_missing"],
            }
        ],
        "evidence_ids": ["vendor:1"],
        "data_gaps": ["asset_mapping_missing"],
    }

    rendered = render_restricted_diagnosis(
        model_text="设备故障（90%）：证据 vendor:1、invented:2。",
        diagnosis=diagnosis,
    )

    assert rendered.used_fallback is True
    assert "invented:2" not in rendered.text
    assert "0.5" in rendered.text


def test_fixed_history_replay_meets_capacity_mape_and_rca_top_three_gates():
    from services import forecastIncidentService as analytics

    fixture_path = Path(__file__).parent / "fixtures" / "forecast-incident-replay.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    capacity = fixture["capacity_growth"]
    points = [
        (
            UTC_NOW - timedelta(days=capacity["days"] - 1 - offset),
            capacity["start_used"] + capacity["daily_growth"] * offset,
        )
        for offset in range(capacity["days"])
    ]

    mape = analytics.capacity_forecast_backtest_mape(
        _asset(),
        points=points,
        hard_limit=capacity["hard_limit"],
    )
    hit_rate = analytics.rca_top_three_hit_rate(
        [
            {
                "expected": case["expected"],
                "evidences": [
                    analytics.DiagnosisEvidence(
                        evidence_type=evidence_type,
                        evidence_ref=f"{case['expected']}:{index}",
                        observed_at=UTC_NOW,
                    )
                    for index, evidence_type in enumerate(case["evidence_types"])
                ],
            }
            for case in fixture["rca_cases"]
        ]
    )

    assert mape is not None and mape <= 15.0
    assert hit_rate >= 0.80


def test_performance_task_writes_only_after_three_consecutive_five_minute_anomalies():
    from celery_tasks.tasks import forecast_incidents

    rows = []
    for offset in range(28, 0, -1):
        observed_at = UTC_NOW - timedelta(days=offset)
        rows.append(
            {
                "storage_cluster_id": "7",
                "object_type": "volume",
                "object_id": "volume-a",
                "object_name": "volume-a",
                "latency_total": 1.0,
                "iops_total": 1.0,
                "throughput_total": 1.0,
                "collected_at": observed_at,
            }
        )
    for minutes in (0, 5, 10):
        rows.append(
            {
                "storage_cluster_id": "7",
                "object_type": "volume",
                "object_id": "volume-a",
                "object_name": "volume-a",
                "latency_total": 100.0,
                "iops_total": 100.0,
                "throughput_total": 100.0,
                "collected_at": UTC_NOW + timedelta(minutes=minutes),
            }
        )

    findings = forecast_incidents._performance_findings(rows, now=UTC_NOW + timedelta(minutes=10))

    assert {item["metric"] for item in findings} == {"latency", "iops", "throughput"}
    assert all(item["window_start"] == UTC_NOW for item in findings)


def test_performance_task_rejects_anomalies_with_a_missing_five_minute_window():
    from celery_tasks.tasks import forecast_incidents

    rows = []
    for offset in range(28, 0, -1):
        observed_at = UTC_NOW - timedelta(days=offset)
        rows.append(
            {
                "storage_cluster_id": "7",
                "object_type": "volume",
                "object_id": "volume-a",
                "object_name": "volume-a",
                "latency_total": 1.0,
                "iops_total": 1.0,
                "throughput_total": 1.0,
                "collected_at": observed_at,
            }
        )
    for minutes in (0, 5, 15):
        rows.append(
            {
                "storage_cluster_id": "7",
                "object_type": "volume",
                "object_id": "volume-a",
                "object_name": "volume-a",
                "latency_total": 100.0,
                "iops_total": 100.0,
                "throughput_total": 100.0,
                "collected_at": UTC_NOW + timedelta(minutes=minutes),
            }
        )

    assert forecast_incidents._performance_findings(
        rows, now=UTC_NOW + timedelta(minutes=15)
    ) == []


def test_capacity_forecast_task_is_registered_for_daily_utc_aligned_execution():
    from celery_worker import diskpulse_app

    entry = diskpulse_app.conf.beat_schedule["capacity_forecast_daily_task"]
    assert entry["task"] == "celery_tasks.tasks.forecast_incidents.capacity_forecast_daily_task"
