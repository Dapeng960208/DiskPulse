# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
import json
from time import monotonic
from typing import Iterator
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from appConfig import base_config
from crud import aiCrud
from models import AIConversation, AIAuditLog, AIMessage, Group, StorageUsage, User
from services.audit_service import AuditContext, append_audit_event, redact_audit_payload
from services import ai_quota_confirmation_service
from services.ai_client import AIClientError, AIClientToolArgumentsError, AIClientToolCall, chat_completion_stream
from services.ai_config_service import serialize_model
from services.ai_tool_service import build_tool_registry, execute_tool, tool_definitions
from services.incidentAiService import render_restricted_diagnosis
from services.project_access_service import accessible_project_ids
from utils.auth_service import is_super_admin


SYSTEM_PROMPT = """你是 DiskPulse AI 助手。你只能使用已授权的只读工具查询数据。
不得编造工具结果，不得请求或泄露密码、令牌、密钥及个人敏感信息。
回答应简洁、准确，并在数据不足时明确说明。"""

_DISPLAY_TOOL_RESULT_LIMIT_BYTES = 32 * 1024
_FAILED_RESPONSE = "抱歉，AI 服务暂时不可用，请稍后重试。"
_MAX_TOOL_ARGUMENT_REPAIRS = 2
_REDACTED = "[REDACTED]"
_HIDDEN_HISTORY_CONTENT = "该历史回复关联的项目权限已失效，内容已隐藏。"
_TRACE_SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "cookie",
    "prompt",
    "request",
    "response",
    "message",
    "content",
    "path",
    "directory",
    "filename",
    "raw",
    "device",
    "body",
)
_RECOVERY_BY_REASON = {
    "tool_iteration_limit": {"reason": "tool_iteration_limit", "action": "continue", "label": "继续查询"},
    "invalid_tool_arguments": {"reason": "invalid_tool_arguments", "action": "retry", "label": "重新查询"},
}
_DEGRADED_FALLBACKS = {
    "tool_iteration_limit": "本轮已达到工具查询上限。我已保留已完成的查询结果；如需补充信息，请授权继续查询。",
    "invalid_tool_arguments": "本轮工具参数多次无效，无法继续执行查询。我已保留当前可用信息；请重新查询。",
}
_SYSTEM_MANAGEMENT_PROMPT = """你当前已获得系统管理工具授权；这是上述只读工具限制的受控例外。
仅在用户明确要求时执行系统管理 CRUD 工具；不要将其用于普通查询。
删除或更新前，先简短说明将影响的资源和结果；如果请求范围不明确，先向用户澄清。"""


def _json_safe(value: object) -> object:
    """Convert tool output to JSON-compatible values before it reaches the client/audit."""
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return str(value)


def _is_sensitive_path(value: str) -> bool:
    return (
        value.startswith(("/", "\\"))
        or (len(value) >= 3 and value[0].isalpha() and value[1] == ":" and value[2] in {"/", "\\"})
    )


