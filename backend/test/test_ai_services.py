# -*- coding: utf-8 -*-
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from sqlalchemy import select

from appConfig import base_config
from models import AIConfig, AIConversation, AIAuditLog, AIMessage, User
from routers import ai, ai_admin
from services import ai_audit_service, ai_chat_service, ai_client
from services.ai_client import AIClientError, AIClientToolArgumentsError, AIClientToolCall, AICompletionStreamEvent
from services.ai_security import encrypt_secret
from services.ai_security import decrypt_secret, mask_secret
from services.ai_tool_service import build_tool_registry, execute_tool, tool_definitions, _unwrap
from utils.security import issue_token


class FakeResponse:
    def __init__(self, body=None, *, status_code=200, lines=None):
        self.body = body or {}
        self.status_code = status_code
        self.lines = lines or []
        self.request = httpx.Request("POST", "https://ai.example.com")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "provider error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        return self.body

    def iter_lines(self):
        return iter(self.lines)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def model(provider="openai", *, encrypted_key=""):
    return SimpleNamespace(
        provider=provider,
        base_url="https://ai.example.com",
        api_key_encrypted=encrypted_key,
        model="model-test",
        temperature=0.4,
        max_tokens=512,
    )


def seed_user(db, *, user_id=1, username="reader"):
    user = User(id=user_id, username=username, rd_username=username, email=f"{username}@example.com")
    db.add(user)
    db.commit()
    return user


