# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from crud.configCrud import get_storage_config
from dependencies import QuestDBSession
from models import StorageAlerts


def _naive(value: datetime) -> datetime:
    return value.astimezone().replace(tzinfo=None) if value.tzinfo is not None else value


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
            StorageAlerts.source.in_(("diskpulse", "netapp", "isilon")),
            StorageAlerts.updated_at.between(_naive(start_time), _naive(end_time)),
        )
    ).all()
    return [{"source": row.source, "severity": row.severity} for row in rows]


def get_top_latency_rows(
    db: Session,
    storage_cluster_id: int,
    start_time: datetime,
    end_time: datetime,
    limit: int,
    object_type: str | None = None,
) -> list[dict]:
    object_filter = "AND object_type = :object_type" if object_type else ""
    statement = text(
        "SELECT object_id, object_name, object_type, "
        "approx_percentile(latency_total, 0.95) AS p95_latency, "
        "avg(latency_total) AS avg_latency, max(latency_total) AS max_latency, "
        "count() AS sample_count "
        "FROM storage_performance_metrics "
        "WHERE storage_cluster_id = :storage_cluster_id "
        "AND collected_at BETWEEN :start_time AND :end_time "
        "AND latency_total IS NOT NULL "
        f"{object_filter} "
        "GROUP BY object_id, object_name, object_type "
        "ORDER BY p95_latency DESC LIMIT :limit"
    )
    parameters = {
        "storage_cluster_id": str(storage_cluster_id),
        "start_time": str(start_time),
        "end_time": str(end_time),
        "limit": limit,
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
            "sample_count": int(row[6]),
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
            "count": int(row.occurrence_count),
            "first_occurred_at": row.first_occurred_at,
            "last_occurred_at": row.last_occurred_at,
        }
        for row in rows
    ]
