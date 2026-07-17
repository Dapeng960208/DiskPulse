# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import AuditEvent


def list_audit_events(
    db: Session,
    *,
    page: int,
    size: int,
    project_id: int | None = None,
    actor_user_id: int | None = None,
    action: str | None = None,
    outcome: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> tuple[list[AuditEvent], int]:
    query = db.query(AuditEvent)
    if project_id is not None:
        query = query.filter(AuditEvent.project_id == project_id)
    if actor_user_id is not None:
        query = query.filter(AuditEvent.actor_user_id == actor_user_id)
    if action:
        query = query.filter(AuditEvent.action == action)
    if outcome:
        query = query.filter(AuditEvent.outcome == outcome)
    if start_time is not None:
        query = query.filter(AuditEvent.occurred_at >= start_time)
    if end_time is not None:
        query = query.filter(AuditEvent.occurred_at <= end_time)

    total = query.count()
    rows = (
        query.order_by(desc(AuditEvent.occurred_at), desc(AuditEvent.id))
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return rows, total
