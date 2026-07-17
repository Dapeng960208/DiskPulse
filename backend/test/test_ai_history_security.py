# -*- coding: utf-8 -*-
import json
from uuid import uuid4

from fastapi import APIRouter, FastAPI

import models
from services import ai_audit_service, ai_chat_service
from services.ai_client import AIClientToolCall, AICompletionStreamEvent
from services.audit_service import AuditContext


HIDDEN_HISTORY_CONTENT = "该历史回复关联的项目权限已失效，内容已隐藏。"


def _seed_conversation(db_session):
    user = models.User(id=1, rd_username="reader", username="Reader")
    model = models.AIConfig(id=1, name="test-model", model="test-model", enabled=True)
    conversation = models.AIConversation(id=1, user_id=user.id, model_id=model.id, title="历史会话")
    db_session.add_all([user, model, conversation])
    db_session.commit()
    return user, model, conversation


def _add_assistant_turn(db_session, conversation, *, response_payload, detail_payload, content):
    message = models.AIMessage(conversation_id=conversation.id, role="assistant", content=content)
    db_session.add(message)
    db_session.flush()
    audit = models.AIAuditLog(
        model_id=conversation.model_id,
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        source="chat",
        source_ref=str(conversation.id),
        request_payload=json.dumps({"content": "[REDACTED]"}),
        response_payload=json.dumps({"message_id": message.id, **response_payload}),
        detail_payload=json.dumps(detail_payload),
        status="succeeded",
        trace_id="audit-trace",
    )
    db_session.add(audit)
    db_session.commit()
    return message, audit


def test_revoked_project_membership_hides_persisted_ai_turn_and_tool_result(db_session):
    user, _model, conversation = _seed_conversation(db_session)
    project = models.Project(id=1, name="revoked-project")
    membership = models.ProjectMembership(project_id=project.id, user_id=user.id, role="reader")
    db_session.add_all([project, membership])
    db_session.commit()
    _add_assistant_turn(
        db_session,
        conversation,
        content="revoked-project 的用量为 42 GiB",
        response_payload={
            "visibility": {
                "known": True,
                "project_scope_ids": [project.id],
                "requires_super_admin": False,
            }
        },
        detail_payload=[
            {
                "tool_name": "get_project",
                "visibility": {
                    "known": True,
                    "project_scope_ids": [project.id],
                    "requires_super_admin": False,
                },
                "result": {"ok": True, "data": {"id": project.id, "name": "revoked-project"}},
            }
        ],
    )
    db_session.delete(membership)
    db_session.commit()

    history = ai_chat_service.get_conversation(db_session, conversation.id, user.id)
    assistant = history["messages"][-1]

    assert assistant["status"] == "restricted"
    assert assistant["content"] == HIDDEN_HISTORY_CONTENT
    assert assistant["tool_calls"] == []


def test_legacy_ai_trace_without_visibility_metadata_is_hidden_safely(db_session):
    user, _model, conversation = _seed_conversation(db_session)
    _add_assistant_turn(
        db_session,
        conversation,
        content="历史项目数据",
        response_payload={},
        detail_payload=[
            {
                "tool_name": "list_groups",
                "result": {"ok": True, "data": {"items": [{"project_id": 1, "name": "secret"}]}},
            }
        ],
    )

    history = ai_chat_service.get_conversation(db_session, conversation.id, user.id)
    assistant = history["messages"][-1]

    assert assistant["status"] == "restricted"
    assert assistant["content"] == HIDDEN_HISTORY_CONTENT
    assert assistant["tool_calls"] == []