def seed_model(db, *, actor_id=1, provider="openai"):
    item = AIConfig(
        name=f"{provider}-model",
        provider=provider,
        base_url="https://ai.example.com",
        api_key_encrypted="",
        model="model-test",
        enabled=True,
        enable_chat=True,
        temperature=0.3,
        max_tokens=512,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_list_audits_includes_safe_display_summaries(db_session):
    user = seed_user(db_session, username="alice")
    configured = seed_model(db_session, actor_id=user.id)
    conversation = AIConversation(user_id=user.id, model_id=configured.id, title="容量风险排查")
    db_session.add(conversation)
    db_session.flush()
    db_session.add(AIAuditLog(
        model_id=configured.id,
        conversation_id=conversation.id,
        user_id=user.id,
        source="chat",
        source_ref=str(conversation.id),
        tool_call_count=2,
        tool_failed_count=0,
        detail_payload=json.dumps([
            {"tool_name": "list_projects"},
            {"tool_name": "get_project"},
            {"tool_name": "list_projects"},
        ]),
        status="succeeded",
    ))
    db_session.commit()

    result = ai_audit_service.list_audits(db_session, page=1, size=20)

    assert result["content"][0]["conversation"] == {"id": conversation.id, "title": "容量风险排查"}
    assert result["content"][0]["user"] == {"id": user.id, "rd_username": "alice", "username": "alice"}
    assert result["content"][0]["model"] == {"id": configured.id, "name": "openai-model", "model": "model-test"}
    assert result["content"][0]["tool_names"] == ["list_projects", "get_project"]


def test_openai_and_claude_non_streaming_payloads(monkeypatch):
    seen = []

    def post(url, **kwargs):
        seen.append((url, kwargs))
        if url.endswith("/v1/messages"):
            return FakeResponse({
                "content": [
                    {"type": "text", "text": "分析中"},
                    {"type": "tool_use", "id": "c1", "name": "lookup", "input": {"id": 2}},
                ],
            })
        return FakeResponse({
            "choices": [{
                "message": {
                    "content": "查询中",
                    "tool_calls": [{
                        "id": "o1",
                        "function": {"name": "lookup", "arguments": '{"id": 1}'},
                    }],
                },
            }],
        })

    monkeypatch.setattr(ai_client.httpx, "post", post)
    openai_result = ai_client.chat_completion(
        model(),
        [{"role": "system", "content": "system"}, {"role": "user", "content": "question"}],
        tools=[{"type": "function"}],
    )
    claude_result = ai_client.chat_completion(
        model("claude"),
        [{"role": "system", "content": "system"}, {"role": "user", "content": "question"}],
        tools=[{"name": "lookup"}],
    )

    assert openai_result.tool_calls[0].arguments == {"id": 1}
    assert claude_result.tool_calls[0].arguments == {"id": 2}
    assert seen[0][1]["json"]["tool_choice"] == "auto"
    assert seen[1][1]["json"]["system"] == "system"
    assert seen[1][1]["json"]["messages"] == [{"role": "user", "content": "question"}]


def test_provider_errors_are_safe(monkeypatch):
    monkeypatch.setattr(ai_client.httpx, "post", lambda *_args, **_kwargs: FakeResponse(status_code=401))
    with pytest.raises(AIClientError, match="HTTP 401"):
        ai_client.chat_completion(model(), [{"role": "user", "content": "hello"}])

    def timeout(*_args, **_kwargs):
        raise httpx.TimeoutException("secret upstream detail")

    monkeypatch.setattr(ai_client.httpx, "post", timeout)
    with pytest.raises(AIClientError, match="请求超时"):
        ai_client.chat_completion(model(), [{"role": "user", "content": "hello"}])

    monkeypatch.setattr(
        ai_client.httpx,
        "post",
        lambda *_args, **_kwargs: FakeResponse({"choices": [{"message": {"content": "", "tool_calls": []}}]}),
    )
    with pytest.raises(AIClientError, match="空内容"):
        ai_client.chat_completion(model(), [{"role": "user", "content": "hello"}])
    with pytest.raises(AIClientError, match="有效 JSON"):
        ai_client._decode_arguments("not-json")
    with pytest.raises(AIClientError, match="必须是对象"):
        ai_client._decode_arguments([])


def test_provider_headers_and_default_urls(monkeypatch):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    encrypted = encrypt_secret("provider-secret")
    assert ai_client._headers(model(encrypted_key=encrypted))["Authorization"] == "Bearer provider-secret"
    assert ai_client._headers(model("claude", encrypted_key=encrypted))["x-api-key"] == "provider-secret"
    assert ai_client._base_url(SimpleNamespace(provider="openrouter", base_url="https://router.example.com")) == "https://router.example.com/api/v1"
    assert ai_client._base_url(SimpleNamespace(provider="ollama", base_url="")) == "http://localhost:11434/v1"


def test_secret_failure_paths_are_safe():
    base_config.set("ai.config_secret_key", "short")
    with pytest.raises(RuntimeError, match="independent"):
        encrypt_secret("secret")
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""
    assert decrypt_secret("plaintext") == ""
    assert decrypt_secret("fernet::invalid") == ""
    assert mask_secret("") == ""
    assert mask_secret("short") == "****"


def test_openai_and_claude_stream_parsing(monkeypatch):
    openai_lines = [
        'data: {"choices":[{"delta":{"content":"容量"}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"t1","function":{"name":"look","arguments":"{\\"id\\":"}}]}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"up","arguments":"2}"}}]}}]}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(ai_client.httpx, "stream", lambda *_args, **_kwargs: FakeResponse(lines=openai_lines))
    events = list(ai_client.chat_completion_stream(model(), [{"role": "user", "content": "q"}], tools=[]))
    assert events[0].text == "容量"
    assert events[-1].tool_calls[0].name == "lookup"
    assert events[-1].tool_calls[0].arguments == {"id": 2}

    claude_lines = [
        'event: content_block_start',
        'data: {"type":"content_block_start","index":0,"content_block":{"type":"tool_use","id":"c1","name":"lookup","input":{}}}',
        'data: {"type":"content_block_delta","index":1,"delta":{"type":"text_delta","text":"完成"}}',
        'data: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"{\\"id\\":3}"}}',
        'data: {"type":"message_stop"}',
    ]
    monkeypatch.setattr(ai_client.httpx, "stream", lambda *_args, **_kwargs: FakeResponse(lines=claude_lines))
    events = list(ai_client.chat_completion_stream(model("claude"), [{"role": "user", "content": "q"}], tools=[]))
    assert events[0].text == "完成"
    assert events[-1].tool_calls[0].arguments == {"id": 3}


@pytest.mark.parametrize(
    ("provider", "lines", "reason"),
    [
        (
            "openai",
            [
                'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"empty-openai","function":{"name":"lookup","arguments":""}}]}}]}',
                "data: [DONE]",
            ],
            "invalid_json",
        ),
        (
            "claude",
            [
                'data: {"type":"content_block_start","index":0,"content_block":{"type":"tool_use","id":"empty-claude","name":"lookup","input":[]}}',
                'data: {"type":"message_stop"}',
            ],
            "non_object",
        ),
    ],
)
def test_stream_rejects_falsey_invalid_tool_arguments(monkeypatch, provider, lines, reason):
    """Explicit empty payloads must not be normalized into executable empty objects."""
    monkeypatch.setattr(ai_client.httpx, "stream", lambda *_args, **_kwargs: FakeResponse(lines=lines))

    with pytest.raises(AIClientToolArgumentsError) as error:
        list(ai_client.chat_completion_stream(model(provider), [{"role": "user", "content": "q"}], tools=[]))

    assert error.value.reason == reason


def test_tool_loop_sync_endpoints_and_audit_filters(api_client_factory, db_session, monkeypatch):
    seed_user(db_session, username="alice")
    configured = seed_model(db_session)

    calls = {"count": 0}

    def provider_stream(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            yield AICompletionStreamEvent(
                kind="completed",
                tool_calls=[AIClientToolCall(tool_id="t1", name="get_capacity", arguments={"item_id": 4})],
                stop_reason="tool_calls",
            )
        else:
            yield AICompletionStreamEvent(kind="delta", text="容量正常")
            yield AICompletionStreamEvent(kind="completed", text="容量正常", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)
    monkeypatch.setattr(ai, "enforce_ai_rate_limit", lambda _user_id: None)

    def setup(router: APIRouter):
        @router.get(
            "/capacity/{item_id}",
            openapi_extra={"ai_exposed": True, "ai_name": "get_capacity", "ai_description": "查询容量"},
        )
        def capacity(item_id: int):
            return {"content": [{"id": item_id, "used": 10}], "total": 1}

    client = api_client_factory(
        [ai.router, ai_admin.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
        route_setup=setup,
    )
    assert len(client.get("/storage-pulse/api/ai/models").json()) == 1
    conversation = client.post(
        "/storage-pulse/api/ai/conversations",
        json={"title": "新对话", "model_id": configured.id},
    ).json()
    response = client.post(
        f"/storage-pulse/api/ai/conversations/{conversation['id']}/messages",
        json={"content": "检查容量"},
    )
    assert response.status_code == 200
    assert response.json()["message"]["content"] == "容量正常"
    detail = client.get(f"/storage-pulse/api/ai/conversations/{conversation['id']}").json()
    assert [item["role"] for item in detail["messages"]] == ["user", "assistant"]
    assert client.get("/storage-pulse/api/ai/conversations").json()[0]["title"] == "检查容量"

    audits = client.get("/storage-pulse/api/admin/ai-audits", params={"status": "succeeded", "model_id": configured.id}).json()
    assert audits["total"] == 1
    audit_id = audits["content"][0]["id"]
    trace = client.get(f"/storage-pulse/api/admin/ai-audits/{audit_id}").json()["detail"]
    assert len(trace) == 1
    assert trace[0]["call_id"]
    assert trace[0]["sequence"] == 1
    assert trace[0]["iteration"] == 1
    assert trace[0]["tool_name"] == "get_capacity"
    assert trace[0]["arguments"] == {"item_id": 4}
    assert trace[0]["status"] == "succeeded"
    assert trace[0]["elapsed_ms"] >= 0
    assert trace[0]["result"]["ok"] is True
    assert trace[0]["truncated"] is False
    assert client.get(f"/storage-pulse/api/admin/ai-audits/conversations/{conversation['id']}").json()["content"]
    assert client.delete(f"/storage-pulse/api/ai/conversations/{conversation['id']}").status_code == 204


def test_stream_reuses_successful_tool_results_and_repairs_failed_calls(db_session, monkeypatch):
    """A failed call may be corrected, but a prior successful identical call is never sent again."""
    seed_user(db_session)
    configured = seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=configured.id, title="告警查询")
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    app = FastAPI()
    invocations = []

    @app.get(
        "/alerts",
        openapi_extra={"ai_exposed": True, "ai_name": "list_storage_alerts", "ai_description": "查询告警"},
    )
    def alerts(cluster_id: int):
        invocations.append(cluster_id)
        return {"data": {"cluster_id": cluster_id, "total": 0}}

    provider_messages = []

    def provider_stream(_model, messages, **_kwargs):
        provider_messages.append(messages)
        round_number = len(provider_messages)
        if round_number == 1:
            yield AICompletionStreamEvent(
                kind="completed",
                tool_calls=[AIClientToolCall(tool_id="alerts-1", name="list_storage_alerts", arguments={"cluster_id": 9})],
                stop_reason="tool_calls",
            )
        elif round_number == 2:
            yield AICompletionStreamEvent(
                kind="completed",
                tool_calls=[AIClientToolCall(tool_id="alerts-invalid", name="list_storage_alerts", arguments={"cluster_id": "invalid"})],
                stop_reason="tool_calls",
            )
        elif round_number == 3:
            yield AICompletionStreamEvent(
                kind="completed",
                tool_calls=[AIClientToolCall(tool_id="alerts-reused", name="list_storage_alerts", arguments={"cluster_id": 9})],
                stop_reason="tool_calls",
            )
        else:
            yield AICompletionStreamEvent(kind="delta", text="当前没有异常告警。")
            yield AICompletionStreamEvent(kind="completed", text="当前没有异常告警。", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)
    events = list(
        ai_chat_service.stream_message(
            app=app,
            db=db_session,
            conversation_id=conversation.id,
            user_id=1,
            content="珠海集群有什么异常告警吗？",
        )
    )

    completed = next(data for event, data in events if event == "completed")
    assert completed["message"]["content"] == "当前没有异常告警。"
    assert invocations == [9]
    assert [item["status"] for item in completed["message"]["tool_calls"]] == ["succeeded", "failed", "reused"]
    assert "调用失败" in json.dumps(provider_messages[2], ensure_ascii=False)
    assert "修改参数" in json.dumps(provider_messages[2], ensure_ascii=False)


def test_stream_persists_live_tool_trace_with_distinct_call_ids_and_truncated_results(db_session, monkeypatch):
    seed_user(db_session)
    configured = seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=configured.id, title="工具轨迹")
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    app = FastAPI()

    @app.get(
        "/capacity/{item_id}",
        openapi_extra={"ai_exposed": True, "ai_name": "get_capacity", "ai_description": "查询容量"},
    )
    def capacity(item_id: int):
        return {"data": {"item_id": item_id, "payload": "x" * (33 * 1024) if item_id == 1 else "ok"}}

    rounds = {"count": 0}

    def provider_stream(*_args, **_kwargs):
        rounds["count"] += 1
        if rounds["count"] == 1:
            yield AICompletionStreamEvent(
                kind="completed",
                tool_calls=[
                    AIClientToolCall(tool_id="provider-call-1", name="get_capacity", arguments={"item_id": 1}),
                    AIClientToolCall(tool_id="provider-call-2", name="get_capacity", arguments={"item_id": 2}),
                ],
                stop_reason="tool_calls",
            )
        else:
            yield AICompletionStreamEvent(kind="delta", text="查询完成")
            yield AICompletionStreamEvent(kind="completed", text="查询完成", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)
    stream = ai_chat_service.stream_message(
        app=app,
        db=db_session,
        conversation_id=conversation.id,
        user_id=1,
        content="重复查询容量",
    )

    events = []
    live_trace = None
    while True:
        try:
            event, data = next(stream)
        except StopIteration:
            break
        events.append((event, data))
        if event == "tool_call_started" and live_trace is None:
            db_session.expire_all()
            audit = db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation.id))
            live_trace = json.loads(audit.detail_payload)

    accepted = next(data for event, data in events if event == "accepted")
    started = [data for event, data in events if event == "tool_call_started"]
    finished = [data for event, data in events if event == "tool_call_finished"]
    assert [item["tool_name"] for item in started] == ["get_capacity", "get_capacity"]
    assert len({item["call_id"] for item in started}) == 2
    assert [item["call_id"] for item in finished] == [item["call_id"] for item in started]
    assert all(item["arguments"] in ({"item_id": 1}, {"item_id": 2}) for item in started)
    assert all(data["turn_id"] == accepted["turn_id"] for _event, data in events)
    assert live_trace == [
        {
            "call_id": started[0]["call_id"],
            "sequence": 1,
            "iteration": 1,
            "tool_name": "get_capacity",
            "arguments": {"item_id": 1},
            "status": "running",
            "elapsed_ms": None,
            "truncated": False,
        }
    ]

    db_session.expire_all()
    audit = db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation.id))
    trace = json.loads(audit.detail_payload)
    assert [item["call_id"] for item in trace] == [item["call_id"] for item in started]
    assert trace[0]["status"] == "succeeded"
    assert trace[0]["truncated"] is True
    assert isinstance(trace[0]["result"], dict)
    assert len(json.dumps(trace[0]["result"], ensure_ascii=False).encode("utf-8")) <= 32 * 1024
    assert trace[1]["result"]["ok"] is True

    history = ai_chat_service.get_conversation(db_session, conversation.id, 1)
    assistant = history["messages"][-1]
    assert assistant["turn_id"] == accepted["turn_id"]
    assert assistant["status"] == "succeeded"
    assert [item["call_id"] for item in assistant["tool_calls"]] == [item["call_id"] for item in started]