def _redact_sensitive(value: object, *, key: str | None = None) -> object:
    key_name = (key or "").casefold()
    if any(name in key_name for name in _TRACE_SENSITIVE_KEY_PARTS):
        return _REDACTED
    if isinstance(value, dict):
        return {
            str(item_key): _redact_sensitive(item, key=str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_sensitive(item, key=key) for item in value]
    if isinstance(value, str):
        return _REDACTED if _is_sensitive_path(value) else value
    return value


def _display_tool_result(result: object) -> tuple[object, bool]:
    """Keep a bounded, valid display copy without changing provider-facing tool output."""
    payload = _json_safe(result)
    if isinstance(payload, dict) and payload.get("ok") is False:
        return {"ok": False, "error": "工具请求失败"}, False
    safe = _redact_sensitive(payload)
    encoded = json.dumps(safe, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) <= _DISPLAY_TOOL_RESULT_LIMIT_BYTES:
        return safe, False
    preview_limit = max(0, _DISPLAY_TOOL_RESULT_LIMIT_BYTES - 512)
    preview = encoded[:preview_limit].decode("utf-8", errors="ignore")
    return {
        "preview": preview,
        "original_bytes": len(encoded),
        "message": "工具结果过大，已截断展示。",
    }, True


def _as_project_id(value: object) -> int | None:
    """Convert a value to a valid project ID, returning None for invalid values.

    Explicitly rejects booleans first to avoid treating True/False as 1/0.
    Returns None for zero and negative integers as they are not valid project IDs.
    """
    if isinstance(value, bool):
        return None
    try:
        project_id = int(value)
    except (TypeError, ValueError):
        return None
    return project_id if project_id > 0 else None


def _known_visibility(
    project_scope_ids: set[int] | tuple[int, ...] | list[int] = (),
    *,
    requires_super_admin: bool = False,
) -> dict:
    return {
        "known": True,
        "project_scope_ids": sorted(set(project_scope_ids)),
        "requires_super_admin": requires_super_admin,
    }


def _unknown_visibility() -> dict:
    return {"known": False, "project_scope_ids": [], "requires_super_admin": False}


def _normalise_visibility(value: object) -> dict | None:
    if not isinstance(value, dict) or value.get("known") is not True:
        return None
    raw_project_ids = value.get("project_scope_ids", [])
    if not isinstance(raw_project_ids, list):
        return None
    project_ids = {_as_project_id(item) for item in raw_project_ids}
    if None in project_ids:
        return None
    return _known_visibility(
        project_ids,
        requires_super_admin=value.get("requires_super_admin") is True,
    )


def _combine_visibility(left: dict, right: dict) -> dict:
    if not left["known"] or not right["known"]:
        return _unknown_visibility()
    return _known_visibility(
        set(left["project_scope_ids"]) | set(right["project_scope_ids"]),
        requires_super_admin=left["requires_super_admin"] or right["requires_super_admin"],
    )


def _project_id_for_group(db: Session, group_id: object) -> int | None:
    identifier = _as_project_id(group_id)
    if identifier is None:
        return None
    group = db.get(Group, identifier)
    return _as_project_id(group.project_id) if group is not None else None


def _project_id_for_storage_usage(db: Session, storage_usage_id: object) -> int | None:
    identifier = _as_project_id(storage_usage_id)
    if identifier is None:
        return None
    storage_usage = db.get(StorageUsage, identifier)
    return _project_id_for_group(db, storage_usage.group_id) if storage_usage is not None else None


def _collect_project_scope_ids(db: Session, value: object) -> set[int]:
    project_ids: set[int] = set()

    def add_project(value: object) -> None:
        project_id = _as_project_id(value)
        if project_id is not None:
            project_ids.add(project_id)

    def add_related(resource_type: object, resource_id: object) -> None:
        normalized = str(resource_type or "").replace("_", "").casefold()
        if normalized == "project":
            add_project(resource_id)
        elif normalized == "group":
            project_id = _project_id_for_group(db, resource_id)
            if project_id is not None:
                project_ids.add(project_id)
        elif normalized == "storageusage":
            project_id = _project_id_for_storage_usage(db, resource_id)
            if project_id is not None:
                project_ids.add(project_id)

    def visit(item: object) -> None:
        if isinstance(item, dict):
            add_project(item.get("project_id"))
            project = item.get("project")
            if isinstance(project, dict):
                add_project(project.get("id"))
            project_id = _project_id_for_group(db, item.get("group_id"))
            if project_id is not None:
                project_ids.add(project_id)
            project_id = _project_id_for_storage_usage(db, item.get("storage_usage_id"))
            if project_id is not None:
                project_ids.add(project_id)
            add_related(item.get("related_type"), item.get("related_id"))
            for child in item.values():
                visit(child)
        elif isinstance(item, (list, tuple, set)):
            for child in item:
                visit(child)

    visit(value)
    return project_ids


def _tool_visibility(db: Session, definition, arguments: dict, result: dict) -> dict:
    if definition.system_management:
        return _known_visibility(requires_super_admin=True)
    project_ids = _collect_project_scope_ids(db, arguments) | _collect_project_scope_ids(db, result)
    if definition.name == "list_projects":
        data = result.get("data") if isinstance(result, dict) else None
        items = data.get("items") if isinstance(data, dict) else data
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    project_id = _as_project_id(item.get("id"))
                    if project_id is not None:
                        project_ids.add(project_id)
    # The tool has already passed its route-level authorization.  With no
    # project reference in either request or result it is a verified global
    # response, not an unknown project-bearing response.  Historical records
    # without this explicit marker still fail closed below.
    return _known_visibility(project_ids)


def _visibility_from_trace_entries(detail: object) -> dict:
    if not isinstance(detail, list) or not detail:
        return _known_visibility()
    visibility = _known_visibility()
    for trace in detail:
        if not isinstance(trace, dict):
            return _unknown_visibility()
        trace_visibility = _normalise_visibility(trace.get("visibility"))
        if trace_visibility is None:
            return _unknown_visibility()
        visibility = _combine_visibility(visibility, trace_visibility)
    return visibility


def _visibility_for_audit(audit: AIAuditLog) -> dict:
    response = _audit_payload(audit.response_payload, {})
    detail = _audit_payload(audit.detail_payload, [])
    trace_visibility = _visibility_from_trace_entries(detail)
    response_visibility = _normalise_visibility(
        response.get("visibility") if isinstance(response, dict) else None
    )
    if response_visibility is None:
        # Historical turns without an explicit response marker are only safe
        # when every persisted tool trace carries an explicit scope marker.
        # A no-tool legacy turn may still summarize an earlier project lookup,
        # so it must not become globally visible by default.
        return trace_visibility if isinstance(detail, list) and detail else _unknown_visibility()
    return _combine_visibility(response_visibility, trace_visibility)


def _visibility_is_allowed(visibility: dict, current_user: User | None, project_ids: set[int] | None) -> bool:
    if current_user is None or not visibility["known"]:
        return False
    if visibility["requires_super_admin"] and not is_super_admin(current_user):
        return False
    return project_ids is None or set(visibility["project_scope_ids"]).issubset(project_ids)


def _audit_payload(value: str | None, fallback: object) -> object:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _message_turn_metadata(message: AIMessage, audits_by_message: dict[int, AIAuditLog]) -> dict:
    audit = audits_by_message.get(message.id)
    if audit is None:
        return {"status": "succeeded", "tool_calls": []}
    detail = _audit_payload(audit.detail_payload, [])
    metadata = {
        "turn_id": audit.id,
        "status": audit.status,
        "tool_calls": detail if isinstance(detail, list) else [],
    }
    response = _audit_payload(audit.response_payload, {})
    recovery = response.get("recovery") if isinstance(response, dict) else None
    if isinstance(recovery, dict) and all(isinstance(recovery.get(key), str) for key in ("reason", "action", "label")):
        metadata["recovery"] = {
            "reason": recovery["reason"],
            "action": recovery["action"],
            "label": recovery["label"],
        }
    pending_confirmation = ai_quota_confirmation_service.pending_confirmation_from_audit(audit)
    if pending_confirmation is not None:
        metadata["quota_confirmation"] = pending_confirmation
    return metadata


def serialize_message(
    message: AIMessage,
    audit: AIAuditLog | None = None,
    *,
    visible: bool = True,
) -> dict:
    data = {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content if visible or message.role != "assistant" else _HIDDEN_HISTORY_CONTENT,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
    }
    if message.role == "assistant":
        if not visible:
            data.update({"status": "restricted", "tool_calls": []})
        elif audit is None:
            data.update({"status": "succeeded", "tool_calls": []})
        else:
            data.update(_message_turn_metadata(message, {message.id: audit}))
    return data


def serialize_conversation(
    conversation: AIConversation,
    *,
    include_messages: bool = False,
    audits_by_message: dict[int, AIAuditLog] | None = None,
    visibility_by_message: dict[int, bool] | None = None,
) -> dict:
    data = {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "model_id": conversation.model_id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }
    if include_messages:
        audits_by_message = audits_by_message or {}
        visibility_by_message = visibility_by_message or {}
        data["messages"] = [
            serialize_message(
                message,
                audit=audits_by_message.get(message.id),
                visible=visibility_by_message.get(message.id, True),
            )
            for message in conversation.messages
        ]
    return data


def list_available_models(db: Session) -> list[dict]:
    return [serialize_model(item) for item in aiCrud.list_models(db, available_only=True)]


def list_conversations(db: Session, user_id: int) -> list[dict]:
    return [serialize_conversation(item) for item in aiCrud.list_conversations(db, user_id)]


def create_conversation(
    db: Session,
    user_id: int,
    title: str,
    model_id: int,
    audit_context: AuditContext | None = None,
) -> dict:
    model = aiCrud.get_model(db, model_id)
    if model is None or not model.enabled or not model.enable_chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="可用 AI 模型不存在")
    conversation = aiCrud.add_conversation(
        db,
        AIConversation(
            user_id=user_id,
            model_id=model_id,
            title=title.strip() or "新对话",
        ),
    )
    if audit_context is not None:
        db.flush()
        append_audit_event(
            db,
            context=audit_context,
            phase="result",
            action="ai.conversation.create",
            resource_type="ai_conversation",
            resource_id=conversation.id,
            outcome="success",
            after_summary={"model_id": model_id},
        )
    db.commit()
    db.refresh(conversation)
    return serialize_conversation(conversation)


