# -*- coding: utf-8 -*-
import importlib
import importlib.util
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

import models
from questdb.database import QuestDBBase
from routers import storage_cluster
from utils.isilonClient import IsilonClient
from utils.netAppClient import NetAppClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
START = datetime(2026, 7, 1, tzinfo=timezone.utc)
END = datetime(2026, 7, 2, tzinfo=timezone.utc)


def _analytics():
    return importlib.import_module("services.storageHealthAnalyticsService")


def _query_params(**overrides):
    params = {"start_time": START.isoformat(), "end_time": END.isoformat()}
    params.update(overrides)
    return params


def test_capacity_change_uses_chronological_first_and_last_samples():
    result = _analytics().summarize_capacity(
        [
            {"updated_at": END, "used": 175.0},
            {"updated_at": START, "used": 100.0},
        ]
    )

    assert result == {
        "start_used": 100.0,
        "end_used": 175.0,
        "change": 75.0,
        "change_percent": 75.0,
        "points": [
            {"updated_at": START, "used": 100.0},
            {"updated_at": END, "used": 175.0},
        ],
    }


@pytest.mark.parametrize(
    ("points", "expected"),
    [
        (
            [{"updated_at": START, "used": 0.0}, {"updated_at": END, "used": 5.0}],
            {
                "start_used": 0.0,
                "end_used": 5.0,
                "change": 5.0,
                "change_percent": None,
                "points": [
                    {"updated_at": START, "used": 0.0},
                    {"updated_at": END, "used": 5.0},
                ],
            },
        ),
        (
            [],
            {
                "start_used": None,
                "end_used": None,
                "change": None,
                "change_percent": None,
                "points": [],
            },
        ),
    ],
    ids=["zero-baseline", "empty"],
)
def test_capacity_change_handles_zero_baseline_and_empty_data(points, expected):
    assert _analytics().summarize_capacity(points) == expected


def test_severity_summary_normalizes_and_merges_alert_sources():
    result = _analytics().summarize_severities(
        [
            {"source": "diskpulse", "severity": "high"},
            {"source": "diskpulse", "severity": "medium"},
            {"source": "netapp", "severity": "emergency"},
            {"source": "netapp", "severity": "error"},
            {"source": "isilon", "severity": "warning"},
            {"source": "isilon", "severity": "informational"},
        ]
    )

    assert result == {
        "counts": {"critical": 2, "error": 1, "warning": 2, "info": 1},
        "total": 6,
        "sources": {
            "diskpulse": {"critical": 1, "error": 0, "warning": 1, "info": 0},
            "netapp": {"critical": 1, "error": 1, "warning": 0, "info": 0},
            "isilon": {"critical": 0, "error": 0, "warning": 1, "info": 1},
        },
    }


def test_top_latency_ranks_by_p95_and_applies_limit():
    rows = [
        {
            "object_id": str(index),
            "object_name": f"volume-{index}",
            "object_type": "volume",
            "p95_latency": float(index),
            "avg_latency": float(index) / 2,
            "max_latency": float(index) + 1,
            "sample_count": index + 1,
        }
        for index in range(12)
    ]

    result = _analytics().rank_top_latency(rows, limit=10)

    assert [row["object_id"] for row in result] == [str(index) for index in range(11, 1, -1)]
    assert all({"p95_latency", "avg_latency", "max_latency", "sample_count"} <= row.keys() for row in result)


def test_repeated_faults_group_vendor_events_only():
    result = _analytics().group_repeated_faults(
        [
            {"source": "netapp", "fingerprint": "disk.offline:disk-1", "occurred_at": START},
            {"source": "netapp", "fingerprint": "disk.offline:disk-1", "occurred_at": END},
            {"source": "isilon", "fingerprint": "node.down:node-1", "occurred_at": START},
            {"source": "diskpulse", "fingerprint": "quota:group-1", "occurred_at": START},
            {"source": "diskpulse", "fingerprint": "quota:group-1", "occurred_at": END},
        ]
    )

    assert result == [
        {
            "source": "netapp",
            "fingerprint": "disk.offline:disk-1",
            "count": 2,
            "first_occurred_at": START,
            "last_occurred_at": END,
        }
    ]


