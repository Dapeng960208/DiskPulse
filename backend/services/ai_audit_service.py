# -*- coding: utf-8 -*-
import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from crud import aiCrud
from models import AIAuditLog


def serialize_audit(item: AIAuditLog, *, include_detail: bool = False) -> dict:
    data = {
        "id": item.id,
        "model_id": item.model_id,
        "conversation_id": item.conversation_id,
        "user_id": item.user_id,
        "source": item.source,
        "source_ref": item.source_ref,
        "tool_call_count": item.tool_call_count,
        "tool_failed_count": item.tool_failed_count,
        "status": item.status,
        "error_message": item.error_message,
        "trace_id": item.trace_id,
        "started_at": item.started_at,
        "finished_at": item.finished_at,
    }
    if include_detail:
        data.update(
            {
                "request": _json_value(item.request_payload),
                "response": _json_value(item.response_payload),
                "detail": _json_value(item.detail_payload),
            }
        )
    return data


def _json_value(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def list_audits(db: Session, **filters) -> dict:
    rows, total = aiCrud.list_audits(db, **filters)
    return {"content": [serialize_audit(item) for item in rows], "total": total}


def get_audit(db: Session, audit_id: int) -> dict:
    item = aiCrud.get_audit(db, audit_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 审计记录不存在")
    return serialize_audit(item, include_detail=True)


def get_conversation_audits(db: Session, conversation_id: int) -> dict:
    rows = aiCrud.list_conversation_audits(db, conversation_id)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 会话审计记录不存在")
    return {"conversation_id": conversation_id, "content": [serialize_audit(item, include_detail=True) for item in rows]}
