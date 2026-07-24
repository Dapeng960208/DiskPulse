# -*- coding: utf-8 -*-
"""Asynchronous production of derived storage-health analytics.

All functions in this module consume already-persisted PostgreSQL/QuestDB
facts.  They never write to a device and failures are isolated from collection
tasks that enqueue them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time
from typing import Iterable
from zoneinfo import ZoneInfo

import numpy as np
from celery.utils.log import get_task_logger
from sqlalchemy import select, text

from appConfig import base_config
from celery_worker import diskpulse_app
from celery_tasks.tasks.redis_lock import redis_lock
from crud import forecastIncidentCrud, incidentAiAgentCrud, telemetryCollectionRunCrud
from database import SessionLocal
from dependencies import QuestDBSession
from models import (
    AnomalyObservation,
    CapacityForecast,
    AIConfig,
    Group,
    Project,
    StorageAlerts,
    StorageCluster,
    StorageUsage,
    TelemetryQualitySnapshot,
    Volume,
    Qtree,
)
from services import (
    capacityPredictionGovernanceService,
    forecastIncidentService,
    incidentNotificationService,
)
from crud import capacityPredictionCrud, vendorEventDefinitionCrud
from services.forecastIncidentService import AssetRef, TelemetryEnvelope
from utils.datetime_utils import from_questdb_utc, utc_now


logger = get_task_logger(__name__)
QUALITY_PERIOD = timedelta(hours=24)
COMPONENT_INTERVAL_SECONDS = {"capacity": 60, "vendor_events": 60, "performance": 300}


@dataclass(frozen=True)
class CapacityTarget:
    asset_ref: AssetRef
    hard_limit: float
    table_name: str
    key_column: str


_CAPACITY_TABLES = {
    "storage_cluster": ("storage_cluster_storage_usages", "storage_cluster_id"),
    "project": ("project_storage_usages", "project_id"),
    "volume": ("volume_storage_usages", "volume_id"),
    "qtree": ("qtree_storage_usages", "qtree_id"),
    "group": ("group_storage_usages", "group_id"),
    "storage_usage": ("storage_usages", "storage_usage_id"),
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _vendor_event_utc(value: datetime) -> datetime:
    """StorageAlerts timestamps are persisted as Asia/Shanghai wall time when naive."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    return value.astimezone(timezone.utc)


def _utc_day(value: datetime) -> datetime:
    value = _utc(value)
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _five_minute_slot(value: datetime) -> datetime:
    value = _utc(value)
    return value.replace(minute=value.minute - value.minute % 5, second=0, microsecond=0)


def _normalise_quest_time(value) -> datetime | None:
    try:
        return from_questdb_utc(value)
    except (TypeError, ValueError):
        return None


def _high_confidence_enabled() -> bool:
    analytics = base_config.get("incident_analytics", {}) or {}
    return bool(analytics.get("replay_gate_verified", False))


def _notifications_after_commit(events: Iterable[tuple[int, str]]) -> None:
    for incident_id, event in events:
        try:
            deliver_incident_notification_task.delay(incident_id, event)
        except Exception:
            logger.warning("Unable to enqueue derived Incident notification: incident=%s", incident_id)


def _drain_incident_ai_review_ids(db) -> set[int]:
    """Return queued review ids without requiring test/session adapters to expose ``info``."""
    info = getattr(db, "info", None)
    if not isinstance(info, dict):
        return set()
    return set(info.pop("incident_ai_review_ids", set()))


def _agent_reviews_after_commit(db, incident_ids: Iterable[int]) -> None:
    from celery_tasks.tasks.incident_ai_agent import review_incident_ai_task

    source_ids = sorted({int(item) for item in incident_ids})
    candidates = incidentAiAgentCrud.list_lifecycle_review_candidates(
        db,
        incident_ids=source_ids,
        freshest_after=utc_now() - timedelta(minutes=60),
    )
    logger.info(
        "Incident AI lifecycle review selection: received=%s selected=%s reason=critical_fresh_only",
        len(source_ids),
        len(candidates),
    )
    for incident in candidates:
        try:
            task = review_incident_ai_task.delay(incident.id, "lifecycle")
            logger.info(
                "Incident AI review enqueued: incident=%s trigger=lifecycle task_id=%s",
                incident.id,
                task.id,
            )
        except Exception:
            logger.exception("Unable to enqueue Incident AI review: incident=%s trigger=lifecycle", incident.id)


def _record_correlation(
    db,
    *,
    envelope: TelemetryEnvelope,
    category: str,
    notifications: list[tuple[int, str]],
) -> None:
    if not forecastIncidentService.should_admit_incident(
        envelope,
        category=category,
        now=envelope.collected_at,
    ):
        return
    result = forecastIncidentService.correlate_incident(db, envelope, category=category)
    if result.incident is None:
        return
    forecastIncidentService.persist_incident_diagnosis(
        db,
        incident_id=result.incident.id,
        high_confidence_enabled=_high_confidence_enabled(),
    )
    db.info.setdefault("incident_ai_review_ids", set()).add(result.incident.id)
    if incidentNotificationService.should_send_incident_notification(
        created=result.created,
        reopened=result.reopened,
        severity_escalated=result.severity_escalated,
    ):
        event = "created" if result.created else "reopened" if result.reopened else "severity_escalated"
        notifications.append((result.incident.id, event))


def _cluster_asset(cluster: StorageCluster, *, project_id: int | None = None) -> AssetRef:
    return AssetRef(
        asset_type="storage_cluster",
        asset_id=str(cluster.id),
        storage_cluster_id=cluster.id,
        project_id=project_id,
        vendor=cluster.storage_type,
        display_name=cluster.name,
    )


def _project_asset(project: Project) -> AssetRef:
    return AssetRef(
        asset_type="project",
        asset_id=str(project.id),
        storage_cluster_id=None,
        project_id=project.id,
        vendor="mixed",
        display_name=project.name,
    )


