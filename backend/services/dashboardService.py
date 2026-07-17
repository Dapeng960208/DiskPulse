# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from crud import dashboardCrud


logger = logging.getLogger(__name__)


def _number(value) -> float:
    return float(value or 0)


def _capacity(item) -> dict:
    limit_gb = _number(item.limit)
    used_gb = _number(item.used)
    return {
        "id": item.id,
        "name": item.name,
        "limit_gb": limit_gb,
        "used_gb": used_gb,
        "available_gb": max(limit_gb - used_gb, 0),
        "use_ratio": _number(item.use_ratio),
    }


def _fill_alert_trend(rows, start_time, days=30):
    counts = {str(alert_date): int(count) for alert_date, count in rows}
    return [
        {
            "date": (start_time.date() + timedelta(days=offset)),
            "count": counts.get(str(start_time.date() + timedelta(days=offset)), 0),
        }
        for offset in range(days)
    ]


def get_dashboard_overview(db: Session, project_id: int | None = None):
    end_time = datetime.now()
    start_time = datetime.combine(end_time.date() - timedelta(days=29), time.min)
    project = dashboardCrud.get_project(db, project_id) if project_id is not None else None
    if project_id is not None and project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    if project is None:
        clusters = dashboardCrud.get_active_clusters(db)
        limit_gb = sum(_number(cluster.limit) for cluster in clusters)
        used_gb = sum(_number(cluster.used) for cluster in clusters)
        cluster_count = len(clusters)
        updated_at = max(
            (cluster.updated_at for cluster in clusters if cluster.updated_at),
            default=end_time,
        )
    else:
        limit_gb = _number(project.limit)
        used_gb = _number(project.used)
        cluster_count = dashboardCrud.get_project_storage_cluster_count(db, project.id)
        updated_at = project.updated_at or end_time

    capacity_items = dashboardCrud.get_capacity_items(db, project_id)
    alert_rows = dashboardCrud.get_alert_counts(db, start_time, end_time, project_id)
    alert_trend = _fill_alert_trend(alert_rows, start_time)
    try:
        trend_rows = dashboardCrud.get_capacity_trend(
            db=db,
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
        )
        capacity_trend = [
            {"timestamp": timestamp, "used_gb": _number(used_gb)}
            for timestamp, used_gb in trend_rows
        ]
    except Exception:
        logger.warning("QuestDB dashboard capacity trend is unavailable", exc_info=True)
        capacity_trend = []

    use_ratio = (used_gb / limit_gb * 100) if limit_gb > 0 else 0
    return {
        "scope": {
            "mode": "project" if project else "global",
            "project_id": project.id if project else None,
            "project_name": project.name if project else None,
            "start_time": start_time,
            "end_time": end_time,
            "updated_at": updated_at,
        },
        "summary": {
            "limit_gb": limit_gb,
            "used_gb": used_gb,
            "available_gb": max(limit_gb - used_gb, 0),
            "use_ratio": round(use_ratio, 2),
            "storage_cluster_count": cluster_count,
            "alert_count": sum(point["count"] for point in alert_trend),
        },
        "capacity_trend": capacity_trend,
        "capacity_items": [_capacity(item) for item in capacity_items],
        "alert_trend": alert_trend,
    }