def get_conversation(db: Session, conversation_id: int, user_id: int) -> dict:
    conversation = _conversation_or_404(db, conversation_id, user_id)
    audits_by_message = _audits_by_message(db, conversation.id)
    # An assistant response without an audit record has no verifiable scope.
    # Keep legacy rows fail-closed until an explicit visibility marker exists.
    visibility_by_message = {
        message.id: False for message in conversation.messages if message.role == "assistant"
    }
    current_user = db.get(User, user_id)
    current_project_ids = accessible_project_ids(db, current_user)
    for message_id, audit in audits_by_message.items():
        visibility_by_message[message_id] = _visibility_is_allowed(
            _visibility_for_audit(audit),
            current_user,
            current_project_ids,
        )
    return serialize_conversation(
        conversation,
        include_messages=True,
        audits_by_message=audits_by_message,
        visibility_by_message=visibility_by_message,
    )


def delete_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
    audit_context: AuditContext | None = None,
) -> None:
    conversation = _conversation_or_404(db, conversation_id, user_id)
    if audit_context is not None:
        append_audit_event(
            db,
            context=audit_context,
            phase="result",
            action="ai.conversation.delete",
            resource_type="ai_conversation",
            resource_id=conversation.id,
            outcome="success",
            before_summary={"model_id": conversation.model_id},
        )
    db.delete(conversation)
    db.commit()