def _capacity_targets(db) -> list[CapacityTarget]:
    clusters = {item.id: item for item in db.execute(select(StorageCluster)).scalars()}
    targets: list[CapacityTarget] = []
    for cluster in clusters.values():
        if cluster.limit and cluster.limit > 0:
            table_name, key_column = _CAPACITY_TABLES["storage_cluster"]
            targets.append(CapacityTarget(_cluster_asset(cluster), float(cluster.limit), table_name, key_column))
    for project in db.execute(select(Project)).scalars():
        if project.limit and project.limit > 0:
            table_name, key_column = _CAPACITY_TABLES["project"]
            targets.append(CapacityTarget(_project_asset(project), float(project.limit), table_name, key_column))
    for volume in db.execute(select(Volume)).scalars():
        cluster = clusters.get(volume.storage_cluster_id)
        if cluster is None or not volume.limit or volume.limit <= 0:
            continue
        table_name, key_column = _CAPACITY_TABLES["volume"]
        targets.append(
            CapacityTarget(
                AssetRef(
                    asset_type="volume",
                    asset_id=str(volume.id),
                    storage_cluster_id=cluster.id,
                    vendor=cluster.storage_type,
                    display_name=volume.name or str(volume.id),
                ),
                float(volume.limit),
                table_name,
                key_column,
            )
        )
    for qtree in db.execute(select(Qtree)).scalars():
        cluster = clusters.get(qtree.storage_cluster_id)
        if cluster is None or not qtree.limit or qtree.limit <= 0:
            continue
        table_name, key_column = _CAPACITY_TABLES["qtree"]
        targets.append(
            CapacityTarget(
                AssetRef(
                    asset_type="qtree",
                    asset_id=str(qtree.id),
                    storage_cluster_id=cluster.id,
                    vendor=cluster.storage_type,
                    display_name=qtree.name or str(qtree.id),
                ),
                float(qtree.limit),
                table_name,
                key_column,
            )
        )
    groups = {item.id: item for item in db.execute(select(Group)).scalars()}
    for group in groups.values():
        cluster = clusters.get(group.storage_cluster_id)
        if cluster is None or not group.limit or group.limit <= 0:
            continue
        table_name, key_column = _CAPACITY_TABLES["group"]
        targets.append(
            CapacityTarget(
                AssetRef(
                    asset_type="group",
                    asset_id=str(group.id),
                    storage_cluster_id=cluster.id,
                    project_id=group.project_id,
                    vendor=cluster.storage_type,
                    display_name=group.name or str(group.id),
                ),
                float(group.limit),
                table_name,
                key_column,
            )
        )
    for usage in db.execute(select(StorageUsage)).scalars():
        group = groups.get(usage.group_id)
        cluster = clusters.get(usage.storage_cluster_id)
        if cluster is None or not usage.limit or usage.limit <= 0:
            continue
        table_name, key_column = _CAPACITY_TABLES["storage_usage"]
        targets.append(
            CapacityTarget(
                AssetRef(
                    asset_type="storage_usage",
                    asset_id=str(usage.id),
                    storage_cluster_id=cluster.id,
                    project_id=group.project_id if group is not None else None,
                    vendor=cluster.storage_type,
                    display_name=usage.linux_path or str(usage.id),
                ),
                float(usage.limit),
                table_name,
                key_column,
            )
        )
    return targets


def _quest_capacity_points(target: CapacityTarget, *, cutoff: datetime) -> list[tuple[datetime, float]]:
    # Table and column names come from the immutable registry above; only the ID is bound.
    quest_cutoff = _utc(cutoff).isoformat().replace("+00:00", "Z")
    statement = text(
        f"SELECT updated_at, used FROM {target.table_name} "
        f"WHERE {target.key_column} = :asset_id AND updated_at >= :cutoff "
        "ORDER BY updated_at ASC"
    )
    with QuestDBSession() as connection:
        rows = connection.execute(
            statement,
            {"asset_id": target.asset_ref.asset_id, "cutoff": quest_cutoff},
        ).mappings().all()
    points: list[tuple[datetime, float]] = []
    for row in rows:
        observed_at = _normalise_quest_time(row.get("updated_at"))
        try:
            used = float(row.get("used"))
        except (TypeError, ValueError):
            continue
        if observed_at is not None:
            points.append((observed_at, used))
    return points


def _forecast_curve_json(result) -> list[dict]:
    return [point.model_dump(mode="json") for point in result.curve]


def _capacity_forecast_for_target(db, target: CapacityTarget, *, now: datetime) -> CapacityForecast:
    points = _quest_capacity_points(
        target,
        cutoff=_utc_day(now) - timedelta(
            days=forecastIncidentService.FORECAST_TRAINING_DAYS + forecastIncidentService.FORECAST_DAYS - 1
        ),
    )
    result = forecastIncidentService.build_capacity_forecast(
        target.asset_ref,
        points=points,
        hard_limit=target.hard_limit,
        now=now,
    )
    training_end = _utc_day(now)
    existing = forecastIncidentCrud.get_capacity_forecast(
        db,
        asset_type=target.asset_ref.asset_type,
        asset_id=target.asset_ref.asset_id,
        training_end=training_end,
        algorithm_version=result.algorithm_version,
    )
    if existing is not None:
        return existing
    return forecastIncidentCrud.add_capacity_forecast(
        db,
        CapacityForecast(
            **target.asset_ref.model_dump(),
            training_start=training_end - timedelta(days=forecastIncidentService.FORECAST_TRAINING_DAYS - 1),
            training_end=training_end,
            hard_limit=target.hard_limit,
            curve=_forecast_curve_json(result),
            exhaustion_dates=result.exhaustion_dates.model_dump(mode="json"),
            algorithm_version=result.algorithm_version,
            input_quality={
                "status": result.status,
                "coverage_ratio": result.coverage_ratio,
                "data_gaps": result.data_gaps,
                "sample_count": len({observed_at.date() for observed_at, _used in points}),
                "latest_observed_at": (
                    max((observed_at for observed_at, _used in points), default=None).isoformat()
                    if points else None
                ),
                "forecast_fresh_at": training_end.isoformat(),
            },
            backtest_mape=forecastIncidentService.capacity_forecast_backtest_mape(
                target.asset_ref,
                points=points,
                hard_limit=target.hard_limit,
            ),
        ),
    )


