# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from crud import dashboardCrud


logger = logging.getLogger(__name__)


def _number(value) -> float:
    return float(value or 0)


def _time_range():
    end_time = datetime.now()
    start_time = datetime.combine(end_time.date() - timedelta(days=29), time.min)
    return start_time, end_time


def _project(db: Session, project_id: int | None):
    if project_id is None:
        return None
    project = dashboardCrud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


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


def get_summary(db: Session, project_id: int | None = None):
    start_time, end_time = _time_range()
    project = _project(db, project_id)
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

    alert_count = sum(
        int(count)
        for _alert_date, count in dashboardCrud.get_alert_counts(
            db, start_time, end_time, project_id
        )
    )
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
            "alert_count": alert_count,
        },
    }


def get_capacity_trend(db: Session, project_id: int | None = None):
    _project(db, project_id)
    start_time, end_time = _time_range()
    try:
        rows = dashboardCrud.get_capacity_trend(
            db=db,
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
        )
    except Exception:
        logger.warning("QuestDB dashboard capacity trend is unavailable", exc_info=True)
        return []
    return [
        {"timestamp": timestamp, "used_gb": _number(used_gb)}
        for timestamp, used_gb in rows
    ]


def get_capacity_items(db: Session, project_id: int | None = None):
    _project(db, project_id)
    return [
        _capacity(item)
        for item in dashboardCrud.get_capacity_items(db, project_id)
    ]


def get_alert_trend(db: Session, project_id: int | None = None):
    _project(db, project_id)
    start_time, end_time = _time_range()
    rows = dashboardCrud.get_alert_counts(db, start_time, end_time, project_id)
    return _fill_alert_trend(rows, start_time)


def get_top_users(db: Session, project_id: int):
    _project(db, project_id)
    return [
        {
            "id": user_id,
            "name": rd_username or username or f"用户 {user_id}",
            "used_gb": _number(used_gb),
        }
        for user_id, rd_username, username, used_gb in dashboardCrud.get_top_users(
            db, project_id
        )
    ]
