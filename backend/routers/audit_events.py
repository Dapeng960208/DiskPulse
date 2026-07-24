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
AI_AUDIT_RESPONSE_BLACKLIST_FIELDS = (
    "actor",
    "actor_user_id",
    "after_summary",
    "before_summary",
    "metadata",
    "resource",
)


@router.get(
    "",
    response_model=auditSchema.AuditEventPage,
    openapi_extra={
        "ai_exposed": True,
        "ai_name": "list_audit_events",
        "ai_blacklist_fields": AI_AUDIT_RESPONSE_BLACKLIST_FIELDS,
        "ai_description": (
            "审计研判专用只读工具：先确认项目或完整时间范围，再在当前用户的项目权限范围内"
            "按筛选条件查询统一审计事件。调用任一审计工具后的最终答复必须区分事实、推断和"
            "数据缺口，并使用研判依据、排查建议、解决方案、限制与数据缺口四个标题。"
        ),
    },
)
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
        content=audit_service.serialize_audit_events(db, events, current_user=current_user),
        total=total,
    )


@router.get(
    "/{event_id}",
    response_model=auditSchema.AuditEventOut,
    openapi_extra={
        "ai_exposed": True,
        "ai_name": "get_audit_event",
        "ai_blacklist_fields": AI_AUDIT_RESPONSE_BLACKLIST_FIELDS,
        "ai_description": (
            "审计研判专用只读工具：在当前用户的项目权限范围内查询一条统一审计事件详情。"
            "优先根据列表结果下钻；以 operation_id、trace_id 或 request_id 配对同一操作的"
            "尝试与结果，不得把脱敏字段、空结果或无权限推断为事实。"
        ),
    },
)
def get_audit_event(event_id: str, current_user: CurrentUserDep, db: DBDep):
    event = audit_service.get_visible_audit_event(
        db,
        current_user=current_user,
        event_id=event_id,
    )
    return audit_service.serialize_audit_events(db, [event], current_user=current_user)[0]