def _conversation_or_404(db: Session, conversation_id: int, user_id: int) -> AIConversation:
    conversation = aiCrud.get_conversation(db, conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 会话不存在")
    return conversation


def _audits_by_message(db: Session, conversation_id: int) -> dict[int, AIAuditLog]:
    audits_by_message = {}
    for audit in aiCrud.list_conversation_audits(db, conversation_id):
        response = _audit_payload(audit.response_payload, {})
        message_id = response.get("message_id") if isinstance(response, dict) else None
        if isinstance(message_id, int):
            audits_by_message[message_id] = audit
    return audits_by_message


def _historical_visibility(
    db: Session,
    conversation_id: int,
    *,
    exclude_audit_id: int | None = None,
) -> dict:
    visibility = _known_visibility()
    for audit in aiCrud.list_conversation_audits(db, conversation_id):
        if audit.id == exclude_audit_id:
            continue
        visibility = _combine_visibility(visibility, _visibility_for_audit(audit))
    return visibility


def _history(db: Session, conversation_id: int, *, current_user: User | None) -> list[dict]:
    # Fetch the newest bounded window cheaply, then restore provider-facing chronology.
    rows = list(
        db.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.id.desc())
            .limit(20)
        )
    )
    audits_by_message = _audits_by_message(db, conversation_id)
    project_ids = accessible_project_ids(db, current_user) if current_user is not None else set()
    history = []
    for item in reversed(rows):
        # The current turn reserves an empty assistant row before streaming; it is not provider history.
        if item.role == "assistant" and not item.content.strip():
            continue
        content = item.content
        if item.role == "assistant":
            audit = audits_by_message.get(item.id)
            if audit is None or not _visibility_is_allowed(
                _visibility_for_audit(audit), current_user, project_ids
            ):
                content = _HIDDEN_HISTORY_CONTENT
        history.append({"role": item.role, "content": content})
    return history


def _provider_tool_messages(provider: str, call: AIClientToolCall, result: dict) -> list[dict]:
    # Tool continuation roles differ by provider even though execution is provider-neutral.
    content = json.dumps(result, ensure_ascii=False, default=str)
    if provider == "claude":
        return [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": call.tool_id, "name": call.name, "input": call.arguments}
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": call.tool_id, "content": content}
                ],
            },
        ]
    return [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": call.tool_id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": json.dumps(call.arguments, ensure_ascii=False)},
                }
            ],
        },
        {"role": "tool", "tool_call_id": call.tool_id, "content": content},
    ]


def _finish_audit(
    db: Session,
    audit: AIAuditLog,
    *,
    status_value: str,
    response: dict | None = None,
    detail: list[dict] | None = None,
    error_message: str | None = None,
    visibility: dict | None = None,
) -> None:
    response_payload = dict(response or {})
    if visibility is not None:
        response_payload["visibility"] = visibility
    audit.status = status_value
    audit.response_payload = json.dumps(response_payload, ensure_ascii=False)
    audit.detail_payload = json.dumps(detail or [], ensure_ascii=False)
    audit.error_message = error_message
    audit.finished_at = datetime.now()
    audit.updated_at = datetime.now()
    db.commit()


def _persist_running_audit(db: Session, audit: AIAuditLog, detail: list[dict]) -> None:
    audit.detail_payload = json.dumps(detail, ensure_ascii=False)
    audit.updated_at = datetime.now()
    db.commit()


def _terminal_message(
    db: Session,
    *,
    assistant: AIMessage,
    audit: AIAuditLog,
    conversation: AIConversation,
    text: str,
    status_value: str,
    tool_trace: list[dict],
    error_message: str | None = None,
    recovery: dict | None = None,
    visibility: dict | None = None,
) -> tuple[dict, dict]:
    assistant.content = text
    assistant.updated_at = datetime.now()
    conversation.updated_at = datetime.now()
    db.flush()
    response = {"message_id": assistant.id, "length": len(assistant.content), "status": status_value}
    if recovery is not None:
        response["recovery"] = recovery
    _finish_audit(
        db,
        audit,
        status_value=status_value,
        response=response,
        detail=tool_trace,
        error_message=error_message,
        visibility=visibility,
    )
    db.refresh(assistant)
    db.refresh(conversation)
    return serialize_message(assistant, audit), serialize_conversation(conversation)


