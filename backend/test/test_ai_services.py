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
from services import ai_chat_service, ai_client
from services.ai_client import AIClientError, AIClientToolCall, AICompletionStreamEvent
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
    assert client.get(f"/storage-pulse/api/admin/ai-audits/{audit_id}").json()["detail"] == [
        {"tool_name": "get_capacity", "ok": True}
    ]
    assert client.get(f"/storage-pulse/api/admin/ai-audits/conversations/{conversation['id']}").json()["content"]
    assert client.delete(f"/storage-pulse/api/ai/conversations/{conversation['id']}").status_code == 204


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
