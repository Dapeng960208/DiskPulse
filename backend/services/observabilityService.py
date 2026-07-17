# -*- coding: utf-8 -*-
import hmac
from pathlib import Path

import redis
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from sqlalchemy import create_engine, select, text

from appConfig import base_config
from crud import telemetryCollectionRunCrud
from models import StorageCluster
from services.telemetryObservabilityService import COMPONENTS, telemetry_freshness


METRICS_REGISTRY = CollectorRegistry(auto_describe=True)
HTTP_REQUESTS = Counter(
    "diskpulse_http_requests_total",
    "HTTP requests handled by DiskPulse",
    ("method", "route", "status_code"),
    registry=METRICS_REGISTRY,
)
HTTP_DURATION = Histogram(
    "diskpulse_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "route", "status_code"),
    registry=METRICS_REGISTRY,
)
DEPENDENCY_READY = Gauge(
    "diskpulse_dependency_ready",
    "Dependency readiness state",
    ("component", "cluster_id"),
    registry=METRICS_REGISTRY,
)
TELEMETRY_FRESHNESS = Gauge(
    "diskpulse_telemetry_freshness_seconds",
    "Age of the latest successful telemetry collection",
    ("component", "cluster_id"),
    registry=METRICS_REGISTRY,
)
TELEMETRY_STATUS = Gauge(
    "diskpulse_telemetry_status",
    "Telemetry state: unknown=0, fresh=1, stale=2",
    ("component", "cluster_id"),
    registry=METRICS_REGISTRY,
)
TELEMETRY_LAST_SUCCESS = Gauge(
    "diskpulse_telemetry_last_success_timestamp_seconds",
    "UTC timestamp of the latest successful telemetry collection",
    ("component", "cluster_id"),
    registry=METRICS_REGISTRY,
)
STATUS_VALUES = {"unknown": 0, "fresh": 1, "stale": 2}
_telemetry_metric_labels: set[tuple[str, str]] = set()


def _probe_engine(url: str, *, connect_args: dict | None = None):
    return create_engine(
        url,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
        connect_args=connect_args or {},
    )


def _check_sqlalchemy(url: str, *, connect_args: dict | None = None) -> bool:
    engine = None
    try:
        engine = _probe_engine(url, connect_args=connect_args)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        if engine is not None:
            engine.dispose()


def check_dependencies() -> dict[str, bool]:
    postgres = _check_sqlalchemy(
        base_config.get_sqlalchemy_database_url(),
        connect_args={"connect_timeout": 1},
    )
    try:
        redis.Redis(
            host=base_config.get("redis.host"),
            port=base_config.get("redis.port", 6379),
            socket_connect_timeout=1,
            socket_timeout=1,
        ).ping()
        redis_ready = True
    except Exception:
        redis_ready = False
    questdb = _check_sqlalchemy(base_config.get_quest_db_url())
    return {"postgres": postgres, "redis": redis_ready, "questdb": questdb}


def update_dependency_metrics(dependencies: dict[str, bool]) -> None:
    for dependency in ("postgres", "redis", "questdb"):
        DEPENDENCY_READY.labels(component=dependency, cluster_id="").set(
            1 if dependencies.get(dependency) else 0
        )


def read_metrics_token() -> str | None:
    path = base_config.resolve_path("observability.metrics_token_file")
    if path is None:
        return None
    try:
        token = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return token or None


def metrics_token_is_valid(value: str | None) -> bool:
    expected = read_metrics_token()
    if not value or not expected:
        return False
    return hmac.compare_digest(value, expected)


def record_http_request(request, response, duration_seconds: float) -> None:
    route = request.scope.get("route")
    route_template = getattr(route, "path", None) or "unmatched"
    labels = {
        "method": request.method.upper(),
        "route": route_template,
        "status_code": str(response.status_code),
    }
    HTTP_REQUESTS.labels(**labels).inc()
    HTTP_DURATION.labels(**labels).observe(duration_seconds)


def refresh_telemetry_metrics(session_factory) -> None:
    global _telemetry_metric_labels
    db = session_factory()
    try:
        active_cluster_ids = tuple(
            db.execute(
                select(StorageCluster.id)
                .where(StorageCluster.is_active.is_(True))
                .order_by(StorageCluster.id)
            ).scalars()
        )
        latest_by_key = {}
        for run in telemetryCollectionRunCrud.list_latest_success_runs(db, active_cluster_ids):
            latest_by_key.setdefault((run.component, run.storage_cluster_id), run)
    finally:
        db.close()

    current_labels = {
        (component, str(cluster_id))
        for component in COMPONENTS
        for cluster_id in active_cluster_ids
    }
    for component, cluster_id in _telemetry_metric_labels - current_labels:
        TELEMETRY_FRESHNESS.remove(component, cluster_id)
        TELEMETRY_STATUS.remove(component, cluster_id)
        TELEMETRY_LAST_SUCCESS.remove(component, cluster_id)
    _telemetry_metric_labels = current_labels

    for component, cluster_id in current_labels:
        run = latest_by_key.get((component, int(cluster_id)))
        freshness = telemetry_freshness(
            component,
            run.finished_at if run else None,
            data_state=run.data_state if run else None,
        )
        TELEMETRY_STATUS.labels(component=component, cluster_id=cluster_id).set(
            STATUS_VALUES[freshness.status]
        )
        if freshness.last_success_at is None:
            continue
        TELEMETRY_FRESHNESS.labels(component=component, cluster_id=cluster_id).set(
            freshness.age_seconds or 0
        )
        TELEMETRY_LAST_SUCCESS.labels(component=component, cluster_id=cluster_id).set(
            freshness.last_success_at.timestamp()
        )


def render_metrics(session_factory) -> bytes:
    dependencies = check_dependencies()
    update_dependency_metrics(dependencies)
    if dependencies["postgres"]:
        try:
            refresh_telemetry_metrics(session_factory)
        except Exception:
            DEPENDENCY_READY.labels(component="postgres", cluster_id="").set(0)
    return generate_latest(METRICS_REGISTRY)