def _persist_active_candidate_prediction(db, *, target: CapacityTarget, baseline: CapacityForecast, now: datetime) -> None:
    candidate = capacityPredictionCrud.active_candidate(db)
    if candidate is None:
        return
    model = db.get(AIConfig, candidate.ai_model_id)
    if model is None or model.enabled is not True:
        return
    points = _quest_capacity_points(
        target,
        cutoff=_utc_day(now) - timedelta(days=forecastIncidentService.FORECAST_TRAINING_DAYS - 1),
    )
    plans = [
        {"effective_at": plan.effective_at, "capacity_delta": plan.capacity_delta}
        for plan in capacityPredictionCrud.list_plans(
            db,
            asset_type=target.asset_ref.asset_type,
            asset_id=target.asset_ref.asset_id,
        )
    ]
    result = capacityPredictionGovernanceService.generate_candidate_curve_with_fallback(
        model=model,
        asset_type=target.asset_ref.asset_type,
        points=points,
        hard_limit=target.hard_limit,
        approved_plans=plans,
        quality_summary=baseline.input_quality,
        forecast_start=baseline.training_end,
        baseline_curve=baseline.curve,
    )
    capacityPredictionGovernanceService.persist_candidate_prediction(
        db,
        candidate_id=candidate.id,
        asset_type=target.asset_ref.asset_type,
        asset_id=int(target.asset_ref.asset_id),
        project_id=target.asset_ref.project_id,
        forecast_start=baseline.training_end,
        baseline_curve=baseline.curve,
        result=result,
    )


def _record_rolling_candidate_evaluations(db, *, now: datetime) -> None:
    """Persist only aggregate, resource-identity-free evidence for inactive candidates."""
    targets = [
        target
        for target in _capacity_targets(db)
        if target.asset_ref.asset_type in {"storage_cluster", "project", "group", "storage_usage"}
    ]
    history_cutoff = _utc_day(now) - timedelta(
        days=forecastIncidentService.FORECAST_TRAINING_DAYS + forecastIncidentService.FORECAST_DAYS * 3 - 1
    )
    for candidate in capacityPredictionCrud.list_candidates(db):
        if candidate.enabled:
            continue
        model = db.get(AIConfig, candidate.ai_model_id)
        if model is None or model.enabled is not True:
            continue
        by_window: dict[tuple[datetime, datetime], list[dict]] = {}
        for target in targets:
            plans = [
                {"effective_at": plan.effective_at, "capacity_delta": plan.capacity_delta}
                for plan in capacityPredictionCrud.list_plans(
                    db,
                    asset_type=target.asset_ref.asset_type,
                    asset_id=target.asset_ref.asset_id,
                )
            ]
            for evaluation in capacityPredictionGovernanceService.rolling_candidate_evaluations(
                model=model,
                asset_ref=target.asset_ref,
                points=_quest_capacity_points(target, cutoff=history_cutoff),
                hard_limit=target.hard_limit,
                approved_plans=plans,
            ):
                key = (evaluation["window_start"], evaluation["window_end"])
                by_window.setdefault(key, []).append(evaluation)
        for (window_start, window_end), rows in by_window.items():
            if capacityPredictionCrud.has_candidate_evaluation(
                db,
                candidate_id=candidate.id,
                window_start=window_start,
                window_end=window_end,
            ):
                continue
            capacityPredictionGovernanceService.record_capacity_prediction_evaluation(
                db,
                candidate_id=candidate.id,
                baseline_mape=round(sum(row["baseline_mape"] for row in rows) / len(rows), 4),
                candidate_mape=round(sum(row["candidate_mape"] for row in rows) / len(rows), 4),
                risk_coverage_ok=all(row["risk_coverage_ok"] for row in rows),
                window_start=window_start,
                window_end=window_end,
            )


def run_capacity_forecasts(*, now: datetime | None = None) -> int:
    now = _utc(now or utc_now())
    notifications: list[tuple[int, str]] = []
    committed = False
    with SessionLocal() as db:
        try:
            persisted = []
            for target in _capacity_targets(db):
                forecast = _capacity_forecast_for_target(db, target, now=now)
                persisted.append(forecast)
                if target.asset_ref.asset_type in {"storage_cluster", "project", "group", "storage_usage"}:
                    _persist_active_candidate_prediction(db, target=target, baseline=forecast, now=now)
                exhaustion_p90 = (forecast.exhaustion_dates or {}).get("p90")
                if exhaustion_p90 is None:
                    continue
                _record_correlation(
                    db,
                    envelope=TelemetryEnvelope(
                        asset_ref=target.asset_ref,
                        source="capacity_forecast",
                        source_ref=f"capacity_forecast:{forecast.id}",
                        observed_at=now,
                        collected_at=now,
                        metric_or_event="forecast_exhaustion",
                        value={"severity": "warning", "exhaustion_p90": exhaustion_p90},
                        quality="good" if forecast.input_quality.get("status") == "ready" else "data_gap:capacity_history_insufficient",
                    ),
                    category="capacity_pressure",
                    notifications=notifications,
                )
            _record_rolling_candidate_evaluations(db, now=now)
            db.commit()
            committed = True
            return len(persisted)
        except Exception:
            db.rollback()
            raise
        finally:
            if committed:
                _notifications_after_commit(notifications)
                _agent_reviews_after_commit(db, _drain_incident_ai_review_ids(db))