def test_stream_finishes_an_unknown_tool_call_without_crashing(db_session, monkeypatch):
    seed_user(db_session)
    configured = seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=configured.id, title="未知工具")
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    rounds = {"count": 0}

    def provider_stream(*_args, **_kwargs):
        rounds["count"] += 1
        if rounds["count"] == 1:
            yield AICompletionStreamEvent(
                kind="completed",
                tool_calls=[AIClientToolCall(tool_id="unknown-1", name="unknown_tool", arguments={})],
                stop_reason="tool_calls",
            )
        else:
            yield AICompletionStreamEvent(kind="delta", text="已完成")
            yield AICompletionStreamEvent(kind="completed", text="已完成", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)
    events = list(
        ai_chat_service.stream_message(
            app=FastAPI(),
            db=db_session,
            conversation_id=conversation.id,
            user_id=1,
            content="调用未知工具",
        )
    )

    assert [event for event, _data in events if event == "error"] == []
    started = next(data for event, data in events if event == "tool_call_started")
    finished = next(data for event, data in events if event == "tool_call_finished")
    completed = next(data for event, data in events if event == "completed")
    assert (finished["call_id"], finished["status"]) == (started["call_id"], "failed")
    assert completed["message"]["status"] == "succeeded"


def test_tool_trace_redacts_sensitive_result_keys_before_persisting():
    display, truncated = ai_chat_service._display_tool_result(
        {"accessToken": "should-not-persist", "nested": {"apiKey": "also-hidden"}}
    )

    assert truncated is False
    assert display == {"accessToken": "[REDACTED]", "nested": {"apiKey": "[REDACTED]"}}


