# -*- coding: utf-8 -*-
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from appConfig import base_config
from models import AIConfig, AIConversation, AIAuditLog, AIMessage, User
from routers import ai, ai_admin
from services import ai_chat_service
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

    roles = list(
        db_session.scalars(
            select(AIMessage.role).where(AIMessage.conversation_id == conversation_id).order_by(AIMessage.id)
        )
    )
    assert roles == ["user", "assistant"]
    assert db_session.scalar(select(AIAuditLog).where(AIAuditLog.conversation_id == conversation_id)).status == "succeeded"

    other_client = api_client_factory([ai.router], headers={"Authorization": f"Bearer {issue_token(2)}"})
    assert other_client.get(f"/storage-pulse/api/ai/conversations/{conversation_id}").status_code == 404


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
