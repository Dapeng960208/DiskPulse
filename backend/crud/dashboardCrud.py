# -*- coding: utf-8 -*-
from datetime import timezone

from sqlalchemy import and_, bindparam, func, or_, select, text
from sqlalchemy.orm import Session

from dependencies import QuestDBSession
from models import Group, Project, StorageAlerts, StorageCluster, StorageUsage, User
from utils.query import apply_use_ratio_range


def _questdb_time(value):
    if value.tzinfo is None:
        return value.isoformat()
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def get_project(db: Session, project_id: int):
    return db.get(Project, project_id)


def get_active_clusters(db: Session):
    return db.scalars(
        select(StorageCluster).where(StorageCluster.is_active.is_(True))
    ).all()


def get_capacity_items(
    db: Session,
    project_id: int | None,
    use_ratio_min: float | None = None,
    use_ratio_max: float | None = None,
):
    if project_id is None:
        statement = select(Project).where(Project.is_common.is_(False))
        model = Project
    else:
        statement = select(Group).where(
            Group.project_id == project_id,
            Group.enable_monitoring.is_(True),
        )
        model = Group
    used_column = Project.used if project_id is None else Group.used
    statement = apply_use_ratio_range(statement, model, use_ratio_min, use_ratio_max)
    return db.scalars(statement.order_by(used_column.desc()).limit(10)).all()


def get_project_storage_cluster_count(db: Session, project_id: int) -> int:
    return int(db.scalar(
        select(func.count(func.distinct(Group.storage_cluster_id))).where(
            Group.project_id == project_id,
            Group.enable_monitoring.is_(True),
        )
    ) or 0)


def get_top_users(db: Session, project_id: int):
    used_gb = func.sum(StorageUsage.used).label("used_gb")
    return db.execute(
        select(User.id, User.rd_username, User.username, used_gb)
        .join(StorageUsage, StorageUsage.user_id == User.id)
        .join(Group, StorageUsage.group_id == Group.id)
        .where(Group.project_id == project_id)
        .group_by(User.id, User.rd_username, User.username)
        .order_by(used_gb.desc())
        .limit(10)
    ).all()


def _alert_filters(start_time, end_time):
    return (
        StorageAlerts.source == "diskpulse",
        StorageAlerts.alert_type == "alert",
        StorageAlerts.event_type == "trigger",
        StorageAlerts.updated_at >= start_time,
        StorageAlerts.updated_at <= end_time,
    )


def _project_alert_scope(project_id: int):
    group_ids = select(Group.id).where(Group.project_id == project_id)
    usage_ids = select(StorageUsage.id).join(Group).where(Group.project_id == project_id)
    return or_(
        and_(StorageAlerts.related_type == "Project", StorageAlerts.related_id == project_id),
        and_(StorageAlerts.related_type == "Group", StorageAlerts.related_id.in_(group_ids)),
        and_(StorageAlerts.related_type == "StorageUsage", StorageAlerts.related_id.in_(usage_ids)),
    )


def get_alert_level_counts(db: Session, start_time, end_time, project_id: int | None):
    statement = select(StorageAlerts.alert_level, func.count(StorageAlerts.id)).where(
        *_alert_filters(start_time, end_time)
    )
    if project_id is not None:
        statement = statement.where(_project_alert_scope(project_id))
    return db.execute(statement.group_by(StorageAlerts.alert_level)).all()


def get_capacity_trend(*, db: Session, project_id: int | None, start_time, end_time):
    if project_id is not None:
        query = text(
            "SELECT updated_at, max(used) AS used_gb "
            "FROM project_storage_usages "
            "WHERE project_id = :project_id AND updated_at BETWEEN :start_time AND :end_time "
            "SAMPLE BY 1d ALIGN TO CALENDAR ORDER BY updated_at"
        )
        params = {
            "project_id": project_id,
            "start_time": _questdb_time(start_time),
            "end_time": _questdb_time(end_time),
        }
    else:
        cluster_ids = [cluster.id for cluster in get_active_clusters(db)]
        if not cluster_ids:
            return []
        query = text(
            "SELECT updated_at, sum(cluster_used) AS used_gb FROM ("
            "SELECT updated_at, storage_cluster_id, max(used) AS cluster_used "
            "FROM storage_cluster_storage_usages "
            "WHERE storage_cluster_id IN :cluster_ids "
            "AND updated_at BETWEEN :start_time AND :end_time "
            "SAMPLE BY 1d ALIGN TO CALENDAR"
            ") SAMPLE BY 1d ALIGN TO CALENDAR ORDER BY updated_at"
        ).bindparams(bindparam("cluster_ids", expanding=True))
        params = {
            "cluster_ids": [str(cluster_id) for cluster_id in cluster_ids],
            "start_time": _questdb_time(start_time),
            "end_time": _questdb_time(end_time),
        }

    with QuestDBSession() as quest_db:
        return quest_db.execute(query, params).all()
