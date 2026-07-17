# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import models
from appConfig import base_config
from utils.security import issue_token


UTC_NOW = datetime(2026, 7, 18, 8, 0, tzinfo=timezone.utc)


def _run_payload(**overrides):
    payload = {
        "task_id": "celery-task-1",
        "attempt": 1,
        "scope_type": "cluster",
        "scope_key": "1",
        "storage_cluster_id": 1,
        "component": "capacity",
        "trace_id": "4b7b1574-f6ca-4373-af40-a94c2b1b9cb5",
        "started_at": UTC_NOW,
    }
    payload.update(overrides)
    return payload


def test_telemetry_run_lifecycle_uses_utc_and_persists_only_safe_outcome_fields(session_factory):
    from services import telemetryObservabilityService as telemetry

    started = telemetry.start_collection_run(
        session_factory,
        **_run_payload(),
    )
    assert isinstance(started.id, UUID)
    assert started.outcome is None
    assert started.started_at.tzinfo is not None

    completed = telemetry.complete_collection_run(
        session_factory,
        started.id,
        outcome="success",
        data_state="empty",
        records_written=0,
    )
    assert completed.outcome == "success"
    assert completed.data_state == "empty"
    assert completed.records_written == 0
    assert completed.error_code is None
    assert completed.finished_at.tzinfo is not None

    failed = telemetry.start_collection_run(
        session_factory,
        **_run_payload(task_id="celery-task-2", trace_id="c12a1b81-2d6d-4eb2-b41f-71a2c5974235"),
    )
    failed = telemetry.complete_collection_run(
        session_factory,
        failed.id,
        outcome="failed",
        error_code="vendor_timeout",
    )
    assert (failed.data_state, failed.records_written, failed.error_code) == (None, None, None)


@pytest.mark.parametrize(
    ("component", "age_seconds", "expected"),
    [
        ("capacity", 150, "fresh"),
        ("capacity", 151, "stale"),
        ("vendor_events", 150, "fresh"),
        ("performance", 630, "fresh"),
        ("performance", 631, "stale"),
    ],
)
def test_freshness_boundaries(component, age_seconds, expected):
    from services.telemetryObservabilityService import telemetry_freshness

    assert telemetry_freshness(
        component,
        UTC_NOW - timedelta(seconds=age_seconds),
        now=UTC_NOW,
    ).status == expected


def test_freshness_is_unknown_without_success_and_empty_is_fresh():
    from services.telemetryObservabilityService import telemetry_freshness

    assert telemetry_freshness("capacity", None, now=UTC_NOW).status == "unknown"
    result = telemetry_freshness("capacity", UTC_NOW, now=UTC_NOW, data_state="empty")
    assert (result.status, result.data_state) == ("fresh", "empty")


@pytest.mark.parametrize(
    ("error", "phase", "expected"),
    [
        (TimeoutError(), "vendor", "vendor_timeout"),
        (RuntimeError(), "postgres", "postgres"),
        (RuntimeError(), "questdb", "questdb"),
        (RuntimeError(), "vendor", "unknown"),
    ],
)
def test_error_classifier_never_returns_raw_error(error, phase, expected):
    from services.telemetryObservabilityService import classify_error_code

    assert classify_error_code(error, phase=phase) == expected


def test_scheduler_lock_skip_does_not_create_cluster_success(session_factory):
    from services import telemetryObservabilityService as telemetry

    run = telemetry.record_scheduler_skip(
        session_factory,
        task_id="scheduler-task",
        attempt=1,
        component="performance",
        trace_id="e6141dd4-3494-4864-9e0a-8c4e9b03da61",
    )
    assert (run.scope_type, run.scope_key, run.outcome) == ("scheduler", "scheduler", "skipped")
    assert run.storage_cluster_id is None
    assert run.data_state is run.records_written is run.error_code is None