def _raw_point_count(cluster_id: int, component: str, *, started_at: datetime) -> tuple[int, datetime | None]:
    if component == "vendor_events":
        with SessionLocal() as db:
            timestamps = db.execute(
                select(StorageAlerts.updated_at).where(
                    StorageAlerts.storage_cluster_id == cluster_id,
                    StorageAlerts.source != "diskpulse",
                    StorageAlerts.updated_at >= _utc(started_at),
                )
            ).scalars().all()
        latest = max((_utc(value) for value in timestamps), default=None)
        return len(timestamps), latest
    statement = text(
        "SELECT collected_at FROM storage_performance_metrics "
        "WHERE storage_cluster_id = :cluster_id AND collected_at >= :started_at"
        if component == "performance"
        else "SELECT updated_at FROM storage_cluster_storage_usages "
        "WHERE storage_cluster_id = :cluster_id AND updated_at >= :started_at"
    )
    timestamp_key = "collected_at" if component == "performance" else "updated_at"
    quest_started_at = _utc(started_at).isoformat().replace("+00:00", "Z")
    with QuestDBSession() as connection:
        rows = connection.execute(
            statement, {"cluster_id": str(cluster_id), "started_at": quest_started_at}
        ).mappings().all()
    points = [_normalise_quest_time(row.get(timestamp_key)) for row in rows]
    points = [point for point in points if point is not None]
    return len(points), max(points, default=None)


def _quality_asset(cluster: StorageCluster) -> AssetRef:
    return _cluster_asset(cluster)


def run_telemetry_quality_snapshots(*, now: datetime | None = None) -> int:
    now = _utc(now or utc_now())
    started_at = now - QUALITY_PERIOD
    notifications: list[tuple[int, str]] = []
    created = 0
    committed = False
    with SessionLocal() as db:
        try:
            clusters = db.execute(select(StorageCluster).where(StorageCluster.is_active.is_(True))).scalars().all()
            for cluster in clusters:
                asset = _quality_asset(cluster)
                for component, interval in COMPONENT_INTERVAL_SECONDS.items():
                    latest_success, successful_runs, failed_runs = telemetryCollectionRunCrud.collection_run_quality_stats(
                        db,
                        cluster_id=cluster.id,
                        component=component,
                        started_at=started_at,
                    )
                    raw_points, latest_point = _raw_point_count(cluster.id, component, started_at=started_at)
                    expected = max(1, int(QUALITY_PERIOD.total_seconds() / interval))
                    # Both sources contribute to coverage; raw data cannot turn a failed collection into success.
                    observed = min(successful_runs, raw_points) if component != "vendor_events" else successful_runs
                    quality = forecastIncidentService.evaluate_telemetry_quality(
                        component=component,
                        latest_success_at=latest_success,
                        latest_point_at=latest_point,
                        observed_points=observed,
                        expected_points=expected,
                        now=now,
                    )
                    calculated_at = _five_minute_slot(now)
                    snapshot = forecastIncidentCrud.get_telemetry_quality_snapshot(
                        db,
                        asset_type=asset.asset_type,
                        asset_id=asset.asset_id,
                        period=component,
                        algorithm_version=forecastIncidentService.ALGORITHM_VERSION,
                        calculated_at=calculated_at,
                    )
                    if snapshot is None:
                        snapshot = TelemetryQualitySnapshot(
                            **asset.model_dump(),
                            period=component,
                            latest_point_at=quality.latest_point_at,
                            coverage_ratio=quality.coverage_ratio,
                            data_gaps=quality.data_gaps,
                            quality_status=quality.status,
                            algorithm_version=forecastIncidentService.ALGORITHM_VERSION,
                            calculated_at=calculated_at,
                        )
                        forecastIncidentCrud.add_telemetry_quality_snapshot(db, snapshot)
                        created += 1
                    for gap in quality.data_gaps:
                        if gap not in {"telemetry_stale", "coverage_insufficient"}:
                            continue
                        _record_correlation(
                            db,
                            envelope=TelemetryEnvelope(
                                asset_ref=asset,
                                source="telemetry_quality",
                                source_ref=f"quality:{cluster.id}:{component}:{calculated_at.isoformat()}:{gap}",
                                observed_at=now,
                                collected_at=now,
                                metric_or_event=gap,
                                value={"severity": "warning", "component": component},
                                quality="good",
                            ),
                            category="telemetry_blindspot",
                            notifications=notifications,
                        )
                    for failed_run in failed_runs:
                        _record_correlation(
                            db,
                            envelope=TelemetryEnvelope(
                                asset_ref=asset,
                                source="telemetry_collection_run",
                                source_ref=f"collection_run:{failed_run.id}",
                                observed_at=_utc(failed_run.finished_at),
                                collected_at=now,
                                metric_or_event="collection_failure",
                                value={"severity": "warning", "component": component},
                                quality="good",
                            ),
                            category="telemetry_blindspot",
                            notifications=notifications,
                        )
            db.commit()
            committed = True
            return created
        except Exception:
            db.rollback()
            raise
        finally:
            if committed:
                _notifications_after_commit(notifications)
                _agent_reviews_after_commit(db, _drain_incident_ai_review_ids(db))


def _performance_asset(db, *, cluster: StorageCluster, object_type: str, object_id: str, object_name: str | None) -> tuple[AssetRef, str]:
    if object_type == "volume":
        name_candidates = {object_id}
        if object_name:
            name_candidates.add(object_name)
        volume_match = Volume.name.in_(sorted(name_candidates))
        # Review source: vendor UUID/name values were bound against integer
        # Volume.id. Resolution: only an ASCII-decimal identifier may add the
        # integer primary-key predicate; all other identifiers stay on name.
        if object_id.isascii() and object_id.isdecimal():
            volume_match = volume_match | (Volume.id == int(object_id))
        volume = db.execute(
            select(Volume).where(
                Volume.storage_cluster_id == cluster.id,
                volume_match,
            )
        ).scalar_one_or_none()
        if volume is not None:
            return (
                AssetRef(
                    asset_type="volume",
                    asset_id=str(volume.id),
                    storage_cluster_id=cluster.id,
                    vendor=cluster.storage_type,
                    display_name=volume.name or str(volume.id),
                ),
                "good",
            )
    return _cluster_asset(cluster), "data_gap:asset_mapping_missing"