@pytest.mark.parametrize(
    ("start_time", "end_time", "message"),
    [
        (START, START, "start_time must be before end_time"),
        (START, START + timedelta(days=181), "180 days"),
    ],
)
def test_analytics_time_range_validation(start_time, end_time, message):
    with pytest.raises(ValueError, match=message):
        _analytics().validate_time_range(start_time, end_time)


@pytest.fixture
def analytics_client(api_client_factory, db_session):
    db_session.add(
        models.StorageCluster(
            id=1,
            name="cluster-a",
            storage_type="netapp",
            storage_host="storage.local",
            is_active=True,
        )
    )
    db_session.commit()
    return api_client_factory([storage_cluster.router], authenticated=False)


@pytest.mark.parametrize(
    ("endpoint", "service_name", "payload"),
    [
        ("capacity-change", "get_capacity_change", {"start_used": None, "points": []}),
        ("error-severity", "get_error_severity", {"counts": {}, "total": 0}),
        ("top-latency", "get_top_latency", []),
        ("repeated-faults", "get_repeated_faults", []),
    ],
)
def test_storage_health_read_endpoints_return_service_results(
    analytics_client, endpoint, service_name, payload
):
    with patch(f"routers.storage_cluster.{service_name}", return_value=payload):
        response = analytics_client.get(
            f"/storage-pulse/api/storage-clusters/1/analytics/{endpoint}",
            params=_query_params(),
        )

    assert response.status_code == 200
    assert response.json() == payload


