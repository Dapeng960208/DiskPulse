# -*- coding: utf-8 -*-
import importlib.util
import json
import io
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import APIRouter, FastAPI, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from appConfig import base_config
from models import AIConfig, AIConversation, AIAuditLog, AIMessage, User
from routers import (
    aggregate,
    ai,
    ai_admin,
    config,
    group_tag,
    qtrees,
    storage_back_up_records,
    storage_cluster,
    users,
    volumes,
)
from services import ai_chat_service
from services import ai_config_service
from services.ai_client import AIClientError, AIClientToolCall, AICompletionResult
from services.ai_client import AICompletionStreamEvent
from services.ai_rate_limit import enforce_ai_rate_limit
from services.ai_security import decrypt_secret, encrypt_secret, mask_secret
from services.ai_tool_service import build_tool_registry, execute_tool
from utils.security import issue_token


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def incr(self, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key, seconds):
        self.ttls[key] = seconds

    def ttl(self, key):
        return self.ttls.get(key, -1)


def _seed_user(db, *, user_id=1, rd_username="reader"):
    user = User(id=user_id, username=rd_username, rd_username=rd_username, email=f"{rd_username}@example.com")
    db.add(user)
    db.commit()
    return user


def _seed_model(db, *, actor_id=1):
    model = AIConfig(
        name="Primary",
        provider="openai",
        base_url="https://ai.example.com/v1",
        api_key_encrypted=encrypt_secret("secret-key-1234"),
        model="gpt-test",
        enabled=True,
        enable_chat=True,
        temperature=0.3,
        max_tokens=256,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def _sse_events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_ai_models_match_global_conversation_contract():
    assert AIConfig.__tablename__ == "ai_configs"
    assert AIConversation.__tablename__ == "ai_conversations"
    assert AIMessage.__tablename__ == "ai_messages"
    assert AIAuditLog.__tablename__ == "ai_audit_logs"
    assert "project_id" not in AIConversation.__table__.columns


def test_ai_secret_is_encrypted_and_masked():
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    encrypted = encrypt_secret("sk-example-123456")

    assert encrypted.startswith("fernet::")
    assert "sk-example" not in encrypted
    assert decrypt_secret(encrypted) == "sk-example-123456"
    assert mask_secret("sk-example-123456") == "sk-e****3456"


def test_rate_limit_uses_fixed_window_and_returns_retry_after():
    client = FakeRedis()
    for _ in range(10):
        enforce_ai_rate_limit(7, client=client)

    try:
        enforce_ai_rate_limit(7, client=client)
    except Exception as error:
        assert getattr(error, "status_code", None) == 429
        assert getattr(error, "headers", {}).get("Retry-After") == "60"
    else:  # pragma: no cover - assertion guard
        raise AssertionError("expected rate limit rejection")


def test_dynamic_tool_registry_only_exposes_marked_get_routes():
    app = FastAPI()
    router = APIRouter()

    @router.get(
        "/visible/{item_id}",
        openapi_extra={"ai_exposed": True, "ai_name": "get_visible", "ai_description": "读取条目"},
    )
    def visible(item_id: int, limit: int = 20):
        return {"content": [{"id": item_id}], "total": 1, "limit": limit}

    @router.get("/hidden")
    def hidden():
        return {"secret": True}

    @router.post("/write", openapi_extra={"ai_exposed": True})
    def write():
        return {"written": True}

    app.include_router(router)
    registry = build_tool_registry(app)

    assert set(registry) == {"get_visible"}
    assert execute_tool(app=app, registry=registry, tool_name="get_visible", arguments={"item_id": 3}) == {
        "ok": True,
        "data": {"items": [{"id": 3}], "total": 1, "limit": 20},
    }
    assert execute_tool(app=app, registry=registry, tool_name="hidden", arguments={})["ok"] is False
    assert execute_tool(
        app=app,
        registry=registry,
        tool_name="get_visible",
        arguments={"item_id": "not-an-integer"},
    )["error"] == "工具参数无效"


def test_system_management_tools_require_super_admin_for_registry_and_execution(monkeypatch):
    app = FastAPI()
    router = APIRouter()
    executed = []

    @router.get(
        "/capacity",
        openapi_extra={"ai_exposed": True, "ai_name": "get_capacity", "ai_description": "查询容量"},
    )
    def get_capacity():
        return {"data": {"used": 10}}

    @router.get(
        "/system/settings",
        openapi_extra={
            "ai_exposed": True,
            "ai_system_management": True,
            "ai_name": "list_system_settings",
            "ai_description": "读取系统设置",
        },
    )
    def list_system_settings():
        return {"data": []}

    @router.post(
        "/system/settings",
        openapi_extra={
            "ai_exposed": True,
            "ai_system_management": True,
            "ai_name": "create_system_setting",
            "ai_description": "创建系统设置",
        },
    )
    def create_system_setting():
        executed.append("create")
        return {"data": {"created": True}}

    @router.patch(
        "/system/settings/{setting_id}",
        openapi_extra={
            "ai_exposed": True,
            "ai_system_management": True,
            "ai_name": "update_system_setting",
            "ai_description": "更新系统设置",
        },
    )
    def update_system_setting(setting_id: int):
        executed.append(f"update:{setting_id}")
        return {"data": {"updated": setting_id}}

    @router.delete(
        "/system/settings/{setting_id}",
        openapi_extra={
            "ai_exposed": True,
            "ai_system_management": True,
            "ai_name": "delete_system_setting",
            "ai_description": "删除系统设置",
        },
    )
    def delete_system_setting(setting_id: int):
        executed.append(f"delete:{setting_id}")
        return {"data": {"deleted": setting_id}}

    app.include_router(router)
    original_get = base_config.get

    def configured_get(key, default=None):
        return ["ai-admin"] if key == "super_admin_usernames" else original_get(key, default)

    monkeypatch.setattr(base_config, "get", configured_get)
    reader = User(id=101, username="reader", rd_username="reader", email="reader@example.com")
    admin = User(id=102, username="ai-admin", rd_username="ai-admin", email="admin@example.com")

    reader_registry = build_tool_registry(app, current_user=reader)
    admin_registry = build_tool_registry(app, current_user=admin)

    assert set(reader_registry) == {"get_capacity"}
    assert set(admin_registry) == {
        "get_capacity",
        "list_system_settings",
        "create_system_setting",
        "update_system_setting",
        "delete_system_setting",
    }

    # A registry constructed for an admin is untrusted at execution time: the current user is authoritative.
    result = execute_tool(
        app=app,
        registry=admin_registry,
        tool_name="create_system_setting",
        arguments={},
        current_user=reader,
    )

    assert result == {"ok": False, "error": "系统管理工具仅限超级管理员"}
    assert executed == []


def test_registered_system_management_crud_tools_are_admin_only(monkeypatch):
    app = FastAPI()
    for router in (
        storage_cluster.router,
        aggregate.router,
        volumes.router,
        qtrees.router,
        group_tag.router,
        users.router,
        config.router,
        ai_admin.router,
        storage_back_up_records.router,
    ):
        app.include_router(router)

    original_get = base_config.get

    def configured_get(key, default=None):
        return ["ai-admin"] if key == "super_admin_usernames" else original_get(key, default)

    monkeypatch.setattr(base_config, "get", configured_get)
    reader = User(id=101, username="reader", rd_username="reader", email="reader@example.com")
    admin = User(id=102, username="ai-admin", rd_username="ai-admin", email="admin@example.com")

    expected = {
        "list_storage_clusters": ("/storage-clusters/", "GET"),
        "create_storage_cluster": ("/storage-clusters/", "POST"),
        "get_storage_cluster": ("/storage-clusters/{storage_cluster_id}", "GET"),
        "update_storage_cluster": ("/storage-clusters/{storage_cluster_id}", "PUT"),
        "delete_storage_cluster": ("/storage-clusters/{storage_cluster_id}", "DELETE"),
        "list_aggregates": ("/aggregates/", "GET"),
        "create_aggregate": ("/aggregates/", "POST"),
        "get_aggregate": ("/aggregates/{aggregate_id}", "GET"),
        "update_aggregate": ("/aggregates/{aggregate_id}", "PUT"),
        "delete_aggregate": ("/aggregates/{aggregate_id}", "DELETE"),
        "list_volumes": ("/volumes/", "GET"),
        "create_volume": ("/volumes/", "POST"),
        "get_volume": ("/volumes/{volume_id}", "GET"),
        "update_volume": ("/volumes/{volume_id}", "PUT"),
        "delete_volume": ("/volumes/{volume_id}", "DELETE"),
        "list_qtrees": ("/qtrees/", "GET"),
        "create_qtree": ("/qtrees/", "POST"),
        "get_qtree": ("/qtrees/{qtree_id}", "GET"),
        "update_qtree": ("/qtrees/{qtree_id}", "PUT"),
        "delete_qtree": ("/qtrees/{qtree_id}", "DELETE"),
        "list_group_tags": ("/group-tags", "GET"),
        "create_group_tag": ("/group-tags", "POST"),
        "get_group_tag": ("/group-tags/{group_tag_id}", "GET"),
        "update_group_tag": ("/group-tags/{group_tag_id}", "PUT"),
        "delete_group_tag": ("/group-tags/{group_tag_id}", "DELETE"),
        "list_users": ("/users/", "GET"),
        "create_user": ("/users/", "POST"),
        "get_user": ("/users/{user_id}", "GET"),
        "update_user": ("/users/{user_id}", "PUT"),
        "delete_user": ("/users/{user_id}", "DELETE"),
        "list_ai_models": ("/admin/ai-models", "GET"),
        "create_ai_model": ("/admin/ai-models", "POST"),
        "update_ai_model": ("/admin/ai-models/{model_id}", "PATCH"),
        "delete_ai_model": ("/admin/ai-models/{model_id}", "DELETE"),
        "get_storage_config": ("/config/storage", "GET"),
        "update_storage_config": ("/config/storage", "PUT"),
        "list_storage_backup_records": ("/storage-back-up-records/", "GET"),
        "delete_storage_backup_record": ("/storage-back-up-records/{storage_back_up_record_id}", "DELETE"),
    }
    admin_registry = build_tool_registry(app, current_user=admin)
    reader_registry = build_tool_registry(app, current_user=reader)

    assert {
        name: (definition.route_path, definition.method)
        for name, definition in admin_registry.items()
        if definition.system_management
    } == expected
    assert not (set(expected) & set(reader_registry))
    assert not any(
        definition.system_management and (definition.route_path, definition.method) in {
            ("/users/login", "POST"),
            ("/users/logout", "POST"),
            ("/users/current/profile", "GET"),
            ("/users/sync-ldap", "POST"),
            ("/storage-clusters/{storage_cluster_id}/realtime", "GET"),
            ("/storage-clusters/{storage_cluster_id}/analytics/capacity-change", "GET"),
            ("/storage-clusters/{storage_cluster_id}/analytics/error-severity", "GET"),
            ("/storage-clusters/{storage_cluster_id}/analytics/top-latency", "GET"),
            ("/storage-clusters/{storage_cluster_id}/analytics/repeated-faults", "GET"),
            ("/storage-clusters/{storage_cluster_id}/analytics/system-events", "GET"),
            ("/storage-clusters/{storage_cluster_id}/analytics/export", "GET"),
            ("/aggregates/{aggregate_id}/realtime", "GET"),
            ("/volumes/{volume_id}/realtime", "GET"),
            ("/qtrees/{qtree_id}/realtime", "GET"),
            ("/admin/ai-models/{model_id}/test", "POST"),
            ("/admin/ai-audits", "GET"),
            ("/admin/ai-audits/conversations/{conversation_id}", "GET"),
            ("/admin/ai-audits/{audit_id}", "GET"),
            ("/storage-back-up-records/{storage_back_up_record_id}/rollback", "POST"),
        }
        for definition in admin_registry.values()
    )


def test_system_management_tool_validates_and_forwards_pydantic_body(monkeypatch):
    class SettingPayload(BaseModel):
        model_config = ConfigDict(extra="forbid")

        name: str
        enabled: bool

    app = FastAPI()
    router = APIRouter()
    executed = []

    @router.post(
        "/system/settings",
        openapi_extra={
            "ai_exposed": True,
            "ai_system_management": True,
            "ai_name": "create_system_setting",
            "ai_description": "创建系统设置",
        },
    )
    def create_system_setting(payload: SettingPayload):
        executed.append(payload)
        return {"data": payload.model_dump()}

    app.include_router(router)
    original_get = base_config.get

    def configured_get(key, default=None):
        return ["ai-admin"] if key == "super_admin_usernames" else original_get(key, default)

    monkeypatch.setattr(base_config, "get", configured_get)
    admin = User(id=102, username="ai-admin", rd_username="ai-admin", email="admin@example.com")
    registry = build_tool_registry(app, current_user=admin)

    result = execute_tool(
        app=app,
        registry=registry,
        tool_name="create_system_setting",
        arguments={"body": {"name": "retention", "enabled": True}},
        current_user=admin,
    )
    invalid = execute_tool(
        app=app,
        registry=registry,
        tool_name="create_system_setting",
        arguments={"body": {"name": "retention", "enabled": True, "unexpected": "blocked"}},
        current_user=admin,
    )

    assert result == {"ok": True, "data": {"name": "retention", "enabled": True}}
    assert invalid["error"] == "工具参数无效"
    assert [payload.name for payload in executed] == ["retention"]


def test_system_management_delete_no_content_is_successful(monkeypatch):
    app = FastAPI()
    router = APIRouter()

    @router.delete(
        "/system/settings/{setting_id}",
        openapi_extra={
            "ai_exposed": True,
            "ai_system_management": True,
            "ai_name": "delete_system_setting",
            "ai_description": "删除系统设置",
        },
    )
    def delete_system_setting(setting_id: int):
        assert setting_id == 7
        return Response(status_code=204)

    app.include_router(router)
    original_get = base_config.get

    def configured_get(key, default=None):
        return ["ai-admin"] if key == "super_admin_usernames" else original_get(key, default)

    monkeypatch.setattr(base_config, "get", configured_get)
    admin = User(id=102, username="ai-admin", rd_username="ai-admin", email="admin@example.com")
    registry = build_tool_registry(app, current_user=admin)

    assert execute_tool(
        app=app,
        registry=registry,
        tool_name="delete_system_setting",
        arguments={"setting_id": 7},
        current_user=admin,
    ) == {"ok": True, "data": None}


def test_chat_adds_system_management_instruction_only_when_admin_tools_are_authorized(
    db_session,
    monkeypatch,
):
    reader = _seed_user(db_session, user_id=1, rd_username="reader")
    admin = _seed_user(db_session, user_id=2, rd_username="ai-admin")
    configured = _seed_model(db_session)
    reader_conversation = AIConversation(user_id=reader.id, model_id=configured.id, title="普通用户")
    admin_conversation = AIConversation(user_id=admin.id, model_id=configured.id, title="超级管理员")
    db_session.add_all([reader_conversation, admin_conversation])
    db_session.commit()
    db_session.refresh(reader_conversation)
    db_session.refresh(admin_conversation)

    app = FastAPI()
    router = APIRouter()

    @router.get(
        "/capacity",
        openapi_extra={"ai_exposed": True, "ai_name": "get_capacity", "ai_description": "查询容量"},
    )
    def get_capacity():
        return {"data": {"used": 10}}

    @router.post(
        "/system/settings",
        openapi_extra={
            "ai_exposed": True,
            "ai_system_management": True,
            "ai_name": "create_system_setting",
            "ai_description": "创建系统设置",
        },
    )
    def create_system_setting():
        return {"data": {"created": True}}

    app.include_router(router)
    original_get = base_config.get

    def configured_get(key, default=None):
        return ["ai-admin"] if key == "super_admin_usernames" else original_get(key, default)

    monkeypatch.setattr(base_config, "get", configured_get)
    provider_requests = []

    def provider_stream(_model, messages, *, tools=None):
        provider_requests.append({"messages": messages, "tools": tools})
        yield AICompletionStreamEvent(kind="delta", text="已收到")
        yield AICompletionStreamEvent(kind="completed", text="已收到", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)
    list(
        ai_chat_service.stream_message(
            app=app,
            db=db_session,
            conversation_id=reader_conversation.id,
            user_id=reader.id,
            current_user=reader,
            content="查看容量",
        )
    )
    list(
        ai_chat_service.stream_message(
            app=app,
            db=db_session,
            conversation_id=admin_conversation.id,
            user_id=admin.id,
            current_user=admin,
            content="创建系统设置",
        )
    )

    reader_request, admin_request = provider_requests
    reader_tool_names = [tool["function"]["name"] for tool in reader_request["tools"]]
    admin_tool_names = [tool["function"]["name"] for tool in admin_request["tools"]]
    reader_prompts = [str(item["content"]) for item in reader_request["messages"] if item["role"] == "system"]
    admin_prompts = [str(item["content"]) for item in admin_request["messages"] if item["role"] == "system"]

    assert reader_tool_names == ["get_capacity"]
    assert admin_tool_names == ["get_capacity", "create_system_setting"]
    assert not any("系统管理工具" in prompt for prompt in reader_prompts)
    assert any("仅在用户明确要求时执行" in prompt and "删除或更新" in prompt for prompt in admin_prompts)


def test_non_super_admin_cannot_manage_ai_models(api_client_factory, db_session):
    _seed_user(db_session)
    client = api_client_factory([ai_admin.router], headers={"Authorization": f"Bearer {issue_token(1)}"})

    assert client.get("/storage-pulse/api/admin/ai-models").status_code == 403


def test_chat_stream_persists_messages_and_isolates_conversations(
    api_client_factory,
    db_session,
    monkeypatch,
):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    _seed_user(db_session, user_id=1, rd_username="reader")
    _seed_user(db_session, user_id=2, rd_username="other")
    model = _seed_model(db_session)

    def fake_stream(*_args, **_kwargs):
        yield AICompletionStreamEvent(kind="delta", text="容量")
        yield AICompletionStreamEvent(kind="delta", text="正常")
        yield AICompletionStreamEvent(kind="completed", text="容量正常", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", fake_stream)
    monkeypatch.setattr(ai, "enforce_ai_rate_limit", lambda _user_id: None)
    client = api_client_factory([ai.router], headers={"Authorization": f"Bearer {issue_token(1)}"})

    created = client.post(
        "/storage-pulse/api/ai/conversations",
        json={"title": "新对话", "model_id": model.id},
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    streamed = client.post(
        f"/storage-pulse/api/ai/conversations/{conversation_id}/messages/stream",
        json={"content": "当前容量如何？"},
    )
    assert streamed.status_code == 200
    assert "event: accepted" in streamed.text
    assert "event: delta" in streamed.text
    assert "event: completed" in streamed.text
    events = _sse_events(streamed.text)
    event_names = [name for name, _data in events]
    assert event_names.index("user_message") < event_names.index("accepted") < event_names.index("delta")
    accepted = next(data for name, data in events if name == "accepted")
    completed = next(data for name, data in events if name == "completed")
    assert accepted["turn_id"] == accepted["audit_id"]
    assert accepted["message_id"] == accepted["message"]["id"]
    assert accepted["message"]["content"] == ""
    assert accepted["message"]["turn_id"] == accepted["turn_id"]
    assert completed["turn_id"] == accepted["turn_id"]
    assert completed["message"]["id"] == accepted["message_id"]
    assert all(data["turn_id"] == accepted["turn_id"] for _name, data in events)

    roles = list(
        db_session.scalars(
            select(AIMessage.role).where(AIMessage.conversation_id == conversation_id).order_by(AIMessage.id)
        )
    )
    assert roles == ["user", "assistant"]
    audit = db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation_id))
    assert audit.status == "succeeded"
    assert json.loads(audit.response_payload)["message_id"] == accepted["message_id"]

    history = client.get(f"/storage-pulse/api/ai/conversations/{conversation_id}").json()
    assistant = history["messages"][-1]
    assert assistant["id"] == accepted["message_id"]
    assert assistant["turn_id"] == accepted["turn_id"]
    assert assistant["status"] == "succeeded"
    assert assistant["tool_calls"] == []

    other_client = api_client_factory([ai.router], headers={"Authorization": f"Bearer {issue_token(2)}"})
    assert other_client.get(f"/storage-pulse/api/ai/conversations/{conversation_id}").status_code == 404


def test_super_admin_model_crud_masks_key_and_runs_real_connection_test(
    api_client_factory,
    db_session,
    monkeypatch,
):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    admin = _seed_user(db_session, rd_username="alice")
    monkeypatch.setattr(
        ai_config_service,
        "chat_completion",
        lambda *_args, **_kwargs: AICompletionResult(text="OK", tool_calls=[], stop_reason="final"),
    )
    client = api_client_factory([ai_admin.router], headers={"Authorization": f"Bearer {issue_token(admin.id)}"})

    created = client.post(
        "/storage-pulse/api/admin/ai-models",
        json={
            "name": "Claude Primary",
            "provider": "claude",
            "base_url": "https://ai.example.com",
            "api_key": "secret-key-1234",
            "model": "claude-test",
            "enabled": True,
            "enable_chat": True,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["api_key_masked"] == "secr****1234"
    assert "api_key" not in body

    updated = client.patch(
        f"/storage-pulse/api/admin/ai-models/{body['id']}",
        json={"description": "updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["api_key_masked"] == "secr****1234"
    assert client.post(f"/storage-pulse/api/admin/ai-models/{body['id']}/test").json()["reply"] == "OK"
    assert client.delete(f"/storage-pulse/api/admin/ai-models/{body['id']}").status_code == 204


def test_provider_failure_persists_the_precreated_assistant_message(
    api_client_factory,
    db_session,
    monkeypatch,
):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    _seed_user(db_session)
    model = _seed_model(db_session)

    def failed_stream(*_args, **_kwargs):
        raise AIClientError("AI 服务返回 HTTP 502")
        yield  # pragma: no cover

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", failed_stream)
    monkeypatch.setattr(ai, "enforce_ai_rate_limit", lambda _user_id: None)
    client = api_client_factory([ai.router], headers={"Authorization": f"Bearer {issue_token(1)}"})
    conversation_id = client.post(
        "/storage-pulse/api/ai/conversations",
        json={"title": "失败对话", "model_id": model.id},
    ).json()["id"]

    response = client.post(
        f"/storage-pulse/api/ai/conversations/{conversation_id}/messages/stream",
        json={"content": "查询容量"},
    )
    assert "event: error" in response.text
    assert "HTTP 502" in response.text
    events = _sse_events(response.text)
    accepted = next(data for name, data in events if name == "accepted")
    error = next(data for name, data in events if name == "error")
    assert error["turn_id"] == accepted["turn_id"]
    assert error["message"]["id"] == accepted["message_id"]
    assert error["message"]["status"] == "failed"
    assert error["message"]["content"]
    db_session.expire_all()
    messages = list(db_session.scalars(select(AIMessage).where(AIMessage.conversation_id == conversation_id)))
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[-1].id == accepted["message_id"]
    assert messages[-1].content
    audit = db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation_id))
    assert audit.status == "failed"
    assert json.loads(audit.response_payload)["message_id"] == accepted["message_id"]


def test_closing_stream_marks_audit_cancelled(db_session):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    _seed_user(db_session)
    model = _seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=model.id, title="取消测试")
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    stream = ai_chat_service.stream_message(
        app=FastAPI(),
        db=db_session,
        conversation_id=conversation.id,
        user_id=1,
        content="停止这个请求",
    )
    assert next(stream)[0] == "user_message"
    event, accepted = next(stream)
    assert event == "accepted"
    stream.close()
    db_session.expire_all()
    audit = db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation.id))
    assert audit.status == "cancelled"
    assert json.loads(audit.response_payload)["message_id"] == accepted["message_id"]
    assistant = db_session.get(AIMessage, accepted["message_id"])
    assert assistant is not None
    assert assistant.role == "assistant"
    history = ai_chat_service.get_conversation(db_session, conversation.id, 1)
    assert history["messages"][-1]["status"] == "cancelled"
    assert history["messages"][-1]["turn_id"] == accepted["turn_id"]


