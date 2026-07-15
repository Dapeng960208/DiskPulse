# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
import json
from typing import Iterator
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from appConfig import base_config
from crud import aiCrud
from models import AIConversation, AIAuditLog, AIMessage
from services.ai_client import AIClientError, AIClientToolCall, chat_completion_stream
from services.ai_config_service import serialize_model
from services.ai_tool_service import build_tool_registry, execute_tool, tool_definitions


SYSTEM_PROMPT = """你是 DiskPulse AI 助手。你只能使用已授权的只读工具查询数据。
不得编造工具结果，不得请求或泄露密码、令牌、密钥及个人敏感信息。
回答应简洁、准确，并在数据不足时明确说明。"""


def serialize_message(message: AIMessage) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
    }


def serialize_conversation(conversation: AIConversation, *, include_messages: bool = False) -> dict:
    data = {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "model_id": conversation.model_id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }
    if include_messages:
        data["messages"] = [serialize_message(message) for message in conversation.messages]
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
    return serialize_conversation(conversation, include_messages=True)


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
    rows = list(
        db.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.id.desc())
            .limit(20)
        )
    )
    return [{"role": item.role, "content": item.content} for item in reversed(rows)]


def _provider_tool_messages(provider: str, call: AIClientToolCall, result: dict) -> list[dict]:
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
            response_payload="{}",
            status="running",
            trace_id=uuid4().hex,
        ),
    )
    db.commit()
    db.refresh(user_message)
    db.refresh(conversation)
    db.refresh(audit)

    registry = build_tool_registry(app)
    tools = tool_definitions(registry, model.provider)
    messages = [{"role": "system", "content": model.system_prompt or SYSTEM_PROMPT}, *_history(db, conversation.id)]
    tool_trace: list[dict] = []
    final_text = ""
    try:
        yield "accepted", {"conversation_id": conversation.id, "audit_id": audit.id, "trace_id": audit.trace_id}
        yield "user_message", {"message": serialize_message(user_message), "conversation": serialize_conversation(conversation)}
        yield "status", {"status": "thinking"}
        max_iterations = int(base_config.get("ai.max_tool_iterations", 4))
        for iteration in range(1, max_iterations + 1):
            completion = None
            streamed_text: list[str] = []
            for event in chat_completion_stream(model, messages, tools=tools):
                if event.kind == "delta" and event.text:
                    streamed_text.append(event.text)
                    yield "delta", {"text": event.text}
                elif event.kind == "completed":
                    completion = event
            if completion is None:
                raise AIClientError("AI 流式响应未正常结束")
            calls = completion.tool_calls or []
            if not calls:
                final_text = completion.text or "".join(streamed_text)
                break
            for sequence, call in enumerate(calls, start=1):
                audit.tool_call_count += 1
                yield "tool_call_started", {
                    "sequence": sequence,
                    "iteration": iteration,
                    "tool_name": call.name,
                }
                result = execute_tool(
                    app=app,
                    registry=registry,
                    tool_name=call.name,
                    arguments=call.arguments,
                    user_id=user_id,
                )
                if not result.get("ok"):
                    audit.tool_failed_count += 1
                tool_trace.append({"tool_name": call.name, "ok": bool(result.get("ok"))})
                yield "tool_call_finished", {
                    "sequence": sequence,
                    "iteration": iteration,
                    "tool_name": call.name,
                    "status": "succeeded" if result.get("ok") else "failed",
                }
                messages.extend(_provider_tool_messages(model.provider, call, result))
            yield "status", {"status": "thinking"}
        else:
            raise AIClientError("AI 工具调用轮次超过限制")

        if not final_text.strip():
            raise AIClientError("AI 服务返回空内容")
        assistant = aiCrud.add_message(
            db,
            AIMessage(conversation_id=conversation.id, role="assistant", content=final_text.strip()),
        )
        conversation.updated_at = datetime.now()
        db.flush()
        _finish_audit(
            db,
            audit,
            status_value="succeeded",
            response={"message_id": assistant.id, "length": len(assistant.content)},
            detail=tool_trace,
        )
        db.refresh(assistant)
        db.refresh(conversation)
        yield "completed", {
            "message": serialize_message(assistant),
            "conversation": serialize_conversation(conversation),
            "audit_id": audit.id,
        }
    except GeneratorExit:
        _finish_audit(db, audit, status_value="cancelled", detail=tool_trace, error_message="用户取消生成")
        raise
    except asyncio.CancelledError:
        _finish_audit(db, audit, status_value="cancelled", detail=tool_trace, error_message="用户取消生成")
        yield "cancelled", {"conversation_id": conversation.id, "audit_id": audit.id}
    except Exception as error:
        db.rollback()
        audit = aiCrud.get_audit(db, audit.id)
        if audit is not None:
            _finish_audit(db, audit, status_value="failed", detail=tool_trace, error_message=str(error)[:1000])
        yield "error", {"message": str(error) if isinstance(error, AIClientError) else "AI 服务暂不可用"}


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