@pytest.mark.parametrize(
    "params",
    [
        _query_params(end_time=START.isoformat()),
        _query_params(end_time=(START + timedelta(days=181)).isoformat()),
    ],
    ids=["reversed", "over-180-days"],
)
def test_storage_health_endpoint_rejects_invalid_time_ranges(analytics_client, params):
    response = analytics_client.get(
        "/storage-pulse/api/storage-clusters/1/analytics/capacity-change",
        params=params,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("export_format", "section", "media_type", "filename"),
    [
        ("csv", "capacity", "text/csv", "storage-health-capacity.csv"),
        (
            "excel",
            "all",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "storage-health.xlsx",
        ),
        ("pdf", "all", "application/pdf", "storage-health.pdf"),
        ("csv", "all", "application/zip", "storage-health-csv.zip"),
    ],
)
def test_storage_health_export_media_contract(
    analytics_client, export_format, section, media_type, filename
):
    with patch(
        "routers.storage_cluster.export_storage_health",
        return_value=(b"report", media_type, filename),
    ):
        response = analytics_client.get(
            "/storage-pulse/api/storage-clusters/1/analytics/export",
            params=_query_params(format=export_format, section=section),
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(media_type)
    assert filename in response.headers["content-disposition"]


def test_netapp_client_exposes_ems_and_volume_metrics_contracts():
    client = object.__new__(NetAppClient)
    client._get_all_records = Mock(side_effect=[[{"index": 7}], [{"uuid": "volume-1"}]])
    since = "2026-07-15T00:00:00Z"

    assert client.get_ems_events(since) == [{"index": 7}]
    assert client.get_volume_metrics() == [{"uuid": "volume-1"}]

    event_call, metrics_call = client._get_all_records.call_args_list
    assert event_call.args[0] == "support/ems/events"
    assert event_call.kwargs["params"]["time"] == f">={since}"
    assert {"time", "index", "message", "node", "log_message"} <= set(
        event_call.kwargs["params"]["fields"].split(",")
    )
    assert metrics_call.args[0] == "storage/volumes"
    assert {"uuid", "name", "metrics"} <= set(metrics_call.kwargs["params"]["fields"].split(","))


def test_isilon_client_discovers_platform_version_before_statistics_and_events():
    client = object.__new__(IsilonClient)
    client.api_version = "1"
    client._get = Mock(
        side_effect=[
            {"latest": 16},
            {"stats": [{"key": "ifs.ops.latency"}]},
            {"eventgroups": [{"id": "event-1"}]},
            {"eventlists": [{"id": "event-list-1"}]},
        ]
    )

    assert client.discover_api_version() == "16"
    assert client.get_performance_statistics() == [{"key": "ifs.ops.latency"}]
    assert client.get_event_group_occurrences() == [{"id": "event-1"}]
    assert client.get_event_lists() == [{"id": "event-list-1"}]
    assert [call.args[0] for call in client._get.call_args_list] == [
        "/latest",
        "/16/statistics/current",
        "/16/event/eventgroup-occurrences",
        "/16/event/eventlists",
    ]


def test_storage_alert_model_and_postgres_migration_contract():
    table = models.StorageAlerts.__table__
    assert {"storage_cluster_id", "source", "external_event_id", "fingerprint", "severity"} <= set(
        table.columns.keys()
    )
    assert table.c.storage_cluster_id.foreign_keys
    assert any(
        {column.name for column in constraint.columns}
        == {"storage_cluster_id", "source", "external_event_id"}
        for constraint in table.constraints
    )
    assert {
        ("storage_cluster_id", "updated_at"),
        ("severity", "updated_at"),
        ("fingerprint", "updated_at"),
    } <= {tuple(column.name for column in index.columns) for index in table.indexes}

    migrations = list((BACKEND_ROOT / "migrate" / "versions").glob("*storage_health*.py"))
    assert len(migrations) == 1, "expected one PostgreSQL storage health migration"
    spec = importlib.util.spec_from_file_location(migrations[0].stem, migrations[0])
    migration = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(migration)
    assert migration.down_revision == "000000000002"

    output = io.StringIO()
    migration.op = Operations(
        MigrationContext.configure(
            dialect_name="postgresql",
            opts={"as_sql": True, "output_buffer": output},
        )
    )
    migration.upgrade()
    sql = " ".join(output.getvalue().lower().split())
    for token in ("storage_cluster_id", "source", "external_event_id", "fingerprint", "severity"):
        assert token in sql
    assert "unique" in sql
    assert sql.count("create index") >= 3


def test_questdb_performance_model_and_migration_contract():
    table = QuestDBBase.metadata.tables["storage_performance_metrics"]
    assert {
        "storage_cluster_id",
        "vendor",
        "object_type",
        "object_id",
        "object_name",
        "latency_read",
        "latency_write",
        "latency_total",
        "iops_total",
        "throughput_total",
        "collected_at",
    } <= set(table.columns.keys())

    migrations = list((BACKEND_ROOT / "questdb" / "migrations").glob("*_storage_performance_metrics.sql"))
    assert len(migrations) == 1, "expected one QuestDB performance migration"
    sql = " ".join(migrations[0].read_text(encoding="utf-8").lower().split())
    assert "create table" in sql
    assert "storage_performance_metrics" in sql
    assert "partition by day" in sql
    assert "wal" in sql
    assert "ttl 180 days" in sql


def test_celery_schedules_event_and_performance_collection():
    source = (BACKEND_ROOT / "celery_worker.py").read_text(encoding="utf-8")

    assert '"storage_events_schedule_fetching_task"' in source
    assert '"task": "celery_tasks.tasks.storage_health.storage_events_schedule_fetching_task"' in source
    assert '"schedule": 60.0' in source
    assert '"storage_performance_schedule_fetching_task"' in source
    assert '"task": "celery_tasks.tasks.storage_health.storage_performance_schedule_fetching_task"' in source
    assert '"schedule": 300.0' in source
