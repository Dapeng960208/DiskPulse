# -*- coding: utf-8 -*-
import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from crud import aiCrud
from models import AIAuditLog
from services.audit_service import redact_audit_payload


_AI_SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "prompt",
    "request",
    "response",
    "raw",
    "path",
    "directory",
    "filename",
    "content",
    "message",
)


def _redact_ai_payload(value, *, key: str | None = None):
    key_name = (key or "").casefold()
    if any(part in key_name for part in _AI_SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            str(item_key): _redact_ai_payload(item, key=str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_ai_payload(item, key=key) for item in value]
    return redact_audit_payload(value, key=key)


def serialize_audit(item: AIAuditLog, *, include_detail: bool = False) -> dict:
    detail = _json_value(item.detail_payload)
    tool_names = []
    for trace in detail if isinstance(detail, list) else []:
        name = trace.get("tool_name") if isinstance(trace, dict) else None
        if isinstance(name, str) and name and name not in tool_names:
            tool_names.append(name)

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
        "conversation": (
            {"id": item.conversation.id, "title": item.conversation.title}
            if item.conversation is not None
            else None
        ),
        "user": (
            {
                "id": item.user.id,
                "rd_username": item.user.rd_username,
                "username": item.user.username,
            }
            if item.user is not None
            else None
        ),
        "model": (
            {"id": item.model.id, "name": item.model.name, "model": item.model.model}
            if item.model is not None
            else None
        ),
        "tool_names": tool_names,
    }
    if include_detail:
        data.update(
            {
                "request": _redact_ai_payload(_json_value(item.request_payload)),
                "response": _redact_ai_payload(_json_value(item.response_payload)),
                "detail": _redact_ai_payload(_json_value(item.detail_payload)),
            }
        )
        if item.error_message:
            data["error_message"] = "AI 操作失败"
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
