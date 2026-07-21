# -*- coding: utf-8 -*-
from collections.abc import Iterable
from datetime import datetime, timedelta

from sqlalchemy import String, and_, cast, func, or_, select, text, tuple_
from sqlalchemy.orm import Session

from crud.configCrud import get_storage_config
from dependencies import QuestDBSession
from models import StorageAlerts
from utils.datetime_utils import to_system_local_naive


def _naive(value: datetime) -> datetime:
    return to_system_local_naive(value)


def get_capacity_points(
    db: Session,
    storage_cluster_id: int,
    start_time: datetime,
    end_time: datetime,
) -> list[dict]:
    if end_time - timedelta(days=30) > start_time:
        sample_by = "SAMPLE BY 1d"
    elif end_time - timedelta(days=7) > start_time:
        sample_by = "SAMPLE BY 1h"
    else:
        sample_by = "SAMPLE BY 1m"
    statement = text(
        "SELECT max(used) AS used, updated_at "
        "FROM storage_cluster_storage_usages "
        "WHERE storage_cluster_id = :storage_cluster_id "
        "AND updated_at BETWEEN :start_time AND :end_time "
        f"{sample_by}"
    )
    with QuestDBSession(config=get_storage_config(db=db)) as connection:
        rows = connection.execute(
            statement,
            {
                "storage_cluster_id": str(storage_cluster_id),
                "start_time": str(start_time),
                "end_time": str(end_time),
            },
        ).all()
    return [{"updated_at": row[1], "used": row[0]} for row in rows]


def get_capacity_boundaries(
    db: Session,
    storage_cluster_id: int,
    start_time: datetime,
    end_time: datetime,
) -> tuple[float | None, float | None]:
    statement = text(
        "SELECT first(used) AS start_used, last(used) AS end_used "
        "FROM storage_cluster_storage_usages "
        "WHERE storage_cluster_id = :storage_cluster_id "
        "AND updated_at BETWEEN :start_time AND :end_time"
    )
    with QuestDBSession(config=get_storage_config(db=db)) as connection:
        row = connection.execute(
            statement,
            {
                "storage_cluster_id": str(storage_cluster_id),
                "start_time": str(start_time),
                "end_time": str(end_time),
            },
        ).first()
    if row is None:
        return None, None
    return row[0], row[1]


def get_alert_severities(
    db: Session,
    storage_cluster_id: int,
    start_time: datetime,
    end_time: datetime,
) -> list[dict]:
    rows = db.execute(
        select(StorageAlerts.source, StorageAlerts.severity).where(
            StorageAlerts.storage_cluster_id == storage_cluster_id,
            StorageAlerts.source.in_(("netapp", "isilon")),
            StorageAlerts.updated_at.between(_naive(start_time), _naive(end_time)),
        )
    ).all()
    return [{"source": row.source, "severity": row.severity} for row in rows]