def test_stream_history_replaces_unattributed_assistant_turn_with_safe_placeholder(db_session, monkeypatch):
    seed_user(db_session)
    configured = seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=configured.id, title="历史消息")
    db_session.add_all(
        [
            conversation,
            AIMessage(conversation=conversation, role="user", content="之前的问题"),
            AIMessage(conversation=conversation, role="assistant", content="之前的回答"),
        ]
    )
    db_session.commit()
    db_session.refresh(conversation)
    captured_messages = []

    def provider_stream(_model, messages, **_kwargs):
        captured_messages.extend(messages)
        yield AICompletionStreamEvent(kind="delta", text="当前回答")
        yield AICompletionStreamEvent(kind="completed", text="当前回答", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)
    stream = ai_chat_service.stream_message(
        app=FastAPI(),
        db=db_session,
        conversation_id=conversation.id,
        user_id=1,
        content="当前问题",
    )
    list(stream)

    assert captured_messages[-3:] == [
        {"role": "user", "content": "之前的问题"},
        {"role": "assistant", "content": ai_chat_service._HIDDEN_HISTORY_CONTENT},
        {"role": "user", "content": "当前问题"},
    ]


def test_claude_tool_message_format_and_missing_resources(db_session):
    call = AIClientToolCall(tool_id="c1", name="lookup", arguments={"id": 1})
    messages = ai_chat_service._provider_tool_messages("claude", call, {"ok": True})
    assert messages[0]["content"][0]["type"] == "tool_use"
    assert messages[1]["content"][0]["type"] == "tool_result"

    from services import ai_audit_service, ai_config_service

    with pytest.raises(Exception) as model_error:
        ai_config_service.test_model(db_session, 999)
    assert model_error.value.status_code == 404
    with pytest.raises(Exception) as audit_error:
        ai_audit_service.get_audit(db_session, 999)
    assert audit_error.value.status_code == 404
    with pytest.raises(Exception) as conversation_error:
        ai_audit_service.get_conversation_audits(db_session, 999)
    assert conversation_error.value.status_code == 404