def test_closing_stream_after_completed_keeps_the_persisted_success(db_session, monkeypatch):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    _seed_user(db_session)
    model = _seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=model.id, title="完成后断开")
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    def completed_stream(*_args, **_kwargs):
        yield AICompletionStreamEvent(kind="delta", text="已完成")
        yield AICompletionStreamEvent(kind="completed", text="已完成", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", completed_stream)
    stream = ai_chat_service.stream_message(
        app=FastAPI(),
        db=db_session,
        conversation_id=conversation.id,
        user_id=1,
        content="完成后关闭",
    )
    while next(stream)[0] != "completed":
        pass
    stream.close()

    db_session.expire_all()
    audit = db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation.id))
    assert audit.status == "succeeded"


def test_stream_setup_failure_still_emits_the_precreated_turn(db_session, monkeypatch):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    _seed_user(db_session)
    model = _seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=model.id, title="初始化失败")
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    def broken_registry(_app):
        raise RuntimeError("工具注册失败")

    monkeypatch.setattr(ai_chat_service, "build_tool_registry", broken_registry)
    events = list(
        ai_chat_service.stream_message(
            app=FastAPI(),
            db=db_session,
            conversation_id=conversation.id,
            user_id=1,
            content="初始化失败后仍需返回回复标识",
        )
    )

    assert [event for event, _data in events[:2]] == ["user_message", "accepted"]
    accepted = events[1][1]
    error = events[-1][1]
    assert events[-1][0] == "error"
    assert error["turn_id"] == accepted["turn_id"]
    assert error["message"]["id"] == accepted["message_id"]
    assert error["message"]["status"] == "failed"


