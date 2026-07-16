# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session
from models import Group, Project, StorageAlerts, StorageCluster, StorageUsage
from schemas import storageAlertsSchema
from sqlalchemy import or_, desc, asc
from utils.query import get_sort_column


def get_storage_alerts(db: Session, page: int, size: int, nameLike: str | None = None, prop: str | None = None,
                       order: str | None = None, related_type: str | None = None, related_id: int | None = None,
                       alert_type: str | None = None, event_type: str | None = None,
                       quota_basis: str | None = None, delivery_status: str | None = None):
    query = db.query(StorageAlerts).filter(StorageAlerts.source == "diskpulse")
    conditions = []
    if nameLike and len(nameLike.strip()) > 0:
        conditions.append(
            or_(StorageAlerts.description.like(f"%{nameLike}%"), StorageAlerts.related_type.like(f"%{nameLike}%")))
    if related_type:
        conditions.append(StorageAlerts.related_type == related_type)
    if related_id:
        conditions.append(StorageAlerts.related_id == related_id)
    if alert_type:
        conditions.append(StorageAlerts.alert_type == alert_type)
    if event_type:
        conditions.append(StorageAlerts.event_type == event_type)
    if quota_basis:
        conditions.append(StorageAlerts.quota_basis == quota_basis)
    if delivery_status:
        conditions.append(StorageAlerts.delivery_status == delivery_status)
    query = query.filter(*conditions)
    total = query.count()
    sort_column = get_sort_column(StorageAlerts, prop)
    if sort_column is not None:
        if order and order.lower() == 'descending':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(StorageAlerts.updated_at.desc())
    storage_alerts = query.offset((page - 1) * size).limit(size).all()
    cluster_names = dict(
        db.query(StorageCluster.id, StorageCluster.name)
        .filter(StorageCluster.id.in_({row.storage_cluster_id for row in storage_alerts if row.storage_cluster_id}))
        .all()
    )
    project_names = {}
    usage_ids = {row.related_id for row in storage_alerts if row.related_type == "StorageUsage" and row.related_id}
    if usage_ids:
        project_names.update(
            (("StorageUsage", usage_id), project_name)
            for usage_id, project_name in db.query(StorageUsage.id, Project.name)
            .join(Group, StorageUsage.group_id == Group.id)
            .join(Project, Group.project_id == Project.id)
            .filter(StorageUsage.id.in_(usage_ids))
            .all()
        )
    group_ids = {row.related_id for row in storage_alerts if row.related_type == "Group" and row.related_id}
    if group_ids:
        project_names.update(
            (("Group", group_id), project_name)
            for group_id, project_name in db.query(Group.id, Project.name)
            .join(Project, Group.project_id == Project.id)
            .filter(Group.id.in_(group_ids))
            .all()
        )
    project_ids = {row.related_id for row in storage_alerts if row.related_type == "Project" and row.related_id}
    if project_ids:
        project_names.update(
            (("Project", project_id), project_name)
            for project_id, project_name in db.query(Project.id, Project.name)
            .filter(Project.id.in_(project_ids))
            .all()
        )
    for row in storage_alerts:
        row.cluster_name = cluster_names.get(row.storage_cluster_id)
        row.project_name = project_names.get((row.related_type, row.related_id))
    return storage_alerts, total