def test_tool_registry_provider_shapes_and_failure_responses():
    app = FastAPI()
    router = APIRouter()

    @router.get("/data", openapi_extra={"ai_exposed": True, "ai_name": "data_tool"})
    def data_route():
        return {"data": [1, 2], "meta": {"total": 2}}

    @router.get("/error", openapi_extra={"ai_exposed": True, "ai_name": "error_tool"})
    def error_route():
        raise HTTPException(status_code=418, detail="不可用")

    @router.get("/text", openapi_extra={"ai_exposed": True, "ai_name": "text_tool"})
    def text_route():
        return PlainTextResponse("plain")

    app.include_router(router)
    registry = build_tool_registry(app)
    assert tool_definitions(registry, "claude")[0]["input_schema"]["type"] == "object"
    assert execute_tool(app=app, registry=registry, tool_name="data_tool", arguments={}) == {
        "ok": True,
        "data": {"items": [1, 2], "total": 2},
    }
    assert execute_tool(app=app, registry=registry, tool_name="error_tool", arguments={})["error"] == "不可用"
    assert execute_tool(app=app, registry=registry, tool_name="text_tool", arguments={})["error"] == "工具返回了非 JSON 响应"
    assert _unwrap([1]) == [1]
    assert _unwrap({"data": {"value": 1}}) == {"value": 1}

    duplicate = FastAPI()
    duplicate.include_router(router)
    duplicate.include_router(router)
    with pytest.raises(RuntimeError, match="duplicate"):
        build_tool_registry(duplicate)


