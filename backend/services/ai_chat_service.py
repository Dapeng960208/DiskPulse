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
from models import AIConversation, AIAuditLog, AIMessage
from services.ai_client import AIClientError, AIClientToolArgumentsError, AIClientToolCall, chat_completion_stream
from services.ai_config_service import serialize_model
from services.ai_tool_service import build_tool_registry, execute_tool, tool_definitions


SYSTEM_PROMPT = """你是 DiskPulse AI 助手。你只能使用已授权的只读工具查询数据。
不得编造工具结果，不得请求或泄露密码、令牌、密钥及个人敏感信息。
回答应简洁、准确，并在数据不足时明确说明。"""

_DISPLAY_TOOL_RESULT_LIMIT_BYTES = 32 * 1024
_FAILED_RESPONSE = "抱歉，AI 服务暂时不可用，请稍后重试。"
_MAX_TOOL_ARGUMENT_REPAIRS = 2
_RECOVERY_BY_REASON = {
    "tool_iteration_limit": {"reason": "tool_iteration_limit", "action": "continue", "label": "继续查询"},
    "invalid_tool_arguments": {"reason": "invalid_tool_arguments", "action": "retry", "label": "重新查询"},
}
_DEGRADED_FALLBACKS = {
    "tool_iteration_limit": "本轮已达到工具查询上限。我已保留已完成的查询结果；如需补充信息，请授权继续查询。",
    "invalid_tool_arguments": "本轮工具参数多次无效，无法继续执行查询。我已保留当前可用信息；请重新查询。",
}


def _json_safe(value: object) -> object:
    """Convert tool output to JSON-compatible values before it reaches the client/audit."""
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return str(value)