def test_list_runs_matches_deleted_cluster_history_by_scope_key(session_factory):
    from services import telemetryObservabilityService as telemetry

    telemetry.start_collection_run(session_factory, **_run_payload())
    telemetry.start_collection_run(
        session_factory,
        **_run_payload(task_id="another-task", scope_key="2", storage_cluster_id=None),
    )

    content, total = telemetry.list_collection_runs(session_factory(), cluster_id=1, page=1, size=20)
    assert total == 1
    assert content[0].scope_key == "1"


def test_probe_endpoints_short_circuit_database_middleware(monkeypatch):
    import main

    monkeypatch.setattr(main, "SessionLocal", Mock(side_effect=AssertionError("database must not be opened")))
    client = TestClient(main.app)

    response = client.get("/storage-pulse/api/v1/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_has_stable_ready_degraded_and_not_ready_responses(monkeypatch):
    import main
    from services import observabilityService

    client = TestClient(main.app)
    monkeypatch.setattr(
        observabilityService,
        "check_dependencies",
        lambda: {"postgres": True, "redis": True, "questdb": True},
    )
    assert client.get("/storage-pulse/api/v1/readyz").json() == {"status": "ready"}

    monkeypatch.setattr(
        observabilityService,
        "check_dependencies",
        lambda: {"postgres": True, "redis": True, "questdb": False},
    )
    assert client.get("/storage-pulse/api/v1/readyz").json() == {"status": "degraded"}

    monkeypatch.setattr(
        observabilityService,
        "check_dependencies",
        lambda: {"postgres": False, "redis": True, "questdb": True},
    )
    response = client.get("/storage-pulse/api/v1/readyz")
    assert (response.status_code, response.json()) == (503, {"status": "not_ready"})


def test_metrics_requires_file_token_and_hides_postgres_failure(tmp_path, monkeypatch):
    import main
    from services import observabilityService

    token_file = Path(tmp_path) / "metrics.token"
    token_file.write_text("metrics-test-token\n", encoding="utf-8")
    base_config.set("observability.metrics_token_file", str(token_file))
    monkeypatch.setattr(
        observabilityService,
        "check_dependencies",
        lambda: {"postgres": False, "redis": True, "questdb": True},
    )
    monkeypatch.setattr(observabilityService, "refresh_telemetry_metrics", Mock())
    client = TestClient(main.app)

    assert client.get("/storage-pulse/api/v1/metrics").status_code == 403
    response = client.get(
        "/storage-pulse/api/v1/metrics",
        headers={"X-Metrics-Token": "metrics-test-token"},
    )

    assert response.status_code == 200
    assert "diskpulse_dependency_ready{cluster_id=\"\",component=\"postgres\"} 0.0" in response.text
    assert "diskpulse_http_requests_total" in response.text
    assert "postgresql" not in response.text.lower()


def test_telemetry_runs_api_requires_super_admin_and_returns_safe_paginated_fields(
    db_session, session_factory, monkeypatch
):
    import main
    from services import telemetryObservabilityService as telemetry

    db_session.add_all(
        [
            models.User(id=1, rd_username="alice"),
            models.User(id=2, rd_username="reader"),
            models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"),
        ]
    )
    db_session.commit()
    run = telemetry.start_collection_run(session_factory, **_run_payload())
    telemetry.complete_collection_run(
        session_factory,
        run.id,
        outcome="success",
        data_state="data",
        records_written=3,
    )
    monkeypatch.setattr(main, "SessionLocal", session_factory)
    client = TestClient(main.app)

    assert client.get("/storage-pulse/api/v1/telemetry-runs").status_code == 401
    reader = client.get(
        "/storage-pulse/api/v1/telemetry-runs",
        headers={"Authorization": f"Bearer {issue_token(2)}"},
    )
    assert reader.status_code == 403

    response = client.get(
        "/storage-pulse/api/v1/telemetry-runs",
        params={"cluster_id": 1, "component": "capacity", "page": 1, "size": 20},
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    item = payload["content"][0]
    assert {
        "run_id",
        "trace_id",
        "scope_type",
        "scope_key",
        "storage_cluster_id",
        "component",
        "outcome",
        "data_state",
        "records_written",
        "error_code",
        "started_at",
        "finished_at",
    } == set(item)
    assert "task_id" not in item
