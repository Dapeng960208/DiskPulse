# -*- coding: utf-8 -*-
"""One-time, server-bound confirmations for the two AI quota write tools."""

import json
from datetime import datetime
from uuid import uuid4

import redis
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import AIAuditLog, Group, StorageUsage
from services.ai_tool_service import AIToolDefinition, execute_tool
from services.quotaService import _quota_redis_client
from utils.auth_service import is_super_admin


_QUOTA_TOOL_NAMES = frozenset({"adjust_group_quota", "adjust_storage_usage_quota"})
_TTL_SECONDS = 300
_KEY_PREFIX = "diskpulse:ai-quota-confirmation:"
_CONSUME_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


def is_quota_write_tool(name: str) -> bool:
    return name in _QUOTA_TOOL_NAMES


def _key(confirmation_id: str) -> str:
    return f"{_KEY_PREFIX}{confirmation_id}"


def _normalise(definition: AIToolDefinition, arguments: dict) -> dict:
    payload = definition.input_model.model_validate(arguments)
    return payload.model_dump(mode="json", exclude_none=True, exclude_computed_fields=True)


def _preview(db: Session, *, tool_name: str, normalized: dict) -> dict:
    body = normalized.get("body") or {}
    if tool_name == "adjust_group_quota":
        resource = db.get(Group, normalized["group_id"])
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        label = resource.name
        resource_type = "group"
    else:
        resource = db.get(StorageUsage, normalized["storage_usage_id"])
        if resource is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage usage not found")
        label = resource.linux_path
        resource_type = "storage_usage"
    return {
        "resource_id": resource.id,
        "resource_type": resource_type,
        "resource": label,
        "storage_type": getattr(resource.storage_cluster, "storage_type", None),
        "old_hard_limit": resource.limit,
        "old_soft_limit": resource.soft_limit,
        "new_hard_limit": body.get("hard_limit"),
        "new_soft_limit": body.get("soft_limit"),
        "unit": body.get("unit"),
        "change_reason": body.get("change_reason"),
    }


def prepare_confirmation(
    db: Session,
    *,
    definition: AIToolDefinition,
    arguments: dict,
    user_id: int,
    conversation_id: int,
    audit: AIAuditLog,
) -> dict:
    if not is_quota_write_tool(definition.name):
        raise ValueError("unsupported quota confirmation tool")
    normalized = _normalise(definition, arguments)
    confirmation_id = str(uuid4())
    preview = _preview(db, tool_name=definition.name, normalized=normalized)
    record = {
        "confirmation_id": confirmation_id,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "audit_id": audit.id,
        "tool_name": definition.name,
        "arguments": normalized,
        "preview": preview,
        "expires_at": int(datetime.now().timestamp()) + _TTL_SECONDS,
    }
    try:
        _quota_redis_client().setex(_key(confirmation_id), _TTL_SECONDS, json.dumps(record, ensure_ascii=False))
    except redis.RedisError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI quota confirmation unavailable") from error
    detail = json.loads(audit.detail_payload or "[]")
    detail.append({"confirmation_id": confirmation_id, "status": "awaiting_confirmation", "preview": preview})
    audit.status = "awaiting_confirmation"
    audit.detail_payload = json.dumps(detail, ensure_ascii=False)
    audit.updated_at = datetime.now()
    db.commit()
    return {"confirmation_id": confirmation_id, "expires_in_seconds": _TTL_SECONDS, "preview": preview}


def decide_confirmation(
    db: Session,
    *,
    app,
    registry: dict[str, AIToolDefinition],
    conversation_id: int,
    confirmation_id: str,
    decision: str,
    current_user,
) -> dict:
    if not is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI quota confirmation requires super admin")
    raw = None
    try:
        client = _quota_redis_client()
        raw = client.get(_key(confirmation_id))
        if raw is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="quota confirmation expired or already used")
        if not client.eval(_CONSUME_SCRIPT, 1, _key(confirmation_id), raw):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="quota confirmation expired or already used")
    except redis.RedisError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI quota confirmation unavailable") from error
    record = json.loads(raw)
    if record["user_id"] != current_user.id or record["conversation_id"] != conversation_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="quota confirmation does not belong to this conversation")
    audit = db.get(AIAuditLog, record["audit_id"])
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI audit not found")
    if decision == "cancel":
        audit.status = "cancelled"
        audit.finished_at = datetime.now()
        audit.updated_at = datetime.now()
        db.commit()
        return {"decision": "cancel", "confirmation_id": confirmation_id}
    definition = registry.get(record["tool_name"])
    if definition is None or not is_quota_write_tool(definition.name):
        audit.status = "failed"
        audit.error_message = "quota tool is no longer registered"
        audit.finished_at = datetime.now()
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="quota tool is no longer available")
    # Revalidate the Redis-bound, normalized arguments immediately before execution.
    result = execute_tool(
        app=app,
        registry=registry,
        tool_name=definition.name,
        arguments=record["arguments"],
        current_user=current_user,
    )
    audit.status = "succeeded" if result.get("ok") else "failed"
    audit.finished_at = datetime.now()
    audit.updated_at = datetime.now()
    db.commit()
    return {"decision": "confirm", "confirmation_id": confirmation_id, "result": result}