def test_rate_limit_returns_503_when_redis_is_unavailable():
    import redis

    class FailedRedis:
        def incr(self, _key):
            raise redis.RedisError("offline")

    try:
        enforce_ai_rate_limit(9, client=FailedRedis())
    except Exception as error:
        assert getattr(error, "status_code", None) == 503
    else:  # pragma: no cover - assertion guard
        raise AssertionError("expected Redis availability rejection")


def test_ai_migration_creates_expected_tables_without_project_binding():
    source = (
        Path(__file__).resolve().parents[1]
        / "migrate"
        / "versions"
        / "000000000003_ai_chat.py"
    ).read_text(encoding="utf-8")

    for table_name in ("ai_configs", "ai_conversations", "ai_messages", "ai_audit_logs"):
        assert f'"{table_name}"' in source
    assert 'down_revision: str = "000000000002"' in source
    assert '"project_id"' not in source


def _ai_migration():
    path = Path(__file__).resolve().parents[1] / "migrate" / "versions" / "000000000003_ai_chat.py"
    spec = importlib.util.spec_from_file_location("ai_chat_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_ai_migration_compiles_for_supported_dialects():
    for dialect_name in ("sqlite", "postgresql", "mysql"):
        migration = _ai_migration()
        output = io.StringIO()
        migration.op = Operations(
            MigrationContext.configure(
                dialect_name=dialect_name,
                opts={"as_sql": True, "output_buffer": output},
            )
        )
        migration.upgrade()
        sql = output.getvalue().lower()
        assert all(table in sql for table in ("ai_configs", "ai_conversations", "ai_messages", "ai_audit_logs"))


def test_ai_migration_adopts_complete_create_all_schema():
    migration = _ai_migration()
    tables = (AIConfig.__table__, AIConversation.__table__, AIMessage.__table__, AIAuditLog.__table__)

    with sa.create_engine("sqlite://").begin() as connection:
        for table in tables:
            table.create(connection)
        migration.op = Operations(MigrationContext.configure(connection))

        migration.upgrade()

        assert set(sa.inspect(connection).get_table_names()) == {table.name for table in tables}


def test_ai_migration_rejects_partial_create_all_schema():
    migration = _ai_migration()

    with sa.create_engine("sqlite://").begin() as connection:
        AIConfig.__table__.create(connection)
        migration.op = Operations(MigrationContext.configure(connection))

        with pytest.raises(RuntimeError, match="partial AI schema"):
            migration.upgrade()