def get_system_event_rows(
    db: Session,
    storage_cluster_id: int,
    start_time: datetime,
    end_time: datetime,
    keyword: str | None = None,
    severity: str | None = None,
    fingerprint: str | None = None,
    include_identity: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[int, list[dict]]:
    filters = [
        StorageAlerts.storage_cluster_id == storage_cluster_id,
        StorageAlerts.source.in_(("netapp", "isilon")),
        StorageAlerts.updated_at.between(_naive(start_time), _naive(end_time)),
    ]
    if severity:
        filters.append(StorageAlerts.severity == severity)
    if fingerprint:
        filters.append(StorageAlerts.fingerprint == fingerprint)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        filters.append(
            or_(
                StorageAlerts.description.ilike(pattern),
                StorageAlerts.fingerprint.ilike(pattern),
                StorageAlerts.external_event_id.ilike(pattern),
                cast(StorageAlerts.related_info, String).ilike(pattern),
            )
        )

    total = db.scalar(
        select(func.count(StorageAlerts.id)).where(*filters)
    ) or 0
    rows = db.execute(
        select(
            StorageAlerts.id,
            StorageAlerts.source,
            StorageAlerts.external_event_id,
            StorageAlerts.fingerprint,
            StorageAlerts.severity,
            StorageAlerts.description,
            StorageAlerts.related_type,
            StorageAlerts.related_info,
            StorageAlerts.updated_at,
        )
        .where(*filters)
        .order_by(StorageAlerts.updated_at.desc(), StorageAlerts.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return int(total), [
        _system_event_row(row, include_identity=include_identity) for row in rows
    ]


def _system_event_row(row, *, include_identity: bool = True) -> dict:
    related_info = row.related_info if isinstance(row.related_info, dict) else {}
    object_id = str(related_info.get("object_id") or "cluster")
    raw = related_info.get("raw")
    raw = raw if isinstance(raw, dict) else {}
    node = raw.get("node") if isinstance(raw.get("node"), dict) else {}
    if row.source == "netapp":
        object_name = node.get("name") or object_id
    elif object_id == "cluster":
        object_name = "集群"
    else:
        object_name = f"节点 {object_id}"
    result = {
        "source": row.source,
        "severity": row.severity,
        "event_code": related_info.get("event_code"),
        "object_id": object_id,
        "object_name": object_name,
        "object_type": row.related_type or "node",
        "description": row.description,
        "occurred_at": row.updated_at,
    }
    if include_identity:
        result.update(
            {
                "id": row.id,
                "external_event_id": row.external_event_id,
                "fingerprint": row.fingerprint,
            }
        )
    return result


def get_system_event_by_id(
    db: Session, storage_cluster_id: int, event_id: int
) -> dict | None:
    row = db.execute(
        select(
            StorageAlerts.id,
            StorageAlerts.source,
            StorageAlerts.external_event_id,
            StorageAlerts.fingerprint,
            StorageAlerts.severity,
            StorageAlerts.description,
            StorageAlerts.related_type,
            StorageAlerts.related_info,
            StorageAlerts.updated_at,
        ).where(
            StorageAlerts.id == event_id,
            StorageAlerts.storage_cluster_id == storage_cluster_id,
            StorageAlerts.source.in_(("netapp", "isilon")),
        )
    ).one_or_none()
    return None if row is None else _system_event_row(row)


def get_system_events_by_ids(
    db: Session,
    storage_cluster_id: int,
    event_ids: Iterable[int],
) -> dict[int, dict]:
    normalized_ids = sorted({int(event_id) for event_id in event_ids})
    if not normalized_ids:
        return {}
    rows = db.execute(
        select(
            StorageAlerts.id,
            StorageAlerts.source,
            StorageAlerts.external_event_id,
            StorageAlerts.fingerprint,
            StorageAlerts.severity,
            StorageAlerts.description,
            StorageAlerts.related_type,
            StorageAlerts.related_info,
            StorageAlerts.updated_at,
        ).where(
            StorageAlerts.id.in_(normalized_ids),
            StorageAlerts.storage_cluster_id == storage_cluster_id,
            StorageAlerts.source.in_(("netapp", "isilon")),
        )
    ).all()
    return {int(row.id): _system_event_row(row) for row in rows}


def get_vendor_alerts_for_evidence_refs(
    db: Session,
    refs: Iterable[str],
    storage_cluster_id: int | None,
) -> dict[str, StorageAlerts]:
    direct_refs: dict[int, str] = {}
    legacy_refs: dict[tuple[str, str], str] = {}
    for value in refs:
        source_ref = str(value or "")
        if source_ref.startswith("storage_alert:"):
            try:
                alert_id = int(source_ref.split(":", 1)[1])
            except ValueError:
                continue
            direct_refs[alert_id] = source_ref
            continue
        source, separator, external_event_id = source_ref.partition(":")
        if separator and source in {"netapp", "isilon"} and external_event_id:
            legacy_refs[(source, external_event_id)] = source_ref

    reference_filters = []
    if direct_refs:
        reference_filters.append(StorageAlerts.id.in_(sorted(direct_refs)))
    if legacy_refs:
        reference_filters.append(
            tuple_(
                StorageAlerts.source,
                StorageAlerts.external_event_id,
            ).in_(sorted(legacy_refs))
        )
    if not reference_filters:
        return {}

    filters = [
        StorageAlerts.source.in_(("netapp", "isilon")),
        or_(*reference_filters),
    ]
    if storage_cluster_id is not None:
        filters.append(StorageAlerts.storage_cluster_id == storage_cluster_id)
    alerts = db.scalars(select(StorageAlerts).where(and_(*filters)))

    result: dict[str, StorageAlerts] = {}
    for alert in alerts:
        direct_ref = direct_refs.get(alert.id)
        if direct_ref is not None:
            result[direct_ref] = alert
        legacy_ref = legacy_refs.get((alert.source, alert.external_event_id))
        if legacy_ref is not None:
            result[legacy_ref] = alert
    return result


def get_vendor_alerts_for_cluster_evidence_refs(
    db: Session,
    references: Iterable[tuple[int | None, str]],
) -> dict[tuple[int, str], StorageAlerts]:
    direct_refs: dict[tuple[int, int], str] = {}
    legacy_refs: dict[tuple[int, str, str], str] = {}
    for cluster_id_value, reference_value in references:
        if cluster_id_value is None:
            continue
        cluster_id = int(cluster_id_value)
        source_ref = str(reference_value or "")
        if source_ref.startswith("storage_alert:"):
            try:
                alert_id = int(source_ref.split(":", 1)[1])
            except ValueError:
                continue
            direct_refs[(cluster_id, alert_id)] = source_ref
            continue
        source, separator, external_event_id = source_ref.partition(":")
        if separator and source in {"netapp", "isilon"} and external_event_id:
            legacy_refs[(cluster_id, source, external_event_id)] = source_ref

    reference_filters = []
    if direct_refs:
        reference_filters.append(
            tuple_(StorageAlerts.storage_cluster_id, StorageAlerts.id).in_(
                sorted(direct_refs)
            )
        )
    if legacy_refs:
        reference_filters.append(
            tuple_(
                StorageAlerts.storage_cluster_id,
                StorageAlerts.source,
                StorageAlerts.external_event_id,
            ).in_(sorted(legacy_refs))
        )
    if not reference_filters:
        return {}

    alerts = db.scalars(
        select(StorageAlerts).where(
            StorageAlerts.source.in_(("netapp", "isilon")),
            or_(*reference_filters),
        )
    )
    result: dict[tuple[int, str], StorageAlerts] = {}
    for alert in alerts:
        direct_ref = direct_refs.get((alert.storage_cluster_id, alert.id))
        if direct_ref is not None:
            result[(alert.storage_cluster_id, direct_ref)] = alert
        legacy_ref = legacy_refs.get(
            (
                alert.storage_cluster_id,
                alert.source,
                alert.external_event_id,
            )
        )
        if legacy_ref is not None:
            result[(alert.storage_cluster_id, legacy_ref)] = alert
    return result


def get_top_latency_rows(
    db: Session,
    storage_cluster_id: int,
    start_time: datetime,
    end_time: datetime,
    limit: int,
    object_type: str | None = None,
    object_ids: set[str] | None = None,
) -> list[dict]:
    object_filter = "AND object_type = :object_type" if object_type else ""
    identity_parameters = {
        f"object_id_{index}": object_id
        for index, object_id in enumerate(sorted(object_ids or ()))
    }
    identity_filter = (
        f"AND object_id IN ({', '.join(f':{name}' for name in identity_parameters)})"
        if identity_parameters
        else ""
    )
    statement = text(
        "SELECT object_id, object_name, object_type, "
        "approx_percentile(latency_total, 0.95) AS p95_latency, "
        "avg(latency_total) AS avg_latency, max(latency_total) AS max_latency, "
        "avg(latency_read) AS avg_read_latency, "
        "avg(latency_write) AS avg_write_latency, "
        "avg(iops_total) AS avg_iops, "
        "avg(throughput_total) AS avg_throughput, "
        "count() AS sample_count "
        "FROM storage_performance_metrics "
        "WHERE storage_cluster_id = :storage_cluster_id "
        "AND collected_at BETWEEN :start_time AND :end_time "
        "AND latency_total IS NOT NULL "
        f"{object_filter} "
        f"{identity_filter} "
        "GROUP BY object_id, object_name, object_type "
        "ORDER BY p95_latency DESC LIMIT :limit"
    )
    parameters = {
        "storage_cluster_id": str(storage_cluster_id),
        "start_time": str(start_time),
        "end_time": str(end_time),
        "limit": limit,
        **identity_parameters,
    }
    if object_type:
        parameters["object_type"] = object_type
    with QuestDBSession(config=get_storage_config(db=db)) as connection:
        rows = connection.execute(statement, parameters).all()
    return [
        {
            "object_id": str(row[0]),
            "object_name": row[1],
            "object_type": row[2],
            "p95_latency": float(row[3]),
            "avg_latency": float(row[4]),
            "max_latency": float(row[5]),
            "avg_read_latency": None if row[6] is None else float(row[6]),
            "avg_write_latency": None if row[7] is None else float(row[7]),
            "avg_iops": None if row[8] is None else float(row[8]),
            "avg_throughput": None if row[9] is None else float(row[9]),
            "sample_count": int(row[10]),
        }
        for row in rows
    ]


def has_performance_metrics(db: Session, storage_cluster_id: int) -> bool:
    statement = text(
        "SELECT 1 FROM storage_performance_metrics "
        "WHERE storage_cluster_id = :storage_cluster_id LIMIT 1"
    )
    with QuestDBSession(config=get_storage_config(db=db)) as connection:
        row = connection.execute(
            statement,
            {"storage_cluster_id": str(storage_cluster_id)},
        ).first()
    return row is not None


def get_repeated_fault_rows(
    db: Session,
    storage_cluster_id: int,
    start_time: datetime,
    end_time: datetime,
) -> list[dict]:
    count = func.count(StorageAlerts.id)
    first_seen = func.min(StorageAlerts.updated_at)
    last_seen = func.max(StorageAlerts.updated_at)
    rows = db.execute(
        select(
            StorageAlerts.source,
            StorageAlerts.fingerprint,
            func.max(StorageAlerts.id).label("sample_event_id"),
            count.label("occurrence_count"),
            first_seen.label("first_occurred_at"),
            last_seen.label("last_occurred_at"),
        )
        .where(
            StorageAlerts.storage_cluster_id == storage_cluster_id,
            StorageAlerts.source.in_(("netapp", "isilon")),
            StorageAlerts.fingerprint.is_not(None),
            StorageAlerts.updated_at.between(_naive(start_time), _naive(end_time)),
        )
        .group_by(StorageAlerts.source, StorageAlerts.fingerprint)
        .having(count >= 2)
        .order_by(count.desc(), last_seen.desc())
    ).all()
    return [
        {
            "source": row.source,
            "fingerprint": row.fingerprint,
            "sample_event_id": int(row.sample_event_id),
            "count": int(row.occurrence_count),
            "first_occurred_at": row.first_occurred_at,
            "last_occurred_at": row.last_occurred_at,
        }
        for row in rows
    ]
