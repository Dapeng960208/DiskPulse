# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
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
    assert (failed.data_state, failed.records_written, failed.error_code) == (
        None,
        None,
        "vendor_timeout",
    )


def test_pending_telemetry_run_cannot_persist_terminal_fields(session_factory):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with session_factory() as db:
            db.add(
                models.TelemetryCollectionRun(
                    **_run_payload(task_id="pending-terminal-fields", finished_at=UTC_NOW)
                )
            )
            db.commit()


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


def test_latest_success_runs_returns_only_each_component_cluster_latest_row(session_factory):
    from crud import telemetryCollectionRunCrud
    from services import telemetryObservabilityService as telemetry

    with session_factory() as db:
        db.add(models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"))
        db.commit()

    older = telemetry.start_collection_run(
        session_factory,
        **_run_payload(task_id="older-success", started_at=UTC_NOW - timedelta(minutes=2)),
    )
    telemetry.complete_collection_run(
        session_factory,
        older.id,
        outcome="success",
        data_state="data",
        records_written=1,
        finished_at=UTC_NOW - timedelta(minutes=1),
    )
    latest = telemetry.start_collection_run(
        session_factory,
        **_run_payload(task_id="latest-success", started_at=UTC_NOW - timedelta(seconds=30)),
    )
    telemetry.complete_collection_run(
        session_factory,
        latest.id,
        outcome="success",
        data_state="empty",
        records_written=0,
        finished_at=UTC_NOW,
    )

    with session_factory() as db:
        rows = telemetryCollectionRunCrud.list_latest_success_runs(db, (1,))

    assert [row.id for row in rows] == [latest.id]


def test_probe_endpoints_short_circuit_database_middleware(monkeypatch):
    import main

    monkeypatch.setattr(main, "SessionLocal", Mock(side_effect=AssertionError("database must not be opened")))
    client = TestClient(main.app)

    response = client.get("/storage-pulse/api/v1/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unhandled_http_error_is_recorded_as_a_500_metric(monkeypatch):
    import main

    def raise_unhandled_error():
        raise RuntimeError("expected test error")

    main.app.add_api_route("/_telemetry-test-error", raise_unhandled_error)
    recorded = Mock()
    monkeypatch.setattr(main.observabilityService, "record_http_request", recorded)
    client = TestClient(main.app, raise_server_exceptions=False)

    response = client.get("/_telemetry-test-error")

    assert response.status_code == 500
    assert recorded.call_args.args[1].status_code == 500


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


def test_dependency_checks_run_concurrently(monkeypatch):
    import time

    from services import observabilityService

    def slow_check(*_args, **_kwargs):
        time.sleep(0.2)
        return True

    class SlowRedis:
        def ping(self):
            time.sleep(0.2)
            return True

    monkeypatch.setattr(observabilityService, "_check_sqlalchemy", slow_check)
    monkeypatch.setattr(observabilityService.redis, "Redis", lambda **_kwargs: SlowRedis())

    started = time.perf_counter()
    result = observabilityService.check_dependencies()

    assert result == {"postgres": True, "redis": True, "questdb": True}
    assert time.perf_counter() - started < 0.5


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


def test_metrics_does_not_pass_the_application_session_factory(tmp_path, monkeypatch):
    import main
    from services import observabilityService

    token_file = Path(tmp_path) / "metrics.token"
    token_file.write_text("metrics-test-token\n", encoding="utf-8")
    base_config.set("observability.metrics_token_file", str(token_file))
    render_metrics = Mock(return_value=b"# metrics\n")
    monkeypatch.setattr(observabilityService, "render_metrics", render_metrics)
    client = TestClient(main.app)

    response = client.get(
        "/storage-pulse/api/v1/metrics",
        headers={"X-Metrics-Token": "metrics-test-token"},
    )

    assert response.status_code == 200
    render_metrics.assert_called_once_with()


def test_metrics_default_session_factory_uses_and_disposes_a_dedicated_probe_engine(monkeypatch):
    from services import observabilityService

    probe_engine = Mock()
    session_factory = Mock()
    monkeypatch.setattr(
        observabilityService,
        "check_dependencies",
        lambda: {"postgres": True, "redis": True, "questdb": True},
    )
    monkeypatch.setattr(observabilityService, "_probe_engine", Mock(return_value=probe_engine))
    monkeypatch.setattr(observabilityService, "sessionmaker", Mock(return_value=session_factory))
    refresh_telemetry_metrics = Mock()
    monkeypatch.setattr(
        observabilityService,
        "refresh_telemetry_metrics",
        refresh_telemetry_metrics,
    )

    observabilityService.render_metrics()

    observabilityService._probe_engine.assert_called_once_with(
        base_config.get_sqlalchemy_database_url(),
        connect_args={"connect_timeout": 1},
    )
    observabilityService.sessionmaker.assert_called_once_with(
        autocommit=False,
        autoflush=False,
        bind=probe_engine,
    )
    refresh_telemetry_metrics.assert_called_once_with(session_factory)
    probe_engine.dispose.assert_called_once_with()


def test_metrics_removes_cached_freshness_when_postgres_becomes_unavailable(monkeypatch):
    from services import observabilityService

    observabilityService._telemetry_metric_labels = {("capacity", "1")}
    observabilityService.TELEMETRY_STATUS.labels(component="capacity", cluster_id="1").set(1)
    observabilityService.TELEMETRY_FRESHNESS.labels(component="capacity", cluster_id="1").set(5)
    observabilityService.TELEMETRY_LAST_SUCCESS.labels(component="capacity", cluster_id="1").set(UTC_NOW.timestamp())
    monkeypatch.setattr(
        observabilityService,
        "check_dependencies",
        lambda: {"postgres": False, "redis": True, "questdb": True},
    )

    response = observabilityService.render_metrics(Mock())

    assert b'diskpulse_telemetry_status{cluster_id="1"' not in response


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


def test_isolated_vendor_collection_records_cluster_success_and_failure(session_factory):
    from celery_tasks.tasks import storage_health

    with session_factory() as db:
        db.add_all(
            [
                models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"),
                models.StorageCluster(id=2, name="cluster-b", storage_type="netapp"),
            ]
        )
        db.commit()

    def collect(cluster_id):
        if cluster_id == 2:
            raise TimeoutError()
        return 4

    summary = storage_health.run_isolated(
        [1, 2],
        collect,
        telemetry_context={
            "task_id": "vendor-task",
            "attempt": 1,
            "trace_id": "698195ec-302f-4c7e-a583-2de7f2948f4c",
        },
        component="vendor_events",
        session_factory=session_factory,
    )

    assert summary == {"succeeded_clusters": (1,), "failed_clusters": (2,)}
    with session_factory() as db:
        rows = db.query(models.TelemetryCollectionRun).order_by(models.TelemetryCollectionRun.scope_key).all()
    assert [(row.outcome, row.records_written, row.data_state, row.error_code) for row in rows] == [
        ("success", 4, "data", None),
        ("failed", None, None, "vendor_timeout"),
    ]


def test_explicitly_unsupported_collection_is_a_success_without_samples(session_factory):
    from celery_tasks.tasks import storage_health

    with session_factory() as db:
        db.add(models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"))
        db.commit()

    summary = storage_health.run_isolated(
        [1],
        lambda _cluster_id: (_ for _ in ()).throw(ValueError("Unsupported storage type: legacy")),
        telemetry_context={
            "task_id": "unsupported-task",
            "attempt": 1,
            "trace_id": "bd0c4595-6eef-44b0-8411-91e6d6bb778d",
        },
        component="performance",
        session_factory=session_factory,
    )

    assert summary == {"succeeded_clusters": (1,), "failed_clusters": ()}
    with session_factory() as db:
        run = db.query(models.TelemetryCollectionRun).one()
    assert (run.outcome, run.data_state, run.records_written) == ("success", "unsupported", 0)


def test_explicitly_unsupported_capacity_collection_is_a_success_without_samples(session_factory):
    from celery_tasks.tasks import storages

    with session_factory() as db:
        db.add(models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"))
        db.commit()

    class UnsupportedMonitor:
        def __init__(self, _db, _logger, _cluster):
            pass

        def collect_postgres(self):
            raise ValueError("Unsupported storage type: legacy")

        def close(self):
            pass

    summary = storages.run_collection_round(
        ({"storage_cluster_id": 1},),
        session_factory=session_factory,
        monitor_factory=UnsupportedMonitor,
        telemetry_context={
            "task_id": "capacity-unsupported-task",
            "attempt": 1,
            "trace_id": "cd40a2d4-59c4-4412-bc20-9a1ed01edbc2",
        },
    )

    assert summary["succeeded_clusters"] == (1,)
    with session_factory() as db:
        run = db.query(models.TelemetryCollectionRun).one()
    assert (run.outcome, run.data_state, run.records_written) == ("success", "unsupported", 0)


def test_telemetry_cleanup_deletes_expired_rows_in_batches_and_retries_on_failure(
    session_factory, monkeypatch
):
    from celery_tasks.tasks import telemetry as telemetry_tasks

    with session_factory() as db:
        db.add(
            models.TelemetryCollectionRun(
                **_run_payload(task_id="expired-run"),
                outcome="success",
                data_state="empty",
                records_written=0,
                finished_at=UTC_NOW,
                created_at=UTC_NOW - timedelta(days=91),
            )
        )
        db.commit()

    @contextmanager
    def lock(_name, expires):
        assert expires == 1800
        yield True

    monkeypatch.setattr(telemetry_tasks, "SessionLocal", session_factory)
    monkeypatch.setattr(telemetry_tasks, "redis_lock", lock)
    monkeypatch.setattr(telemetry_tasks, "utc_now", lambda: UTC_NOW)

    assert telemetry_tasks.telemetry_collection_runs_cleanup_task.run() == {"deleted": 1}
    with session_factory() as db:
        assert db.query(models.TelemetryCollectionRun).count() == 0


def test_telemetry_cleanup_rethrows_after_safe_notification_failure(monkeypatch):
    from celery_tasks.tasks import telemetry as telemetry_tasks

    @contextmanager
    def lock(_name, expires):
        assert expires == 1800
        yield True

    monkeypatch.setattr(telemetry_tasks, "redis_lock", lock)
    monkeypatch.setattr(telemetry_tasks, "purge_expired_collection_runs", Mock(side_effect=RuntimeError("db down")))
    monkeypatch.setattr(telemetry_tasks, "_notify_cleanup_failure", Mock(side_effect=RuntimeError("notify down")))

    with pytest.raises(RuntimeError, match="db down"):
        telemetry_tasks.telemetry_collection_runs_cleanup_task.run()


def test_telemetry_cleanup_processes_all_expired_batches(session_factory, monkeypatch):
    from celery_tasks.tasks import telemetry as telemetry_tasks

    with session_factory() as db:
        db.add_all(
            models.TelemetryCollectionRun(
                **_run_payload(task_id=f"expired-{index}"),
                outcome="success",
                data_state="empty",
                records_written=0,
                finished_at=UTC_NOW,
                created_at=UTC_NOW - timedelta(days=91),
            )
            for index in range(1001)
        )
        db.commit()

    @contextmanager
    def lock(_name, expires):
        assert expires == 1800
        yield True

    monkeypatch.setattr(telemetry_tasks, "SessionLocal", session_factory)
    monkeypatch.setattr(telemetry_tasks, "redis_lock", lock)
    monkeypatch.setattr(telemetry_tasks, "utc_now", lambda: UTC_NOW)

    assert telemetry_tasks.telemetry_collection_runs_cleanup_task.run() == {"deleted": 1001}
    with session_factory() as db:
        assert db.query(models.TelemetryCollectionRun).count() == 0


def test_telemetry_model_contract_and_migration_compile_for_supported_dialects():
    import importlib.util
    import io

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration_path = Path(__file__).resolve().parents[1] / "migrate" / "versions" / "000000000008_telemetry_collection_runs.py"
    spec = importlib.util.spec_from_file_location("telemetry_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert models.TelemetryCollectionRun.__tablename__ == "telemetry_collection_runs"
    assert {"trace_id", "started_at", "finished_at", "outcome", "data_state"} <= set(
        models.TelemetryCollectionRun.__table__.columns.keys()
    )
    terminal_constraint = next(
        constraint
        for constraint in models.TelemetryCollectionRun.__table__.constraints
        if constraint.name == "ck_telemetry_run_terminal_fields"
    )
    assert "finished_at is not null" in str(terminal_constraint.sqltext).lower()
    ledger_index = next(
        index
        for index in models.TelemetryCollectionRun.__table__.indexes
        if index.name == "ix_telemetry_run_component_cluster_finished"
    )
    assert str(ledger_index.expressions[-1]).lower() == "finished_at desc"
    for dialect_name in ("sqlite", "postgresql", "mysql"):
        output = io.StringIO()
        migration.op = Operations(
            MigrationContext.configure(
                dialect_name=dialect_name,
                opts={"as_sql": True, "output_buffer": output},
            )
        )
        migration.upgrade()
        sql = output.getvalue().lower()
        assert "telemetry_collection_runs" in sql
        assert "trace_id" in sql
        assert "storage_cluster_id" in sql
        assert "finished_at is not null" in sql


@pytest.mark.parametrize("dialect_name", ("sqlite", "postgresql", "mysql"))
def test_telemetry_failure_code_migration_replaces_terminal_constraint(dialect_name):
    import importlib.util
    import io

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrate"
        / "versions"
        / "000000000010_telemetry_failed_error_code.py"
    )
    spec = importlib.util.spec_from_file_location("telemetry_failure_code_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    output = io.StringIO()
    migration.op = Operations(
        MigrationContext.configure(
            dialect_name=dialect_name,
            opts={"as_sql": True, "output_buffer": output},
        )
    )

    migration.upgrade()
    migration.downgrade()

    sql = output.getvalue().lower()
    assert "ck_telemetry_run_terminal_fields" in sql
    assert "outcome = 'failed'" in sql
    assert "error_code is not null" in sql


def test_telemetry_migration_upgrades_and_downgrades_sqlite():
    import importlib.util

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration_path = Path(__file__).resolve().parents[1] / "migrate" / "versions" / "000000000008_telemetry_collection_runs.py"
    spec = importlib.util.spec_from_file_location("telemetry_migration_sqlite", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    with sa.create_engine("sqlite://").begin() as connection:
        connection.execute(sa.text("CREATE TABLE storage_clusters (id INTEGER PRIMARY KEY)"))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = sa.inspect(connection)
        columns = {column["name"] for column in inspector.get_columns("telemetry_collection_runs")}
        assert {"id", "trace_id", "storage_cluster_id", "started_at", "created_at"} <= columns
        assert {
            "ix_telemetry_run_component_cluster_finished",
            "ix_telemetry_run_created_at",
        } <= {index["name"] for index in inspector.get_indexes("telemetry_collection_runs")}

        migration.downgrade()
        inspector.clear_cache()
        assert "telemetry_collection_runs" not in inspector.get_table_names()


def test_telemetry_failure_code_migration_upgrades_existing_sqlite_ledger():
    """Existing r8 ledgers accept classified failed runs after the r10 upgrade."""
    import importlib.util
    from uuid import uuid4

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migrations_dir = Path(__file__).resolve().parents[1] / "migrate" / "versions"

    def load_migration(filename, module_name):
        spec = importlib.util.spec_from_file_location(module_name, migrations_dir / filename)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        return migration

    r8 = load_migration("000000000008_telemetry_collection_runs.py", "telemetry_r8_sqlite")
    r10 = load_migration("000000000010_telemetry_failed_error_code.py", "telemetry_r10_sqlite")

    with sa.create_engine("sqlite://").begin() as connection:
        connection.execute(sa.text("CREATE TABLE storage_clusters (id INTEGER PRIMARY KEY)"))
        r8.op = Operations(MigrationContext.configure(connection))
        r8.upgrade()
        r10.op = Operations(MigrationContext.configure(connection))
        r10.upgrade()
        ledger = sa.Table("telemetry_collection_runs", sa.MetaData(), autoload_with=connection)

        # Review fix verification: the upgraded constraint must retain a failed error code.
        connection.execute(
            ledger.insert().values(
                id=str(uuid4()),
                task_id="r8-upgrade-failure",
                attempt=1,
                scope_type="cluster",
                scope_key="1",
                component="capacity",
                trace_id="f164d96d-647a-4303-82e8-5356031da939",
                started_at=UTC_NOW,
                finished_at=UTC_NOW,
                outcome="failed",
                error_code="vendor_timeout",
                created_at=UTC_NOW,
            )
        )

        assert connection.execute(
            sa.select(ledger.c.error_code).where(ledger.c.task_id == "r8-upgrade-failure")
        ).scalar_one() == "vendor_timeout"