def _redact_sensitive(value: object) -> object:
    sensitive_names = {"password", "secret", "token", "api_key", "apikey", "authorization", "credential"}
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if any(name in str(key).lower() for name in sensitive_names)
                else _redact_sensitive(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value


def _display_tool_result(result: object) -> tuple[object, bool]:
    """Keep a bounded, valid display copy without changing provider-facing tool output."""
    safe = _redact_sensitive(_json_safe(result))
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
    return metadata


def serialize_message(message: AIMessage, audit: AIAuditLog | None = None) -> dict:
    data = {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
    }
    if message.role == "assistant":
        if audit is None:
            data.update({"status": "succeeded", "tool_calls": []})
        else:
            data.update(_message_turn_metadata(message, {message.id: audit}))
    return data


def serialize_conversation(
    conversation: AIConversation,
    *,
    include_messages: bool = False,
    audits_by_message: dict[int, AIAuditLog] | None = None,
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
        data["messages"] = [
            {
                **serialize_message(message),
                **(_message_turn_metadata(message, audits_by_message) if message.role == "assistant" else {}),
            }
            for message in conversation.messages
        ]
    return data


def list_available_models(db: Session) -> list[dict]:
    return [serialize_model(item) for item in aiCrud.list_models(db, available_only=True)]


def list_conversations(db: Session, user_id: int) -> list[dict]:
    return [serialize_conversation(item) for item in aiCrud.list_conversations(db, user_id)]


def create_conversation(db: Session, user_id: int, title: str, model_id: int) -> dict:
    model = aiCrud.get_model(db, model_id)
    if model is None or not model.enabled or not model.enable_chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="可用 AI 模型不存在")
    conversation = aiCrud.add_conversation(
        db,
        AIConversation(user_id=user_id, model_id=model_id, title=title.strip() or "新对话"),
    )
    db.commit()
    db.refresh(conversation)
    return serialize_conversation(conversation)


def get_conversation(db: Session, conversation_id: int, user_id: int) -> dict:
    conversation = _conversation_or_404(db, conversation_id, user_id)
    audits_by_message = {}
    for audit in aiCrud.list_conversation_audits(db, conversation.id):
        response = _audit_payload(audit.response_payload, {})
        message_id = response.get("message_id") if isinstance(response, dict) else None
        if isinstance(message_id, int):
            audits_by_message[message_id] = audit
    return serialize_conversation(
        conversation,
        include_messages=True,
        audits_by_message=audits_by_message,
    )


def delete_conversation(db: Session, conversation_id: int, user_id: int) -> None:
    conversation = _conversation_or_404(db, conversation_id, user_id)
    db.delete(conversation)
    db.commit()


def _conversation_or_404(db: Session, conversation_id: int, user_id: int) -> AIConversation:
    conversation = aiCrud.get_conversation(db, conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 会话不存在")
    return conversation


def _history(db: Session, conversation_id: int) -> list[dict]:
    # Fetch the newest bounded window cheaply, then restore provider-facing chronology.
    rows = list(
        db.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.id.desc())
            .limit(20)
        )
    )
    return [
        {"role": item.role, "content": item.content}
        for item in reversed(rows)
        # The current turn reserves an empty assistant row before streaming; it is not provider history.
        if item.role != "assistant" or item.content.strip()
    ]


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
) -> None:
    audit.status = status_value
    audit.response_payload = json.dumps(response or {}, ensure_ascii=False)
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
    )
    db.refresh(assistant)
    db.refresh(conversation)
    return serialize_message(assistant, audit), serialize_conversation(conversation)


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
            trace_id=uuid4().hex,
        ),
    )
    # Persist the recoverable user turn and audit before any SSE bytes leave the process.
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant)
    db.refresh(conversation)
    db.refresh(audit)

    tool_trace: list[dict] = []
    emitted_text: list[str] = []
    final_text = ""
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
        registry = build_tool_registry(app)
        tools = tool_definitions(registry, model.provider)
        messages = [{"role": "system", "content": model.system_prompt or SYSTEM_PROMPT}, *_history(db, conversation.id)]
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
                final_text = "".join(emitted_text) or completion.text or "".join(streamed_text)
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
                result = execute_tool(
                    app=app,
                    registry=registry,
                    tool_name=call.name,
                    arguments=call.arguments,
                    user_id=user_id,
                )
                elapsed_ms = max(0, round((monotonic() - started_at) * 1000))
                if not result.get("ok"):
                    audit.tool_failed_count += 1
                display_result, truncated = _display_tool_result(result)
                trace_entry.update(
                    {
                        "status": "succeeded" if result.get("ok") else "failed",
                        "elapsed_ms": elapsed_ms,
                        "result": display_result,
                        "truncated": truncated,
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
                messages.extend(_provider_tool_messages(model.provider, call, result))
            yield "status", {"turn_id": turn_id, "status": "thinking"}
        else:
            recovery = dict(_RECOVERY_BY_REASON["tool_iteration_limit"])
            degraded_error_message = "已达到 AI 工具调用轮次上限"

        if recovery is not None:
            summary_text: list[str] = []
            try:
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
            final_text = "".join(summary_text).strip() or _DEGRADED_FALLBACKS[recovery["reason"]]
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
        message_data, conversation_data = _terminal_message(
            db,
            assistant=assistant,
            audit=audit,
            conversation=conversation,
            text=final_text.strip(),
            status_value="succeeded",
            tool_trace=tool_trace,
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
            _terminal_message(
                db,
                assistant=assistant,
                audit=audit,
                conversation=conversation,
                text="".join(emitted_text),
                status_value="cancelled",
                tool_trace=tool_trace,
                error_message="用户取消生成",
            )
        raise
    except asyncio.CancelledError:
        message_data, conversation_data = _terminal_message(
            db,
            assistant=assistant,
            audit=audit,
            conversation=conversation,
            text="".join(emitted_text),
            status_value="cancelled",
            tool_trace=tool_trace,
            error_message="用户取消生成",
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
            message_data, conversation_data = _terminal_message(
                db,
                assistant=assistant,
                audit=audit,
                conversation=conversation,
                text="".join(emitted_text) or _FAILED_RESPONSE,
                status_value="failed",
                tool_trace=tool_trace,
                error_message=_safe_audit_error(error),
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
