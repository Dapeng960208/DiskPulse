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
_PREVIEW_FIELDS = frozenset({
    "resource_id", "resource_type", "resource", "storage_type",
    "old_hard_limit", "old_soft_limit", "new_hard_limit", "new_soft_limit",
    "unit", "change_reason",
})
_TERMINAL_CONFIRMATION_STATUSES = frozenset({"succeeded", "failed", "cancelled"})
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


def pending_confirmation_from_audit(
    audit: AIAuditLog,
    *,
    now: datetime | None = None,
) -> dict | None:
    """Return only the safe, still-valid confirmation metadata persisted in an audit."""
    if audit.status != "awaiting_confirmation":
        return None
    try:
        detail = json.loads(audit.detail_payload or "[]")
    except json.JSONDecodeError:
        return None
    if not isinstance(detail, list):
        return None
    current_epoch = int((now or datetime.now()).timestamp())
    for entry in reversed(detail):
        if not isinstance(entry, dict) or entry.get("status") != "awaiting_confirmation":
            continue
        candidate = entry
        result = entry.get("result")
        if isinstance(result, dict):
            data = result.get("data")
            if isinstance(data, dict) and isinstance(data.get("confirmation_required"), dict):
                candidate = data["confirmation_required"]
        confirmation_id = candidate.get("confirmation_id")
        expires_at = candidate.get("expires_at")
        preview = candidate.get("preview")
        if (
            not isinstance(confirmation_id, str)
            or not isinstance(expires_at, int)
            or expires_at <= current_epoch
            or not isinstance(preview, dict)
        ):
            continue
        # Review source: SSE-only confirmation cards vanished on reload.
        # Resolution: restore only whitelisted preview fields from the owning
        # audit; normalized tool arguments remain Redis-only.
        safe_preview = {key: preview[key] for key in _PREVIEW_FIELDS if key in preview}
        return {
            "confirmation_id": confirmation_id,
            "expires_at": expires_at,
            "expires_in_seconds": expires_at - current_epoch,
            "preview": safe_preview,
        }
    return None


def completed_confirmation_from_audit(audit: AIAuditLog) -> dict | None:
    """Restore the safe terminal confirmation state for a conversation reload."""
    if audit.status not in _TERMINAL_CONFIRMATION_STATUSES:
        return None
    try:
        detail = json.loads(audit.detail_payload or "[]")
    except json.JSONDecodeError:
        return None
    if not isinstance(detail, list):
        return None
    for entry in reversed(detail):
        if not isinstance(entry, dict) or entry.get("status") not in _TERMINAL_CONFIRMATION_STATUSES:
            continue
        confirmation_id = entry.get("confirmation_id")
        preview = entry.get("preview")
        decision = entry.get("decision")
        if (
            not isinstance(confirmation_id, str)
            or not isinstance(preview, dict)
            or decision not in {"confirm", "cancel"}
        ):
            continue
        confirmation = {
            "confirmation_id": confirmation_id,
            "preview": {key: preview[key] for key in _PREVIEW_FIELDS if key in preview},
            "decided": decision,
        }
        if decision == "confirm":
            result = entry.get("result")
            if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
                continue
            safe_result = {"ok": result["ok"]}
            error = result.get("error")
            if isinstance(error, str) and error:
                safe_result["error"] = error[:256]
            confirmation["result"] = safe_result
        return confirmation
    return None


def _safe_result(result: dict | None) -> dict | None:
    if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
        return None
    safe_result = {"ok": result["ok"]}
    error = result.get("error")
    if isinstance(error, str) and error:
        safe_result["error"] = error[:256]
    return safe_result


def _audit_visibility(audit: AIAuditLog, detail: list) -> dict | None:
    """Reuse the audit's established visibility marker for terminal traces."""
    for trace in reversed(detail):
        if isinstance(trace, dict) and isinstance(trace.get("visibility"), dict):
            return trace["visibility"]
    try:
        response = json.loads(audit.response_payload or "{}")
    except json.JSONDecodeError:
        return None
    visibility = response.get("visibility") if isinstance(response, dict) else None
    return visibility if isinstance(visibility, dict) else None


def _complete_confirmation(
    audit: AIAuditLog,
    *,
    record: dict,
    confirmation_id: str,
    decision: str,
    status_value: str,
    result: dict | None = None,
    error_message: str | None = None,
) -> None:
    try:
        detail = json.loads(audit.detail_payload or "[]")
    except json.JSONDecodeError:
        detail = []
    if not isinstance(detail, list):
        detail = []
    entry = {
        "status": status_value,
        "confirmation_id": confirmation_id,
        "decision": decision,
        "preview": {
            key: value
            for key, value in (record.get("preview") or {}).items()
            if key in _PREVIEW_FIELDS
        },
    }
    visibility = _audit_visibility(audit, detail)
    if visibility is not None:
        entry["visibility"] = visibility
    safe_result = _safe_result(result)
    if safe_result is not None:
        entry["result"] = safe_result
    detail.append(entry)
    audit.status = status_value
    audit.detail_payload = json.dumps(detail, ensure_ascii=False)
    audit.error_message = error_message
    audit.finished_at = datetime.now()
    audit.updated_at = datetime.now()


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
    expires_at = int(datetime.now().timestamp()) + _TTL_SECONDS
    record = {
        "confirmation_id": confirmation_id,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "audit_id": audit.id,
        "tool_name": definition.name,
        "arguments": normalized,
        "preview": preview,
        "expires_at": expires_at,
    }
    try:
        _quota_redis_client().setex(_key(confirmation_id), _TTL_SECONDS, json.dumps(record, ensure_ascii=False))
    except redis.RedisError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI quota confirmation unavailable") from error
    detail = json.loads(audit.detail_payload or "[]")
    pending = {
        "confirmation_id": confirmation_id,
        "expires_at": expires_at,
        "expires_in_seconds": _TTL_SECONDS,
        "preview": preview,
    }
    detail.append({"status": "awaiting_confirmation", **pending})
    audit.status = "awaiting_confirmation"
    audit.detail_payload = json.dumps(detail, ensure_ascii=False)
    audit.updated_at = datetime.now()
    db.flush()
    return pending


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
        _complete_confirmation(
            audit,
            record=record,
            confirmation_id=confirmation_id,
            decision="cancel",
            status_value="cancelled",
        )
        db.flush()
        return {"decision": "cancel", "confirmation_id": confirmation_id}
    definition = registry.get(record["tool_name"])
    if definition is None or not is_quota_write_tool(definition.name):
        error_message = "quota tool is no longer registered"
        _complete_confirmation(
            audit,
            record=record,
            confirmation_id=confirmation_id,
            decision="confirm",
            status_value="failed",
            result={"ok": False, "error": error_message},
            error_message=error_message,
        )
        db.flush()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="quota tool is no longer available")
    # Revalidate the Redis-bound, normalized arguments immediately before execution.
    result = execute_tool(
        app=app,
        registry=registry,
        tool_name=definition.name,
        arguments=record["arguments"],
        current_user=current_user,
    )
    _complete_confirmation(
        audit,
        record=record,
        confirmation_id=confirmation_id,
        decision="confirm",
        status_value="succeeded" if result.get("ok") else "failed",
        result=result,
        error_message=result.get("error") if not result.get("ok") else None,
    )
    db.flush()
    return {"decision": "confirm", "confirmation_id": confirmation_id, "result": result}
