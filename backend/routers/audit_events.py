# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from dependencies import CurrentUserDep, get_db
from schemas import auditSchema
from services import audit_service


router = APIRouter(prefix="/v1/audit-events", tags=["audit-events"])
DBDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=auditSchema.AuditEventPage)
def list_audit_events(
    current_user: CurrentUserDep,
    db: DBDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    project_id: Annotated[int | None, Query(gt=0)] = None,
    actor_user_id: Annotated[int | None, Query(gt=0)] = None,
    action: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    outcome: Annotated[auditSchema.AuditOutcome | None, Query()] = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
):
    events, total = audit_service.list_visible_audit_events(
        db,
        current_user=current_user,
        page=page,
        size=size,
        project_id=project_id,
        actor_user_id=actor_user_id,
        action=action,
        outcome=outcome,
        start_time=start_time,
        end_time=end_time,
    )
    return auditSchema.AuditEventPage(
        content=[audit_service.serialize_audit_event(event) for event in events],
        total=total,
    )


@router.get("/{event_id}", response_model=auditSchema.AuditEventOut)
def get_audit_event(event_id: str, current_user: CurrentUserDep, db: DBDep):
    event = audit_service.get_visible_audit_event(
        db,
        current_user=current_user,
        event_id=event_id,
    )
    return audit_service.serialize_audit_event(event)