def _performance_rows(*, cutoff: datetime) -> list[dict]:
    quest_cutoff = _utc(cutoff).isoformat().replace("+00:00", "Z")
    with QuestDBSession() as connection:
        return connection.execute(
            text(
                "SELECT storage_cluster_id, object_type, object_id, object_name, "
                "latency_total, iops_total, throughput_total, collected_at "
                "FROM storage_performance_metrics WHERE collected_at >= :cutoff "
                "ORDER BY collected_at ASC"
            ),
            {"cutoff": quest_cutoff},
        ).mappings().all()


def _p95(values: list[float]) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), 0.95))


def _safe_performance_ai_context(
    by_series: dict[tuple[str, str, str, str], list[tuple[datetime, float]]],
    *,
    series_key: tuple[str, str, str, str],
    observed_at: datetime,
    trigger_values: list[float],
) -> dict:
    """Produce metric aggregates only; never persist raw object identifiers or samples.

    Performance: Pre-computes 28-day window boundary once and caches history summaries
    to avoid redundant calculations across associated metrics.
    """
    start_time = time.perf_counter()
    cluster_id, object_type, object_id, metric = series_key

    # Pre-compute 28-day window boundary (used by all history_summary calls)
    window_start = observed_at - timedelta(days=28)

    # Cache for history summaries to avoid recalculating for the same points
    _history_cache: dict[tuple, dict] = {}

    def history_summary(points: list[tuple[datetime, float]]) -> dict:
        # Use tuple of points as cache key
        cache_key = tuple(points)
        if cache_key in _history_cache:
            return _history_cache[cache_key]

        # Filter to 28-day window using pre-computed boundary
        history = [
            value
            for point_at, value in points
            if point_at < observed_at and point_at >= window_start
        ]
        if not history:
            result = {"sample_count": 0, "coverage_ratio": 0.0}
        else:
            median = float(np.median(history))
            result = {
                "sample_count": len(history),
                "coverage_ratio": round(min(1.0, len(history) / (28 * 24 * 12)), 4),
                "median": round(median, 4),
                "p95": round(_p95(history), 4),
                "mad": round(float(np.median(np.abs(np.asarray(history) - median))), 4),
            }

        _history_cache[cache_key] = result
        return result

    current_points = sorted(by_series[series_key])

    # Pre-compute 2-hour window boundary
    trend_window_start = observed_at - timedelta(hours=2)
    trend_points = [
        {"minutes_before_trigger": int((observed_at - point_at).total_seconds() // 60), "p95": round(value, 4)}
        for point_at, value in current_points
        if trend_window_start <= point_at <= observed_at
    ]

    # Build associated metrics with cached history summaries
    associated_metrics = []
    resource_key = (cluster_id, object_type, object_id)
    for candidate_key, candidate_points in by_series.items():
        candidate_cluster, candidate_type, candidate_object, candidate_metric = candidate_key
        if (candidate_cluster, candidate_type, candidate_object) != resource_key:
            continue
        candidate_points = sorted(candidate_points)
        latest = next((value for point_at, value in reversed(candidate_points) if point_at <= observed_at), None)
        if latest is None:
            continue
        associated_metrics.append({
            "metric": candidate_metric,
            "latest_p95": round(latest, 4),
            "history_28d": history_summary(candidate_points),
        })

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    if elapsed_ms > 100:  # Log if computation takes >100ms
        logger.warning(
            "Performance AI context computation slow: %.1fms for %s/%s/%s",
            elapsed_ms, cluster_id, object_type, metric
        )

    return {
        "metric": metric,
        "trigger_three_bucket_p95": [round(value, 4) for value in trigger_values],
        "trend_2h_p95": trend_points[-24:],
        "history_28d": history_summary(current_points),
        "associated_metrics": sorted(associated_metrics, key=lambda item: item["metric"]),
    }


def _performance_findings(
    rows: list[dict],
    *,
    now: datetime,
    iops_absolute_floor: float = forecastIncidentService.DEFAULT_IOPS_ABSOLUTE_FLOOR,
    iops_baseline_ratio: float = forecastIncidentService.DEFAULT_IOPS_BASELINE_RATIO,
) -> list[dict]:
    buckets: dict[tuple[str, str, str, datetime], dict[str, list[float]]] = {}
    names: dict[tuple[str, str, str], str | None] = {}
    for row in rows:
        observed_at = _normalise_quest_time(row.get("collected_at"))
        if observed_at is None:
            continue
        identity = (str(row.get("storage_cluster_id")), str(row.get("object_type")), str(row.get("object_id")))
        names[identity] = row.get("object_name")
        bucket = buckets.setdefault((*identity, _five_minute_slot(observed_at)), {"latency": [], "iops": [], "throughput": []})
        for metric, field in (("latency", "latency_total"), ("iops", "iops_total"), ("throughput", "throughput_total")):
            try:
                value = float(row.get(field))
            except (TypeError, ValueError):
                continue
            bucket[metric].append(value)
    by_series: dict[tuple[str, str, str, str], list[tuple[datetime, float]]] = {}
    for (*identity, bucket_at), metrics in buckets.items():
        for metric, values in metrics.items():
            if values:
                by_series.setdefault((*identity, metric), []).append((bucket_at, _p95(values)))
    findings: list[dict] = []
    for series_key, values in by_series.items():
        cluster_id, object_type, object_id, metric = series_key
        identity = (cluster_id, object_type, object_id)
        values.sort(key=lambda item: item[0])
        scored: list[tuple[datetime, float, float, float, float, int]] = []
        for observed_at, value in values:
            historical = [
                item_value
                for item_at, item_value in values
                if item_at < observed_at
                and item_at.weekday() == observed_at.weekday()
                and item_at.hour == observed_at.hour
                and item_at >= observed_at - timedelta(days=28)
            ]
            if not historical:
                continue
            median = float(np.median(historical))
            mad = float(np.median(np.abs(np.asarray(historical) - median)))
            score = forecastIncidentService.robust_z_score(value=value, median=median, mad=mad)
            scored.append((observed_at, value, median, mad, score, len(historical)))
        if len(scored) < 3:
            continue
        last_three = scored[-3:]
        if any(
            right[0] - left[0] != timedelta(minutes=5)
            for left, right in zip(last_three, last_three[1:])
        ):
            continue
        if not forecastIncidentService.qualifies_performance_anomaly([item[4] for item in last_three]):
            continue
        observed_at, value, baseline, mad, score, seasonal_sample_count = last_three[-1]
        incident_eligible = metric == "latency" and forecastIncidentService.qualifies_latency_incident(
            scores=[item[4] for item in last_three],
            values=[item[1] for item in last_three],
            baselines=[item[2] for item in last_three],
            seasonal_sample_counts=[item[5] for item in last_three],
        )
        if metric == "iops" and all(item[3] == 0 for item in last_three):
            resource_history = [
                item_value
                for item_at, item_value in values
                if item_at < observed_at and item_at >= observed_at - timedelta(days=28)
            ]
            resource_baseline = (
                float(np.median(resource_history))
                if len(resource_history) >= forecastIncidentService.IOPS_BASELINE_MIN_SAMPLES
                else None
            )
            cluster_values = [
                item_value
                for (candidate_cluster_id, _candidate_type, _candidate_id, candidate_metric), candidate_values in by_series.items()
                if candidate_cluster_id == cluster_id and candidate_metric == "iops"
                for item_at, item_value in candidate_values
                if item_at < observed_at and item_at >= observed_at - timedelta(days=28)
            ]
            cluster_baseline = (
                float(np.median(cluster_values))
                if len(cluster_values) >= forecastIncidentService.IOPS_BASELINE_MIN_SAMPLES
                else None
            )
            if forecastIncidentService.should_suppress_zero_mad_iops(
                [item[1] for item in last_three],
                resource_baseline=resource_baseline,
                cluster_baseline=cluster_baseline,
                absolute_floor=iops_absolute_floor,
                baseline_ratio=iops_baseline_ratio,
            ):
                continue
        findings.append(
            {
                "cluster_id": int(cluster_id),
                "object_type": object_type,
                "object_id": object_id,
                "object_name": names.get(identity),
                "metric": metric,
                "observed_at": observed_at,
                "observed_value": value,
                "baseline": baseline,
                "mad": mad,
                "score": score,
                "seasonal_sample_count": seasonal_sample_count,
                "incident_eligible": incident_eligible,
                "window_start": last_three[0][0],
                "window_end": observed_at,
                "ai_performance_context": _safe_performance_ai_context(
                    by_series,
                    series_key=series_key,
                    observed_at=observed_at,
                    trigger_values=[item[1] for item in last_three],
                ),
            }
        )
    return findings


def run_performance_anomalies(*, now: datetime | None = None) -> int:
    now = _utc(now or utc_now())
    notifications: list[tuple[int, str]] = []
    committed = False
    with SessionLocal() as db:
        try:
            clusters = {item.id: item for item in db.execute(select(StorageCluster)).scalars()}
            ai_settings = incidentAiAgentCrud.get_settings(db)
            iops_absolute_floor = (
                float(ai_settings.iops_absolute_floor)
                if ai_settings is not None
                else forecastIncidentService.DEFAULT_IOPS_ABSOLUTE_FLOOR
            )
            iops_baseline_ratio = (
                float(ai_settings.iops_baseline_ratio)
                if ai_settings is not None
                else forecastIncidentService.DEFAULT_IOPS_BASELINE_RATIO
            )
            created = 0
            for finding in _performance_findings(
                _performance_rows(cutoff=now - timedelta(days=29)),
                now=now,
                iops_absolute_floor=iops_absolute_floor,
                iops_baseline_ratio=iops_baseline_ratio,
            ):
                cluster = clusters.get(finding["cluster_id"])
                if cluster is None:
                    continue
                asset, quality = _performance_asset(
                    db,
                    cluster=cluster,
                    object_type=finding["object_type"],
                    object_id=finding["object_id"],
                    object_name=finding["object_name"],
                )
                source_ref = (
                    f"performance:{cluster.id}:{finding['object_type']}:{finding['object_id']}:"
                    f"{finding['metric']}:{finding['observed_at'].isoformat()}"
                )
                observation = forecastIncidentCrud.get_anomaly_observation(
                    db,
                    source="questdb_performance",
                    source_ref=source_ref,
                    metric=finding["metric"],
                    algorithm_version=forecastIncidentService.ALGORITHM_VERSION,
                )
                if observation is not None:
                    continue
                observation = forecastIncidentCrud.add_anomaly_observation(
                    db,
                    AnomalyObservation(
                        **asset.model_dump(),
                        metric=finding["metric"],
                        observed_at=finding["observed_at"],
                        observed_value=finding["observed_value"],
                        seasonal_baseline=finding["baseline"],
                        mad=finding["mad"],
                        robust_z_score=finding["score"],
                        severity=(
                            "critical"
                            if finding["incident_eligible"] or abs(finding["score"]) >= 7
                            else "warning"
                        ),
                        evidence_window_start=finding["window_start"],
                        evidence_window_end=finding["window_end"],
                        source="questdb_performance",
                        source_ref=source_ref,
                        input_quality={
                            "asset_mapping": quality == "good",
                            "seasonal_sample_count": finding["seasonal_sample_count"],
                            "incident_eligible": finding["incident_eligible"],
                            "ai_performance_context": finding["ai_performance_context"],
                        },
                        algorithm_version=forecastIncidentService.ALGORITHM_VERSION,
                    ),
                )
                created += 1
                _record_correlation(
                    db,
                    envelope=TelemetryEnvelope(
                        asset_ref=asset,
                        source="anomaly_observation",
                        source_ref=f"anomaly:{observation.id}",
                        observed_at=finding["observed_at"],
                        collected_at=now,
                        metric_or_event="continuous_performance_anomaly",
                        value={
                            "severity": observation.severity,
                            "metric": finding["metric"],
                            "incident_eligible": finding["incident_eligible"],
                        },
                        quality=quality,
                    ),
                    category="performance_contention",
                    notifications=notifications,
                )
            db.commit()
            committed = True
            return created
        except Exception:
            db.rollback()
            raise
        finally:
            if committed:
                _notifications_after_commit(notifications)
                _agent_reviews_after_commit(db, _drain_incident_ai_review_ids(db))


def _vendor_event_asset(
    cluster: StorageCluster, event: StorageAlerts
) -> tuple[AssetRef, str]:
    related_info_value = getattr(event, "related_info", None)
    related_info = related_info_value if isinstance(related_info_value, dict) else {}
    object_id = related_info.get("object_id")
    related_type = str(getattr(event, "related_type", None) or "").lower()
    if object_id and str(object_id).lower() != "cluster" and related_type in {
        "node",
        "storage_node",
    }:
        raw = related_info.get("raw")
        raw = raw if isinstance(raw, dict) else {}
        node = raw.get("node") if isinstance(raw.get("node"), dict) else {}
        return (
            AssetRef(
                asset_type="storage_node",
                asset_id=str(object_id),
                storage_cluster_id=cluster.id,
                project_id=None,
                vendor=cluster.storage_type,
                display_name=str(node.get("name") or object_id),
            ),
            "good",
        )
    if object_id and str(object_id).lower() == "cluster":
        return _cluster_asset(cluster), "good"
    return _cluster_asset(cluster), "data_gap:asset_mapping_missing"


def _vendor_event_definition_key(
    cluster: StorageCluster,
    event: StorageAlerts,
) -> tuple[str, str] | None:
    storage_type = str(event.source or cluster.storage_type or "").strip().lower()
    related_info_value = getattr(event, "related_info", None)
    related_info = related_info_value if isinstance(related_info_value, dict) else {}
    event_code_value = related_info.get("event_code")
    event_code = (
        event_code_value.strip() if isinstance(event_code_value, str) else ""
    )
    if storage_type not in {"netapp", "isilon"} or not event_code:
        return None
    return storage_type, event_code


def _vendor_event_association_type(
    definition_map: dict,
    key: tuple[str, str] | None,
) -> str:
    definition = definition_map.get(key) if key is not None else None
    if (
        definition is None
        or not definition.is_active
        or definition.review_status != "reviewed"
    ):
        return "unknown"
    return str(definition.association_type)


def _diskpulse_alert_asset(db, event: StorageAlerts) -> tuple[AssetRef, str]:
    cluster = db.get(StorageCluster, event.storage_cluster_id) if event.storage_cluster_id is not None else None
    if cluster is None:
        raise LookupError("storage cluster was not found")
    if event.related_type == "StorageUsage" and event.related_id is not None:
        usage = db.get(StorageUsage, event.related_id)
        group = db.get(Group, usage.group_id) if usage is not None and usage.group_id is not None else None
        if usage is not None:
            return (
                AssetRef(
                    asset_type="storage_usage",
                    asset_id=str(usage.id),
                    storage_cluster_id=cluster.id,
                    project_id=group.project_id if group is not None else None,
                    vendor=cluster.storage_type,
                    display_name=usage.linux_path or str(usage.id),
                ),
                "good" if group is not None else "data_gap:asset_mapping_missing",
            )
    if event.related_type == "Group" and event.related_id is not None:
        group = db.get(Group, event.related_id)
        if group is not None:
            return (
                AssetRef(
                    asset_type="group",
                    asset_id=str(group.id),
                    storage_cluster_id=cluster.id,
                    project_id=group.project_id,
                    vendor=cluster.storage_type,
                    display_name=group.name or str(group.id),
                ),
                "good",
            )
    if event.related_type == "Project" and event.related_id is not None:
        return _cluster_asset(cluster, project_id=event.related_id), "good"
    return _cluster_asset(cluster), "data_gap:asset_mapping_missing"


def process_diskpulse_alert_evidence(*, alert_ids: Iterable[int]) -> int:
    notifications: list[tuple[int, str]] = []
    committed = False
    with SessionLocal() as db:
        try:
            events = db.execute(
                select(StorageAlerts).where(
                    StorageAlerts.id.in_(tuple(alert_ids)),
                    StorageAlerts.source == "diskpulse",
                    StorageAlerts.event_type.in_(("trigger", "escalation")),
                )
            ).scalars().all()
            handled = 0
            for event in events:
                try:
                    asset, quality = _diskpulse_alert_asset(db, event)
                except LookupError:
                    logger.warning("Ignoring raw alert with unavailable storage cluster: alert=%s", event.id)
                    continue
                envelope = TelemetryEnvelope(
                    asset_ref=asset,
                    source="diskpulse_alert",
                    source_ref=f"diskpulse:{event.id}",
                    observed_at=_vendor_event_utc(event.updated_at),
                    collected_at=utc_now(),
                    metric_or_event=(
                        "hard_limit_alert" if event.quota_basis == "hard" else "soft_limit_alert"
                    ),
                    value={"severity": event.severity},
                    quality=quality,
                )
                if not forecastIncidentService.should_admit_incident(
                    envelope,
                    category="capacity_pressure",
                    now=envelope.collected_at,
                ):
                    continue
                _record_correlation(
                    db,
                    envelope=envelope,
                    category="capacity_pressure",
                    notifications=notifications,
                )
                handled += 1
            db.commit()
            committed = True
            return handled
        except Exception:
            db.rollback()
            raise
        finally:
            if committed:
                _notifications_after_commit(notifications)
                _agent_reviews_after_commit(db, _drain_incident_ai_review_ids(db))


def process_vendor_event_evidence(*, storage_cluster_id: int, source: str | None = None) -> int:
    notifications: list[tuple[int, str]] = []
    committed = False
    with SessionLocal() as db:
        try:
            cluster = db.get(StorageCluster, storage_cluster_id)
            if cluster is None:
                return 0
            statement = select(StorageAlerts).where(
                StorageAlerts.storage_cluster_id == storage_cluster_id,
                StorageAlerts.source.in_(("netapp", "isilon")),
            )
            if source is not None:
                statement = statement.where(StorageAlerts.source == source)
            events = db.execute(statement.order_by(StorageAlerts.updated_at.desc()).limit(500)).scalars().all()
            source_refs_by_event = {
                event.id: (
                    f"storage_alert:{event.id}",
                    f"{event.source}:{event.external_event_id or event.id}",
                )
                for event in events
            }
            existing_source_refs = (
                forecastIncidentCrud.list_existing_incident_evidence_source_refs(
                    db,
                    source="vendor_event",
                    source_refs=(
                        source_ref
                        for refs in source_refs_by_event.values()
                        for source_ref in refs
                    ),
                )
            )
            definition_keys = {
                key
                for event in events
                if (key := _vendor_event_definition_key(cluster, event)) is not None
            }
            definition_map = vendorEventDefinitionCrud.get_definition_map(
                db,
                definition_keys,
            )
            handled = 0
            for event in events:
                current_ref, legacy_ref = source_refs_by_event[event.id]
                if current_ref in existing_source_refs or legacy_ref in existing_source_refs:
                    continue
                asset, quality = _vendor_event_asset(cluster, event)
                definition_key = _vendor_event_definition_key(cluster, event)
                association_type = _vendor_event_association_type(
                    definition_map,
                    definition_key,
                )
                envelope = TelemetryEnvelope(
                    asset_ref=asset,
                    source="vendor_event",
                    source_ref=current_ref,
                    observed_at=_vendor_event_utc(event.updated_at),
                    collected_at=utc_now(),
                    metric_or_event="severe_vendor_event" if event.severity == "critical" else "vendor_event",
                    value={
                        "severity": event.severity,
                        "association_type": association_type,
                    },
                    quality=quality,
                )
                if not forecastIncidentService.should_admit_incident(
                    envelope,
                    category="device_fault",
                    now=envelope.collected_at,
                ):
                    continue
                _record_correlation(
                    db,
                    envelope=envelope,
                    category="device_fault",
                    notifications=notifications,
                )
                handled += 1
            db.commit()
            committed = True
            return handled
        except Exception:
            db.rollback()
            raise
        finally:
            if committed:
                _notifications_after_commit(notifications)
                _agent_reviews_after_commit(db, _drain_incident_ai_review_ids(db))


@diskpulse_app.task(soft_time_limit=600, time_limit=660, expires=900)
def capacity_forecast_daily_task():
    with redis_lock("capacity_forecast_daily_task_lock", expires=900) as have_lock:
        if not have_lock:
            return 0
        try:
            return run_capacity_forecasts()
        except Exception:
            logger.exception("Capacity forecast task failed without affecting collection")
            return 0


@diskpulse_app.task(soft_time_limit=300, time_limit=360, expires=480)
def telemetry_quality_snapshot_task():
    with redis_lock("telemetry_quality_snapshot_task_lock", expires=480) as have_lock:
        if not have_lock:
            return 0
        try:
            return run_telemetry_quality_snapshots()
        except Exception:
            logger.exception("Telemetry quality task failed without affecting collection")
            return 0


@diskpulse_app.task(soft_time_limit=600, time_limit=660, expires=780)
def performance_anomaly_scan_task():
    with redis_lock("performance_anomaly_scan_task_lock", expires=780) as have_lock:
        if not have_lock:
            return 0
        try:
            return run_performance_anomalies()
        except Exception:
            logger.exception("Performance anomaly task failed without affecting collection")
            return 0


@diskpulse_app.task(soft_time_limit=300, time_limit=360, expires=480)
def vendor_event_evidence_task(storage_cluster_id: int, source: str | None = None):
    with redis_lock(f"vendor_event_evidence_task_lock:{storage_cluster_id}", expires=480) as have_lock:
        if not have_lock:
            return 0
        try:
            return process_vendor_event_evidence(storage_cluster_id=storage_cluster_id, source=source)
        except Exception:
            logger.exception("Vendor event correlation failed without affecting collection")
            return 0


@diskpulse_app.task(soft_time_limit=180, time_limit=240, expires=300)
def diskpulse_alert_evidence_task(alert_ids: list[int]):
    if not alert_ids:
        return 0
    try:
        return process_diskpulse_alert_evidence(alert_ids=alert_ids)
    except Exception:
        logger.exception("DiskPulse alert correlation failed without affecting alert delivery")
        return 0


@diskpulse_app.task(soft_time_limit=60, time_limit=90, expires=180)
def deliver_incident_notification_task(incident_id: int, event: str) -> list[str]:
    with SessionLocal() as db:
        incident = forecastIncidentCrud.get_incident(db, incident_id)
        if incident is None:
            return []
        try:
            return list(incidentNotificationService.notify_incident(db, incident, event=event))
        except Exception:
            logger.exception("Derived Incident notification failed: incident=%s", incident_id)
            return []