def _append_message_lifecycle_result(
    db: Session,
    *,
    context: AuditContext | None,
    conversation: AIConversation,
    model_id: int,
    outcome: str,
    status_value: str,
    reason_code: str | None = None,
) -> None:
    if context is None:
        return
    append_audit_event(
        db,
        context=context,
        phase="result",
        action="ai.message.send",
        resource_type="ai_conversation",
        resource_id=conversation.id,
        outcome=outcome,
        reason_code=reason_code,
        after_summary={"model_id": model_id, "status": status_value},
    )


def _safe_audit_error(error: Exception) -> str:
    return str(error)[:1000] if isinstance(error, AIClientError) else "AI 服务暂不可用"


def _tool_argument_repair_instruction(error: AIClientToolArgumentsError) -> dict:
    tool_name = error.tool_name.strip()[:128] or "上一条工具"
    reason = "不是有效 JSON" if error.reason == "invalid_json" else "不是 JSON 对象"
    return {
        "role": "user",
        "content": (
            f"系统校验：工具 {tool_name} 的参数{reason}，本次调用未执行。"
            "请仅重新调用该工具，参数必须是符合工具定义的合法 JSON 对象；"
            "不要编造查询结果或输出参数原文。"
        ),
    }


def _invalid_tool_trace(
    *,
    audit: AIAuditLog,
    iteration: int,
    attempt: int,
    error: AIClientToolArgumentsError,
) -> tuple[dict, dict, dict]:
    audit.tool_call_count += 1
    audit.tool_failed_count += 1
    tool_name = error.tool_name.strip()[:128] or "unknown_tool"
    call_id = f"{audit.id}:{iteration}:invalid:{attempt}"
    trace = {
        "call_id": call_id,
        "sequence": attempt,
        "iteration": iteration,
        "tool_name": tool_name,
        "arguments": {},
        "status": "failed",
        "elapsed_ms": 0,
        "truncated": False,
        "visibility": _known_visibility(),
        "result": {"ok": False, "error": "AI 工具参数格式无效"},
    }
    started = {
        "call_id": call_id,
        "sequence": attempt,
        "iteration": iteration,
        "tool_name": tool_name,
        "arguments": {},
        "status": "running",
    }
    finished = {
        "call_id": call_id,
        "sequence": attempt,
        "iteration": iteration,
        "tool_name": tool_name,
        "status": "failed",
        "elapsed_ms": 0,
        "result": trace["result"],
        "truncated": False,
    }
    return trace, started, finished


def _tool_free_summary_instruction(reason: str) -> dict:
    action = _RECOVERY_BY_REASON[reason]["label"]
    return {
        "role": "system",
        "content": (
            "系统限制：当前回合不能再调用工具。请严格基于已经获得的工具结果回答用户，"
            "不得编造新数据或请求工具。明确说明尚未完成的查询范围，并邀请用户点击“"
            f"{action}”后再继续查询。"
        ),
    }