def test_ai_audit_trace_inherits_request_trace_id_before_generating_a_new_one(db_session, monkeypatch):
    user, _model, conversation = _seed_conversation(db_session)

    def completed_stream(*_args, **_kwargs):
        yield AICompletionStreamEvent(kind="delta", text="已完成")
        yield AICompletionStreamEvent(kind="completed", text="已完成", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", completed_stream)
    context = AuditContext(request_id=uuid4(), trace_id=uuid4(), operation_id=uuid4(), actor_user_id=user.id)

    list(
        ai_chat_service.stream_message(
            app=FastAPI(),
            db=db_session,
            conversation_id=conversation.id,
            user_id=user.id,
            current_user=user,
            content="生成安全摘要",
            audit_context=context,
        )
    )

    audit = db_session.query(models.AIAuditLog).filter_by(conversation_id=conversation.id).one()
    assert audit.trace_id == context.trace_id


def test_tool_trace_persists_visibility_and_redacts_sensitive_values(db_session, monkeypatch):
    user, _model, conversation = _seed_conversation(db_session)
    app = FastAPI()
    router = APIRouter()

    @router.get(
        "/projects/{project_id}",
        openapi_extra={"ai_exposed": True, "ai_name": "get_project", "ai_description": "查询项目"},
    )
    def get_project(project_id: int, prompt: str = "", token: str = "", path: str = ""):
        return {
            "id": project_id,
            "safe": "visible",
            "linux_path": "/secure/project/private",
            "token": "result-token",
            "password": "result-password",
            "raw_response": "device-original-response",
            "nested": {"path": "C:\\secure\\private"},
        }

    app.include_router(router)
    calls = {"count": 0}

    def provider_stream(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            yield AICompletionStreamEvent(
                kind="completed",
                tool_calls=[
                    AIClientToolCall(
                        tool_id="tool-1",
                        name="get_project",
                        arguments={
                            "project_id": 7,
                            "prompt": "original user prompt",
                            "token": "argument-token",
                            "path": "/secure/input/path",
                        },
                    )
                ],
                stop_reason="tool_calls",
            )
            return
        yield AICompletionStreamEvent(kind="delta", text="查询完成")
        yield AICompletionStreamEvent(kind="completed", text="查询完成", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)
    list(
        ai_chat_service.stream_message(
            app=app,
            db=db_session,
            conversation_id=conversation.id,
            user_id=user.id,
            current_user=user,
            content="请查询项目",
        )
    )

    audit = db_session.query(models.AIAuditLog).filter_by(conversation_id=conversation.id).one()
    persisted = json.dumps(json.loads(audit.detail_payload), ensure_ascii=False)
    for secret in (
        "original user prompt",
        "argument-token",
        "/secure/input/path",
        "/secure/project/private",
        "result-token",
        "result-password",
        "device-original-response",
        "C:\\secure\\private",
    ):
        assert secret not in persisted
    trace = json.loads(audit.detail_payload)[0]
    assert trace["visibility"] == {
        "known": True,
        "project_scope_ids": [7],
        "requires_super_admin": False,
    }
    assert trace["result"]["data"]["safe"] == "visible"


def test_admin_ai_audit_read_redacts_legacy_prompt_response_path_and_secret(db_session):
    user, _model, conversation = _seed_conversation(db_session)
    _message, audit = _add_assistant_turn(
        db_session,
        conversation,
        content="安全内容",
        response_payload={"raw_response": "provider-original-response"},
        detail_payload=[
            {
                "prompt": "legacy raw prompt",
                "path": "/legacy/private/path",
                "token": "legacy-token",
                "response": "device-original-response",
            }
        ],
    )
    audit.request_payload = json.dumps({"prompt": "legacy raw prompt"})
    audit.error_message = "device-original-response"
    db_session.commit()

    result = ai_audit_service.get_audit(db_session, audit.id)
    returned = json.dumps(result, ensure_ascii=False, default=str)

    for secret in (
        "legacy raw prompt",
        "/legacy/private/path",
        "legacy-token",
        "provider-original-response",
        "device-original-response",
    ):
        assert secret not in returned
    assert result["request"]["prompt"] == "[REDACTED]"
    assert result["response"]["raw_response"] == "[REDACTED]"
    assert result["detail"][0]["path"] == "[REDACTED]"
