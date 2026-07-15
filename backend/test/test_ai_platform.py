# -*- coding: utf-8 -*-
import importlib.util
import io
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from appConfig import base_config
from models import AIConfig, AIConversation, AIAuditLog, AIMessage, User
from routers import ai, ai_admin
from services import ai_chat_service
from services import ai_config_service
from services.ai_client import AIClientError, AICompletionResult
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
    assert streamed.text.index("event: accepted") < streamed.text.index("event: user_message")
    assert streamed.text.index("event: user_message") < streamed.text.index("event: delta")

    roles = list(
        db_session.scalars(
            select(AIMessage.role).where(AIMessage.conversation_id == conversation_id).order_by(AIMessage.id)
        )
    )
    assert roles == ["user", "assistant"]
    assert db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation_id)).status == "succeeded"

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


def test_provider_failure_is_audited_without_assistant_message(
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
    db_session.expire_all()
    assert list(db_session.scalars(select(AIMessage).where(AIMessage.conversation_id == conversation_id)))[0].role == "user"
    assert db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation_id)).status == "failed"


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
    assert next(stream)[0] == "accepted"
    stream.close()
    db_session.expire_all()
    assert db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation.id)).status == "cancelled"


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