def stream_message(
    *,
    app: FastAPI,
    db: Session,
    conversation_id: int,
    user_id: int,
    content: str,
    current_user: User | None = None,
    audit_context: AuditContext | None = None,
) -> Iterator[tuple[str, dict]]:
    conversation = _conversation_or_404(db, conversation_id, user_id)
    model = aiCrud.get_model(db, conversation.model_id)
    if model is None or not model.enabled or not model.enable_chat:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前 AI 模型不可用")

    user_message = aiCrud.add_message(
        db,
        AIMessage(conversation_id=conversation.id, role="user", content=content.strip()),
    )
    assistant = aiCrud.add_message(
        db,
        AIMessage(conversation_id=conversation.id, role="assistant", content=""),
    )
    if conversation.title == "新对话":
        conversation.title = content.strip().replace("\n", " ")[:32] or "新对话"
    conversation.updated_at = datetime.now()
    audit = aiCrud.add_audit(
        db,
        AIAuditLog(
            model_id=model.id,
            conversation_id=conversation.id,
            user_id=user_id,
            source="chat",
            source_ref=str(conversation.id),
            request_payload=json.dumps({"content": "[REDACTED]", "length": len(content)}, ensure_ascii=False),
            response_payload=json.dumps({"message_id": assistant.id}, ensure_ascii=False),
            status="running",
            trace_id=(audit_context.trace_id if audit_context is not None else uuid4().hex),
        ),
    )
    if audit_context is not None:
        append_audit_event(
            db,
            context=audit_context,
            phase="attempt",
            action="ai.message.send",
            resource_type="ai_conversation",
            resource_id=conversation.id,
            outcome="success",
            metadata={"model_id": model.id},
        )
    # Persist the recoverable user turn and audit before any SSE bytes leave the process.
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant)
    db.refresh(conversation)
    db.refresh(audit)

    turn_visibility = _historical_visibility(
        db,
        conversation.id,
        exclude_audit_id=audit.id,
    )
    tool_trace: list[dict] = []
    diagnosis_payloads: list[dict] = []
    emitted_text: list[str] = []
    final_text = ""
    confirmation_pending: dict | None = None
    recovery: dict | None = None
    degraded_error_message: str | None = None
    terminal = False
    turn_id = audit.id
    assistant_id = assistant.id
    audit_id = audit.id
    conversation_id = conversation.id
    try:
        yield "user_message", {
            "turn_id": turn_id,
            "message": serialize_message(user_message),
            "conversation": serialize_conversation(conversation),
        }
        yield "accepted", {
            "turn_id": turn_id,
            "audit_id": audit.id,
            "message_id": assistant.id,
            "message": serialize_message(assistant, audit),
            "trace_id": audit.trace_id,
        }
        yield "status", {"turn_id": turn_id, "status": "thinking"}
        # Build from live routes inside the failure boundary so setup failures retain a terminal reply.
        registry = build_tool_registry(app, current_user=current_user)
        tools = tool_definitions(registry, model.provider)
        system_messages = [{"role": "system", "content": model.system_prompt or SYSTEM_PROMPT}]
        if any(item.system_management for item in registry.values()):
            system_messages.append({"role": "system", "content": _SYSTEM_MANAGEMENT_PROMPT})
        messages = [*system_messages, *_history(db, conversation.id, current_user=current_user)]
        # Bound recursive model/tool turns independently of the number of tools per turn.
        max_iterations = int(base_config.get("ai.max_tool_iterations", 4))
        for iteration in range(1, max_iterations + 1):
            completion = None
            repair_attempts = 0
            while True:
                streamed_text: list[str] = []
                try:
                    for event in chat_completion_stream(model, messages, tools=tools):
                        if event.kind == "delta" and event.text:
                            streamed_text.append(event.text)
                            emitted_text.append(event.text)
                            if not diagnosis_payloads:
                                yield "delta", {"turn_id": turn_id, "text": event.text}
                        elif event.kind == "completed":
                            completion = event
                    if completion is None:
                        raise AIClientError("AI 流式响应未正常结束")
                    break
                except AIClientToolArgumentsError as error:
                    repair_attempts += 1
                    trace_entry, started, finished = _invalid_tool_trace(
                        audit=audit,
                        iteration=iteration,
                        attempt=repair_attempts,
                        error=error,
                    )
                    tool_trace.append(trace_entry)
                    _persist_running_audit(db, audit, tool_trace)
                    yield "tool_call_started", {"turn_id": turn_id, **started}
                    yield "tool_call_finished", {"turn_id": turn_id, **finished}
                    if repair_attempts > _MAX_TOOL_ARGUMENT_REPAIRS:
                        recovery = dict(_RECOVERY_BY_REASON["invalid_tool_arguments"])
                        degraded_error_message = "AI 工具参数连续修复失败"
                        break
                    messages.append(_tool_argument_repair_instruction(error))
                    yield "status", {"turn_id": turn_id, "status": "thinking"}
            if recovery is not None:
                break
            calls = completion.tool_calls or []
            if not calls:
                raw_text = "".join(emitted_text) or completion.text or "".join(streamed_text)
                if diagnosis_payloads:
                    final_text = render_restricted_diagnosis(
                        model_text=raw_text,
                        diagnosis=diagnosis_payloads[-1],
                    ).text
                    yield "delta", {"turn_id": turn_id, "text": final_text}
                else:
                    final_text = raw_text
                break
            for sequence, call in enumerate(calls, start=1):
                audit.tool_call_count += 1
                call_id = f"{audit.id}:{iteration}:{sequence}"
                trace_entry = {
                    "call_id": call_id,
                    "sequence": sequence,
                    "iteration": iteration,
                    "tool_name": call.name,
                    "arguments": _redact_sensitive(_json_safe(call.arguments)),
                    "status": "running",
                    "elapsed_ms": None,
                    "truncated": False,
                }
                tool_trace.append(trace_entry)
                _persist_running_audit(db, audit, tool_trace)
                yield "tool_call_started", {
                    "turn_id": turn_id,
                    "call_id": call_id,
                    "sequence": sequence,
                    "iteration": iteration,
                    "tool_name": call.name,
                    "arguments": trace_entry["arguments"],
                    "status": "running",
                }
                started_at = monotonic()
                if ai_quota_confirmation_service.is_quota_write_tool(call.name):
                    try:
                        confirmation_pending = ai_quota_confirmation_service.prepare_confirmation(
                            db,
                            definition=registry[call.name],
                            arguments=call.arguments,
                            user_id=user_id,
                            conversation_id=conversation.id,
                            audit=audit,
                        )
                        result = {"ok": True, "data": {"confirmation_required": confirmation_pending}}
                    except HTTPException as error:
                        result = {"ok": False, "error": str(error.detail)}
                else:
                    result = execute_tool(
                        app=app,
                        registry=registry,
                        tool_name=call.name,
                        arguments=call.arguments,
                        user_id=user_id,
                        current_user=current_user,
                    )
                if (
                    call.name == "get_incident_diagnosis"
                    and result.get("ok") is True
                    and isinstance(result.get("data"), dict)
                ):
                    diagnosis_payloads.append(result["data"])
                elapsed_ms = max(0, round((monotonic() - started_at) * 1000))
                if result.get("ok") is False:
                    audit.tool_failed_count += 1
                display_result, truncated = _display_tool_result(result)
                definition = registry.get(call.name)
                # Review fix: unknown provider tool names must complete as safe failed calls.
                visibility = (
                    _tool_visibility(db, definition, call.arguments, result)
                    if definition is not None
                    else _unknown_visibility()
                )
                trace_entry.update(
                    {
                        "status": "failed" if result.get("ok") is False else (
                            "awaiting_confirmation" if confirmation_pending is not None else "succeeded"
                        ),
                        "elapsed_ms": elapsed_ms,
                        "result": display_result,
                        "truncated": truncated,
                        "visibility": visibility,
                    }
                )
                _persist_running_audit(db, audit, tool_trace)
                yield "tool_call_finished", {
                    "turn_id": turn_id,
                    "call_id": call_id,
                    "sequence": sequence,
                    "iteration": iteration,
                    "tool_name": call.name,
                    "status": trace_entry["status"],
                    "elapsed_ms": elapsed_ms,
                    "result": display_result,
                    "truncated": truncated,
                }
                if confirmation_pending is not None:
                    yield "quota_confirmation_required", {
                        "turn_id": turn_id,
                        "tool_name": call.name,
                        **confirmation_pending,
                    }
                    final_text = "配额调整已生成安全预览，请在五分钟内确认或取消。"
                    break
                messages.extend(_provider_tool_messages(model.provider, call, result))
                if call.name == "get_incident_diagnosis" and result.get("ok") is True:
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                "诊断工具结果是唯一事实来源。仅返回 JSON 对象，字段必须是 "
                                "incident_id、confidence、candidates、evidence_ids、data_gaps；"
                                "不得增加、删除或改写候选、分数、证据 ID、数据缺口或置信度。"
                            ),
                        }
                    )
            if confirmation_pending is not None:
                break
            yield "status", {"turn_id": turn_id, "status": "thinking"}
        else:
            recovery = dict(_RECOVERY_BY_REASON["tool_iteration_limit"])
            degraded_error_message = "已达到 AI 工具调用轮次上限"

        if recovery is not None:
            summary_text: list[str] = []
            try:
                if not diagnosis_payloads:
                    summary_completion = None
                    summary_messages = [*messages, _tool_free_summary_instruction(recovery["reason"])]
                    for event in chat_completion_stream(model, summary_messages, tools=[]):
                        if event.kind == "delta" and event.text:
                            summary_text.append(event.text)
                            yield "delta", {"turn_id": turn_id, "text": event.text}
                        elif event.kind == "completed":
                            summary_completion = event
                    if not summary_text and summary_completion is not None and summary_completion.text:
                        summary_text.append(summary_completion.text)
            except Exception:
                degraded_error_message = f"{degraded_error_message}；无工具总结调用失败"
            if diagnosis_payloads:
                final_text = render_restricted_diagnosis(
                    model_text="".join(summary_text), diagnosis=diagnosis_payloads[-1]
                ).text
                yield "delta", {"turn_id": turn_id, "text": final_text}
            else:
                final_text = "".join(summary_text).strip() or _DEGRADED_FALLBACKS[recovery["reason"]]
            _append_message_lifecycle_result(
                db,
                context=audit_context,
                conversation=conversation,
                model_id=model.id,
                outcome="failure",
                status_value="degraded",
                reason_code=recovery["reason"],
            )
            message_data, conversation_data = _terminal_message(
                db,
                assistant=assistant,
                audit=audit,
                conversation=conversation,
                text=final_text,
                status_value="degraded",
                tool_trace=tool_trace,
                error_message=degraded_error_message,
                recovery=recovery,
                visibility=_combine_visibility(turn_visibility, _visibility_from_trace_entries(tool_trace)),
            )
            terminal = True
            yield "completed", {
                "turn_id": turn_id,
                "message": message_data,
                "conversation": conversation_data,
                "audit_id": audit.id,
            }
            return

        if confirmation_pending is not None:
            message_data, conversation_data = _terminal_message(
                db,
                assistant=assistant,
                audit=audit,
                conversation=conversation,
                text=final_text,
                status_value="awaiting_confirmation",
                tool_trace=tool_trace,
                visibility=_combine_visibility(turn_visibility, _visibility_from_trace_entries(tool_trace)),
            )
            terminal = True
            yield "completed", {
                "turn_id": turn_id,
                "message": message_data,
                "conversation": conversation_data,
                "audit_id": audit.id,
            }
            return

        if not final_text.strip():
            raise AIClientError("AI 服务返回空内容")
        _append_message_lifecycle_result(
            db,
            context=audit_context,
            conversation=conversation,
            model_id=model.id,
            outcome="success",
            status_value="succeeded",
        )
        message_data, conversation_data = _terminal_message(
            db,
            assistant=assistant,
            audit=audit,
            conversation=conversation,
            text=final_text.strip(),
            status_value="succeeded",
            tool_trace=tool_trace,
            visibility=_combine_visibility(turn_visibility, _visibility_from_trace_entries(tool_trace)),
        )
        terminal = True
        yield "completed", {
            "turn_id": turn_id,
            "message": message_data,
            "conversation": conversation_data,
            "audit_id": audit.id,
        }
    except GeneratorExit:
        if not terminal:
            _append_message_lifecycle_result(
                db,
                context=audit_context,
                conversation=conversation,
                model_id=model.id,
                outcome="failure",
                status_value="cancelled",
                reason_code="cancelled",
            )
            _terminal_message(
                db,
                assistant=assistant,
                audit=audit,
                conversation=conversation,
                text="".join(emitted_text),
                status_value="cancelled",
                tool_trace=tool_trace,
                error_message="用户取消生成",
                visibility=_combine_visibility(turn_visibility, _visibility_from_trace_entries(tool_trace)),
            )
        raise
    except asyncio.CancelledError:
        _append_message_lifecycle_result(
            db,
            context=audit_context,
            conversation=conversation,
            model_id=model.id,
            outcome="failure",
            status_value="cancelled",
            reason_code="cancelled",
        )
        message_data, conversation_data = _terminal_message(
            db,
            assistant=assistant,
            audit=audit,
            conversation=conversation,
            text="".join(emitted_text),
            status_value="cancelled",
            tool_trace=tool_trace,
            error_message="用户取消生成",
            visibility=_combine_visibility(turn_visibility, _visibility_from_trace_entries(tool_trace)),
        )
        terminal = True
        yield "cancelled", {
            "turn_id": turn_id,
            "message": message_data,
            "conversation": conversation_data,
            "audit_id": audit.id,
        }
    except Exception as error:
        # A failed flush poisons the Session; reload the durable audit after rollback.
        db.rollback()
        audit = aiCrud.get_audit(db, audit_id)
        assistant = db.get(AIMessage, assistant_id)
        conversation = aiCrud.get_conversation(db, conversation_id, user_id)
        if audit is not None and assistant is not None and conversation is not None:
            _append_message_lifecycle_result(
                db,
                context=audit_context,
                conversation=conversation,
                model_id=model.id,
                outcome="failure",
                status_value="failed",
                reason_code="ai_message_failed",
            )
            message_data, conversation_data = _terminal_message(
                db,
                assistant=assistant,
                audit=audit,
                conversation=conversation,
                text="".join(emitted_text) or _FAILED_RESPONSE,
                status_value="failed",
                tool_trace=tool_trace,
                error_message=_safe_audit_error(error),
                visibility=_combine_visibility(turn_visibility, _visibility_from_trace_entries(tool_trace)),
            )
            terminal = True
            yield "error", {
                "turn_id": turn_id,
                "message": message_data,
                "conversation": conversation_data,
                "audit_id": audit_id,
                "error": str(error) if isinstance(error, AIClientError) else "AI 服务暂不可用",
            }


def send_message(**kwargs) -> dict:
    completed = None
    error = None
    for event, data in stream_message(**kwargs):
        if event == "completed":
            completed = data
        elif event == "error":
            error = data.get("message")
    if completed is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error or "AI 服务未返回结果")
    return completed
