# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session
from models import StorageAlerts
from schemas import storageAlertsSchema
from sqlalchemy import or_, desc, asc
from utils.query import get_sort_column


def get_storage_alerts(db: Session, page: int, size: int, nameLike: str | None = None, prop: str | None = None,
                       order: str | None = None, related_type: str | None = None, related_id: int | None = None,
                       alert_type: str | None = None):
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
    return storage_alerts, total