def _openai_tool_call_response(arguments: str, *, tool_id="tool-repair", tool_name="get_capacity"):
    return FakeResponse(
        lines=[
            "data: "
            + json.dumps(
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": tool_id,
                                        "function": {"name": tool_name, "arguments": arguments},
                                    }
                                ]
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            "data: [DONE]",
        ]
    )


def _openai_text_response(text: str):
    return FakeResponse(
        lines=[
            "data: " + json.dumps({"choices": [{"delta": {"content": text}}]}, ensure_ascii=False),
            "data: [DONE]",
        ]
    )


def test_openai_stream_ignores_empty_choice_status_frames(monkeypatch):
    response = FakeResponse(
        lines=[
            "data: " + json.dumps({"choices": [], "usage": {"prompt_tokens": 12}}),
            "data: " + json.dumps({"choices": [{"delta": {"content": "容量正常"}}]}, ensure_ascii=False),
            "data: [DONE]",
        ]
    )
    monkeypatch.setattr(ai_client.httpx, "stream", lambda *_args, **_kwargs: response)

    events = list(ai_client.chat_completion_stream(model(), [{"role": "user", "content": "查询容量"}]))

    assert [(event.kind, event.text) for event in events] == [
        ("delta", "容量正常"),
        ("completed", "容量正常"),
    ]


