# -*- coding: utf-8 -*-
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Callable

from celery.utils.log import get_task_logger
from sqlalchemy import func, select, text

from celery_worker import diskpulse_app
from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from celery_tasks.tasks.redis_lock import redis_lock
from database import SessionLocal
from dependencies import QuestDBSession
from models import StorageAlerts, StorageCluster, Volume
from services.storageHealthAnalyticsService import normalize_severity
from services import telemetryObservabilityService


logger = get_task_logger(__name__)


def _enqueue_derived_analytics(*, component: str, succeeded_clusters: tuple[int, ...]) -> None:
    """Best-effort hand-off after raw facts have committed; never block collection."""
    if not succeeded_clusters:
        return
    try:
        from celery_tasks.tasks import forecast_incidents

        telemetry_task = forecast_incidents.telemetry_quality_snapshot_task
        telemetry_task.delay()
        if component == "vendor_events":
            for cluster_id in succeeded_clusters:
                forecast_incidents.vendor_event_evidence_task.delay(cluster_id)
        elif component == "performance":
            forecast_incidents.performance_anomaly_scan_task.delay()
    except Exception:
        logger.warning("Unable to enqueue derived analytics after %s collection", component)


def event_window_start(latest_event: datetime | None, now: datetime) -> datetime:
    return now - timedelta(hours=24) if latest_event is None else latest_event - timedelta(minutes=5)


def _datetime(value, default: datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    elif isinstance(value, (int, float)):
        result = datetime.fromtimestamp(value)
    else:
        result = default or datetime.now()
    if result.tzinfo is not None:
        return result.astimezone().replace(tzinfo=None)
    return result


def _utc_z(value: datetime) -> str:
    value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat(timespec="seconds") + "Z"


def _event_identity(vendor: str, record: dict) -> tuple[str, str, str, str]:
    if vendor == "netapp":
        node = record.get("node") or {}
        message = record.get("message") or {}
        object_id = str(node.get("uuid") or node.get("name") or "cluster")
        event_code = str(message.get("name") or "unknown")
        external_id = f"{object_id}:{record.get('index')}"
        return external_id, event_code, "node", object_id

    object_data = record.get("node") or record.get("object") or {}
    specifier = record.get("specifier") or {}
    causes = record.get("causes") or []
    cause = causes[0] if causes else []
    object_id = str(
        record.get("devid")
        or record.get("node_id")
        or object_data.get("id")
        or object_data.get("name")
        or specifier.get("devid")
        or "cluster"
    )
    event_code = str(
        record.get("event_type")
        or record.get("event_type_id")
        or record.get("event")
        or record.get("name")
        or (cause[0] if cause else None)
        or "unknown"
    )
    external_id = record.get("id") or record.get("eventgroup_instance_id")
    if external_id is None:
        external_id = hashlib.sha256(
            json.dumps(record, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
    return str(external_id), event_code, "node", object_id


def normalize_vendor_events(
    storage_cluster_id: int,
    vendor: str,
    records: list[dict],
) -> list[dict]:
    rows = []
    expanded_records = [
        event
        for record in records
        for event in (
            record["events"]
            if isinstance(record.get("events"), list)
            else [record]
        )
    ]
    for record in expanded_records:
        causes = record.get("causes") or []
        cause = causes[0] if causes else []
        message_data = record.get("message") if isinstance(record.get("message"), dict) else {}
        raw_severity = (
            message_data.get("severity")
            if vendor == "netapp"
            else record.get("severity") or record.get("event_severity")
        )
        raw_time = (
            record.get("time")
            or record.get("timestamp")
            or record.get("start_time")
            or record.get("last_event")
            or record.get("time_noticed")
        )
        raw_external_id = (
            record.get("index")
            if vendor == "netapp"
            else record.get("id") or record.get("eventgroup_instance_id")
        )
        if raw_external_id in (None, "") or raw_time in (None, "") or raw_severity in (None, ""):
            logger.warning(
                "Skipping incomplete %s event (id=%r, time=%r, severity=%r)",
                vendor,
                raw_external_id,
                raw_time,
                raw_severity,
            )
            continue

        external_id, event_code, object_type, object_id = _event_identity(vendor, record)
        occurred_at = _datetime(raw_time)
        message = str(
            record.get("log_message")
            or record.get("message_text")
            or record.get("message")
            or (cause[1] if len(cause) > 1 else None)
            or event_code
        )
        rows.append(
            {
                "storage_cluster_id": storage_cluster_id,
                "source": vendor,
                "external_event_id": external_id,
                "fingerprint": f"{vendor}:{event_code}:{object_type}:{object_id}",
                "severity": normalize_severity(raw_severity),
                "alert_level": str(raw_severity or "info").lower(),
                "alert_type": "vendor_event",
                "description": message,
                "threshold": 0,
                "avg_use_ratio": 0,
                "related_id": None,
                "related_type": object_type,
                "related_info": {
                    "event_code": event_code,
                    "object_id": object_id,
                    "raw": record,
                },
                "updated_at": occurred_at,
            }
        )
    return rows


def run_isolated(
    cluster_ids,
    collect: Callable[[int], object],
    task_logger=logger,
    *,
    telemetry_context: dict | None = None,
    component: str | None = None,
    session_factory=SessionLocal,
) -> dict:
    succeeded = []
    failed = []
    for cluster_id in cluster_ids:
        run = None
        if telemetry_context is not None and component is not None:
            run = telemetryObservabilityService.safe_start_collection_run(
                session_factory,
                task_logger,
                task_id=telemetry_context["task_id"],
                attempt=telemetry_context["attempt"],
                scope_type="cluster",
                scope_key=str(cluster_id),
                storage_cluster_id=cluster_id,
                component=component,
                trace_id=telemetry_context["trace_id"],
            )
        try:
            records_written = collect(cluster_id)
            succeeded.append(cluster_id)
            if run is not None:
                telemetryObservabilityService.safe_complete_collection_run(
                    session_factory,
                    task_logger,
                    run.id,
                    outcome="success",
                    data_state=telemetryObservabilityService.successful_data_state(records_written),
                    records_written=records_written,
                )
        except Exception as exc:
            if telemetryObservabilityService.is_explicitly_unsupported(exc):
                succeeded.append(cluster_id)
                if run is not None:
                    telemetryObservabilityService.safe_complete_collection_run(
                        session_factory,
                        task_logger,
                        run.id,
                        outcome="success",
                        data_state="unsupported",
                        records_written=0,
                    )
                task_logger.info(
                    "Storage health collection is unsupported for cluster %s",
                    cluster_id,
                )
                continue
            failed.append(cluster_id)
            error_code = telemetryObservabilityService.classify_error_code(
                exc,
                phase="vendor",
            )
            if run is not None:
                telemetryObservabilityService.safe_complete_collection_run(
                    session_factory,
                    task_logger,
                    run.id,
                    outcome="failed",
                    error_code=error_code,
                )
            task_logger.error(
                "Storage health collection failed for cluster %s: error_code=%s",
                cluster_id,
                error_code,
            )
    return {
        "succeeded_clusters": tuple(succeeded),
        "failed_clusters": tuple(failed),
    }


def _active_cluster_ids() -> tuple[int, ...]:
    with SessionLocal() as db:
        return tuple(
            db.execute(
                select(StorageCluster.id)
                .where(StorageCluster.is_active.is_(True))
                .order_by(StorageCluster.id)
            ).scalars()
        )


def _persist_vendor_events(db, rows: list[dict], since: datetime) -> int:
    rows = [row for row in rows if row["updated_at"] >= since]
    if not rows:
        return 0
    deduplicated = {}
    for row in rows:
        deduplicated.setdefault(row["external_event_id"], row)
    rows = list(deduplicated.values())
    cluster_id = rows[0]["storage_cluster_id"]
    source = rows[0]["source"]
    ids = {row["external_event_id"] for row in rows}
    existing = set(
        db.execute(
            select(StorageAlerts.external_event_id).where(
                StorageAlerts.storage_cluster_id == cluster_id,
                StorageAlerts.source == source,
                StorageAlerts.external_event_id.in_(ids),
            )
        ).scalars()
    )
    new_rows = [row for row in rows if row["external_event_id"] not in existing]
    db.add_all(StorageAlerts(**row) for row in new_rows)
    return len(new_rows)


def _collect_events(storage_cluster_id: int) -> int:
    monitor = None
    with SessionLocal() as db:
        try:
            latest = db.execute(
                select(func.max(StorageAlerts.updated_at)).where(
                    StorageAlerts.storage_cluster_id == storage_cluster_id,
                    StorageAlerts.source != "diskpulse",
                )
            ).scalar_one_or_none()
            if latest is not None:
                latest = _datetime(latest)
            now = _datetime(datetime.now())
            since = event_window_start(latest, now)
            monitor = StoragePulseMonitor(db, logger, storage_cluster_id)
            monitor.setup()
            if monitor.storage_type == "netapp":
                records = monitor.client.get_ems_events(_utc_z(since))
            else:
                records = [
                    *monitor.client.get_event_group_occurrences(),
                    *monitor.client.get_event_lists(),
                ]
            inserted = _persist_vendor_events(
                db,
                normalize_vendor_events(storage_cluster_id, monitor.storage_type, records),
                since,
            )
            db.commit()
            return inserted
        except Exception:
            db.rollback()
            raise
        finally:
            if monitor is not None:
                monitor.cleanup()


def _number(value):
    if isinstance(value, dict):
        value = value.get("total")
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _microseconds_to_milliseconds(value):
    value = _number(value)
    return None if value is None else value / 1000


def _isilon_latency_milliseconds(value, unit):
    value = _number(value)
    if value is None or unit is None:
        return None
    normalized = str(unit).strip().lower()
    if normalized in {"microseconds", "microsecond", "us", "usec", "μs", "µs"}:
        return value / 1000
    if normalized in {"milliseconds", "millisecond", "ms"}:
        return value
    if normalized in {"seconds", "second", "s", "sec"}:
        return value * 1000
    return None


def _netapp_performance_rows(
    cluster_id: int,
    records: list[dict],
    now: datetime,
    volume_identities: dict[str, str] | None = None,
) -> list[dict]:
    rows = []
    for record in records:
        vendor_object_id = str(record.get("uuid") or record.get("name") or "")
        if volume_identities is not None and vendor_object_id not in volume_identities:
            continue
        metrics = record.get("metric") or {}
        latency_total = _microseconds_to_milliseconds(metrics.get("latency"))
        if latency_total is None:
            continue
        latency = metrics.get("latency") if isinstance(metrics.get("latency"), dict) else {}
        rows.append(
            {
                "storage_cluster_id": str(cluster_id),
                "vendor": "netapp",
                "object_type": "volume",
                "object_id": (
                    volume_identities[vendor_object_id]
                    if volume_identities is not None
                    else vendor_object_id
                ),
                "object_name": str(record.get("name") or record.get("uuid")),
                "latency_read": _microseconds_to_milliseconds(latency.get("read")),
                "latency_write": _microseconds_to_milliseconds(latency.get("write")),
                "latency_total": latency_total,
                "iops_total": _number(metrics.get("iops")),
                "throughput_total": _number(metrics.get("throughput")),
                "collected_at": _datetime(metrics.get("timestamp"), now),
            }
        )
    return rows


def _isilon_performance_rows(
    cluster_id: int,
    records: list[dict],
    now: datetime,
    volume_paths: set[str] | None = None,
    volume_identities: dict[str, str] | None = None,
) -> list[dict]:
    rows = []
    for record in records:
        key = str(record.get("key") or "").lower()
        if "latency" not in key:
            continue
        workload = record.get("workload")
        workload_key = str(workload) if workload not in (None, "") else None
        if (
            workload not in (None, "")
            and volume_paths is not None
            and workload_key not in volume_paths
        ):
            continue
        if volume_identities is not None and (
            workload_key is None or workload_key not in volume_identities
        ):
            continue
        object_type = "volume" if workload not in (None, "") else "node"
        object_id = (
            volume_identities[workload_key]
            if volume_identities is not None
            else str(
                workload
                or record.get("devid")
                or record.get("node")
                or record.get("name")
                or key
            )
        )
        value = _isilon_latency_milliseconds(record.get("value"), record.get("unit"))
        if value is None:
            continue
        rows.append(
            {
                "storage_cluster_id": str(cluster_id),
                "vendor": "isilon",
                "object_type": object_type,
                "object_id": object_id,
                "object_name": str(record.get("name") or workload_key or object_id),
                "latency_read": _isilon_latency_milliseconds(
                    record.get("latency_read"), record.get("unit")
                ),
                "latency_write": _isilon_latency_milliseconds(
                    record.get("latency_write"), record.get("unit")
                ),
                "latency_total": value,
                "iops_total": _number(record.get("iops_total")),
                "throughput_total": _number(record.get("throughput_total")),
                "collected_at": _datetime(record.get("timestamp") or record.get("time"), now),
            }
        )
    workloads = [row for row in rows if row["object_type"] == "volume"]
    return workloads or rows


def _write_performance_rows(rows: list[dict]) -> int:
    if not rows:
        return 0
    statement = text(
        f"INSERT BATCH {len(rows)} INTO storage_performance_metrics "
        "(storage_cluster_id, vendor, object_type, object_id, object_name, "
        "latency_read, latency_write, latency_total, iops_total, throughput_total, collected_at) "
        "VALUES (:storage_cluster_id, :vendor, :object_type, :object_id, :object_name, "
        ":latency_read, :latency_write, :latency_total, :iops_total, :throughput_total, :collected_at)"
    )
    try:
        with QuestDBSession() as connection:
            transaction = connection.begin()
            connection.execute(statement, rows)
            transaction.commit()
    except Exception as error:
        error.telemetry_phase = "questdb"
        raise
    return len(rows)


def _collect_performance(storage_cluster_id: int) -> int:
    monitor = None
    with SessionLocal() as db:
        try:
            monitor = StoragePulseMonitor(db, logger, storage_cluster_id)
            monitor.setup()
            now = datetime.now()
            volume_identities = {
                str(name): str(performance_object_id)
                for name, performance_object_id in db.execute(
                    select(Volume.name, Volume.performance_object_id).where(
                        Volume.storage_cluster_id == storage_cluster_id,
                        Volume.performance_object_id.is_not(None),
                    )
                ).all()
                if name and performance_object_id
            }
            if monitor.storage_type == "netapp":
                identities_by_device_id = {
                    performance_object_id: performance_object_id
                    for performance_object_id in volume_identities.values()
                }
                rows = _netapp_performance_rows(
                    storage_cluster_id,
                    monitor.client.get_volume_metrics(),
                    now,
                    volume_identities=identities_by_device_id,
                )
            else:
                rows = _isilon_performance_rows(
                    storage_cluster_id,
                    monitor.client.get_performance_statistics(),
                    now,
                    volume_identities=volume_identities,
                )
            return _write_performance_rows(rows)
        finally:
            if monitor is not None:
                monitor.cleanup()


@diskpulse_app.task(bind=True, soft_time_limit=50, time_limit=60, expires=60)
def storage_events_schedule_fetching_task(self):
    telemetry_context = telemetryObservabilityService.task_execution_context(self)
    logger.info("Storage vendor event collection started: trace_id=%s", telemetry_context["trace_id"])
    with redis_lock("storage_events_schedule_fetching_task_lock", expires=60) as have_lock:
        if not have_lock:
            telemetryObservabilityService.safe_record_scheduler_skip(
                SessionLocal,
                logger,
                component="vendor_events",
                **telemetry_context,
            )
            return {"succeeded_clusters": (), "failed_clusters": ()}
        result = run_isolated(
            _active_cluster_ids(),
            _collect_events,
            telemetry_context=telemetry_context,
            component="vendor_events",
        )
        _enqueue_derived_analytics(
            component="vendor_events",
            succeeded_clusters=result["succeeded_clusters"],
        )
        return result


@diskpulse_app.task(bind=True, soft_time_limit=240, time_limit=300, expires=300)
def storage_performance_schedule_fetching_task(self):
    telemetry_context = telemetryObservabilityService.task_execution_context(self)
    logger.info("Storage performance collection started: trace_id=%s", telemetry_context["trace_id"])
    with redis_lock("storage_performance_schedule_fetching_task_lock", expires=300) as have_lock:
        if not have_lock:
            telemetryObservabilityService.safe_record_scheduler_skip(
                SessionLocal,
                logger,
                component="performance",
                **telemetry_context,
            )
            return {"succeeded_clusters": (), "failed_clusters": ()}
        result = run_isolated(
            _active_cluster_ids(),
            _collect_performance,
            telemetry_context=telemetry_context,
            component="performance",
        )
        _enqueue_derived_analytics(
            component="performance",
            succeeded_clusters=result["succeeded_clusters"],
        )
        return result