@pytest.mark.parametrize(
    ("raw_arguments", "case"),
    [
        ("not-json-private-tool-arguments", "invalid_json"),
        (json.dumps(["private-non-object-tool-arguments"]), "non_object"),
    ],
)
def test_stream_repairs_malformed_tool_arguments_without_exposing_raw_payload(
    db_session,
    monkeypatch,
    raw_arguments,
    case,
):
    """A malformed provider tool payload is repaired in-band instead of failing the user turn."""
    seed_user(db_session)
    configured = seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=configured.id, title=f"参数修复-{case}")
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    app = FastAPI()

    @app.get(
        "/capacity/{item_id}",
        openapi_extra={"ai_exposed": True, "ai_name": "get_capacity", "ai_description": "查询容量"},
    )
    def capacity(item_id: int):
        return {"data": {"item_id": item_id, "used": 10}}

    provider_requests = []
    provider_responses = [
        _openai_tool_call_response(raw_arguments),
        _openai_tool_call_response('{"item_id": 4}', tool_id="tool-repaired"),
        _openai_text_response("容量已查询"),
    ]

    def provider_stream(*_args, **kwargs):
        provider_requests.append(kwargs["json"])
        return provider_responses.pop(0)

    monkeypatch.setattr(ai_client.httpx, "stream", provider_stream)
    events = list(
        ai_chat_service.stream_message(
            app=app,
            db=db_session,
            conversation_id=conversation.id,
            user_id=1,
            content="查询容量",
        )
    )

    completed = next(data for event, data in events if event == "completed")
    assert not [data for event, data in events if event == "error"]
    assert completed["message"]["status"] == "succeeded"
    assert completed["message"]["content"] == "容量已查询"
    assert len(provider_requests) == 3
    repair_messages = json.dumps(provider_requests[1]["messages"], ensure_ascii=False)
    assert "get_capacity" in repair_messages
    assert raw_arguments not in repair_messages

    db_session.expire_all()
    audit = db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation.id))
    assert audit is not None
    assert audit.status == "succeeded"
    assert all(raw_arguments not in (payload or "") for payload in (audit.request_payload, audit.response_payload, audit.detail_payload))


@pytest.mark.parametrize("summary_fails", [False, True], ids=["disabled_tool_summary", "local_fallback"])
def test_tool_iteration_limit_completes_as_degraded_and_persists_recovery_metadata(
    db_session,
    monkeypatch,
    summary_fails,
):
    seed_user(db_session)
    configured = seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=configured.id, title="轮次限制")
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    app = FastAPI()

    @app.get(
        "/capacity",
        openapi_extra={"ai_exposed": True, "ai_name": "get_capacity", "ai_description": "查询容量"},
    )
    def capacity():
        return {"data": {"used": 10}}

    original_get = base_config.get

    def configured_get(key, default=None):
        return 1 if key == "ai.max_tool_iterations" else original_get(key, default)

    monkeypatch.setattr(ai_chat_service.base_config, "get", configured_get)
    invocations = []

    def provider_stream(_model, _messages, *, tools=None):
        invocations.append(tools)
        if len(invocations) == 1:
            assert tools
            yield AICompletionStreamEvent(
                kind="completed",
                tool_calls=[AIClientToolCall(tool_id="tool-limit", name="get_capacity", arguments={})],
                stop_reason="tool_calls",
            )
            return

        assert tools == []
        if summary_fails:
            raise AIClientError("摘要服务暂不可用")
        yield AICompletionStreamEvent(kind="delta", text="已基于已查询信息完成当前回答。")
        yield AICompletionStreamEvent(
            kind="completed",
            text="已基于已查询信息完成当前回答。",
            tool_calls=[],
            stop_reason="final",
        )

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)
    events = list(
        ai_chat_service.stream_message(
            app=app,
            db=db_session,
            conversation_id=conversation.id,
            user_id=1,
            content="继续查容量",
        )
    )

    completed = next(data for event, data in events if event == "completed")
    assert not [data for event, data in events if event == "error"]
    assert invocations[1] == []
    assert completed["message"]["status"] == "degraded"
    assert completed["message"]["recovery"] == {
        "reason": "tool_iteration_limit",
        "action": "continue",
        "label": "继续查询",
    }
    if summary_fails:
        assert completed["message"]["content"]
        assert "AI 服务暂时不可用" not in completed["message"]["content"]
    else:
        assert completed["message"]["content"] == "已基于已查询信息完成当前回答。"

    db_session.expire_all()
    audit = db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation.id))
    assert audit is not None
    assert audit.status == "degraded"
    response_payload = json.loads(audit.response_payload)
    assert response_payload["status"] == "degraded"
    assert response_payload["recovery"] == completed["message"]["recovery"]
    history = ai_chat_service.get_conversation(db_session, conversation.id, 1)
    assert history["messages"][-1]["status"] == "degraded"
    assert history["messages"][-1]["recovery"] == completed["message"]["recovery"]


def test_history_restores_unfinished_quota_confirmation_for_owner(db_session):
    """Review source: live SSE confirmation cards were absent from history reloads.

    Resolution contract: persist and serialize only the safe, unexpired preview
    for the owning conversation; a different user continues to receive 404.
    """
    seed_user(db_session, user_id=1, username="owner")
    seed_user(db_session, user_id=2, username="other")
    configured = seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=configured.id, title="配额确认")
    db_session.add(conversation)
    db_session.flush()
    assistant = AIMessage(conversation_id=conversation.id, role="assistant", content="请确认")
    db_session.add(assistant)
    db_session.flush()
    pending = {
        "confirmation_id": "confirmation-owner-only",
        "expires_at": 4102444800,
        "expires_in_seconds": 300,
        "preview": {
            "resource": "project-alpha",
            "old_hard_limit": 100,
            "new_hard_limit": 200,
            "unit": "GB",
        },
    }
    db_session.add(AIAuditLog(
        model_id=configured.id,
        conversation_id=conversation.id,
        user_id=1,
        source="chat",
        source_ref=str(conversation.id),
        request_payload="{}",
        response_payload=json.dumps({
            "message_id": assistant.id,
            "visibility": {"known": True, "project_scope_ids": [], "requires_super_admin": False},
        }),
        detail_payload=json.dumps([{
            "status": "awaiting_confirmation",
            "result": {"ok": True, "data": {"confirmation_required": pending}},
            "visibility": {"known": True, "project_scope_ids": [], "requires_super_admin": False},
        }]),
        status="awaiting_confirmation",
    ))
    db_session.commit()

    history = ai_chat_service.get_conversation(db_session, conversation.id, 1)

    restored = history["messages"][-1]["quota_confirmation"]
    assert restored["confirmation_id"] == pending["confirmation_id"]
    assert restored["expires_at"] == pending["expires_at"]
    assert restored["expires_in_seconds"] > 0
    assert restored["preview"] == pending["preview"]
    with pytest.raises(HTTPException) as denied:
        ai_chat_service.get_conversation(db_session, conversation.id, 2)
    assert denied.value.status_code == 404


def test_invalid_json_tool_argument_repairs_stop_after_two_attempts_and_degrade_safely(db_session, monkeypatch):
    seed_user(db_session)
    configured = seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=configured.id, title="参数修复次数")
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    app = FastAPI()

    @app.get(
        "/capacity/{item_id}",
        openapi_extra={"ai_exposed": True, "ai_name": "get_capacity", "ai_description": "查询容量"},
    )
    def capacity(item_id: int):
        return {"data": {"item_id": item_id}}

    raw_arguments = "not-json-secret-tool-arguments"
    provider_requests = []

    def provider_stream(*_args, **kwargs):
        provider_requests.append(kwargs["json"])
        if len(provider_requests) <= 3:
            return _openai_tool_call_response(raw_arguments)
        assert kwargs["json"].get("tools") == []
        return _openai_text_response("已基于已有查询信息给出有限结论。")

    monkeypatch.setattr(ai_client.httpx, "stream", provider_stream)
    events = list(
        ai_chat_service.stream_message(
            app=app,
            db=db_session,
            conversation_id=conversation.id,
            user_id=1,
            content="查询容量",
        )
    )

    completed = next(data for event, data in events if event == "completed")
    assert not [data for event, data in events if event == "error"]
    assert completed["message"]["status"] == "degraded"
    assert completed["message"]["recovery"] == {
        "reason": "invalid_tool_arguments",
        "action": "retry",
        "label": "重新查询",
    }
    enabled_tool_requests = [item for item in provider_requests if item.get("tools")]
    assert len(enabled_tool_requests) == 3
    assert all(raw_arguments not in json.dumps(item["messages"], ensure_ascii=False) for item in provider_requests[1:])
    if len(provider_requests) > 3:
        assert not provider_requests[-1].get("tools")
    assert "AI 服务暂时不可用" not in completed["message"]["content"]
    assert raw_arguments not in json.dumps(completed, ensure_ascii=False, default=str)

    db_session.expire_all()
    audit = db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation.id))
    assert audit is not None
    assert audit.status == "degraded"
    response_payload = json.loads(audit.response_payload)
    assert response_payload["recovery"] == completed["message"]["recovery"]
    assert all(raw_arguments not in (payload or "") for payload in (audit.request_payload, audit.response_payload, audit.detail_payload))
