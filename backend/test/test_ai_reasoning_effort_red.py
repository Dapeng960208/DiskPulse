# -*- coding: utf-8 -*-
import importlib
import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import select

from appConfig import base_config
from models import AIConfig, AIConversation, AIAuditLog, AIMessage, User
from routers import ai, ai_admin
from schemas.aiSchema import AIModelCreate, ConversationCreate, MessageCreate
from services import ai_chat_service, ai_config_service
from services.ai_client import AICompletionStreamEvent
from services.ai_security import encrypt_secret
from utils.security import issue_token


PROVIDERS = {
    "openai",
    "openrouter",
    "ollama",
    "claude",
    "claude_code",
    "deepseek",
    "dashscope",
    "volcengine",
    "zhipu",
    "moonshot",
    "minimax",
    "qianfan",
    "hunyuan",
}


def _seed_user(db, *, user_id=1, username="alice"):
    user = User(
        id=user_id,
        username=username,
        rd_username=username,
        email=f"{username}@example.com",
    )
    db.add(user)
    db.commit()
    return user


def _seed_model(
    db,
    *,
    actor_id=1,
    name="Reasoning model",
    provider="openai",
    model_name="gpt-5.2",
    control=None,
):
    model = AIConfig(
        name=name,
        provider=provider,
        base_url="https://ai.example.com/v1",
        api_key_encrypted=encrypt_secret("secret-key-1234"),
        model=model_name,
        enabled=True,
        enable_chat=True,
        temperature=0.3,
        max_tokens=256,
        created_by=actor_id,
        updated_by=actor_id,
    )
    # These attributes become mapped columns in the implementation. Assigning them
    # here lets the current runtime reach the intended assertion instead of failing
    # in unrelated fixture setup.
    model.capability_cache = json.dumps(
        control
        or {
            "kind": "effort",
            "options": ["auto", "low", "medium", "high"],
            "provider_default": "medium",
            "mandatory": False,
            "source": "official_catalog",
        },
        ensure_ascii=False,
    )
    model.capability_status = "ready"
    model.capability_error = None
    model.capability_updated_at = datetime(2026, 7, 23, 10, 0, 0)
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def _completed_stream(*_args, **_kwargs):
    yield AICompletionStreamEvent(kind="delta", text="完成")
    yield AICompletionStreamEvent(
        kind="completed",
        text="完成",
        tool_calls=[],
        stop_reason="final",
    )


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_ai_model_schema_accepts_every_supported_provider(provider):
    payload = AIModelCreate(name=provider, provider=provider, model="model-test")

    assert payload.provider == provider


def test_conversation_and_message_schemas_expose_optional_model_and_reasoning():
    conversation = ConversationCreate()
    message = MessageCreate(content="分析容量", reasoning="high")

    assert conversation.model_id is None
    assert message.reasoning == "high"
    assert MessageCreate(content="自动选择").reasoning == "auto"
    with pytest.raises(ValidationError):
        MessageCreate(content="无效档位", reasoning="ultra")


def test_reasoning_persistence_models_and_migration_contract():
    from models import AIPlatformSetting

    assert AIPlatformSetting.__tablename__ == "ai_platform_settings"
    assert set(AIPlatformSetting.__table__.columns.keys()) >= {
        "id",
        "default_chat_model_id",
        "updated_by",
        "created_at",
        "updated_at",
    }
    assert set(AIConfig.__table__.columns.keys()) >= {
        "capability_cache",
        "capability_status",
        "capability_error",
        "capability_updated_at",
    }
    assert "reasoning" in AIMessage.__table__.columns

    versions_dir = Path(__file__).resolve().parents[1] / "migrate" / "versions"
    migration_sources = [
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
        if "ai_platform_settings" in path.read_text(encoding="utf-8")
    ]
    assert len(migration_sources) == 1
    assert "capability_cache" in migration_sources[0]
    assert "reasoning" in migration_sources[0]


@pytest.mark.parametrize(
    ("provider", "model_name", "expected_kind", "expected_options"),
    [
        ("openai", "gpt-5.2", "effort", ["auto", "none", "low", "medium", "high", "xhigh"]),
        ("ollama", "gpt-oss:20b", "effort", ["auto", "low", "medium", "high"]),
        ("deepseek", "deepseek-reasoner", "effort", ["auto", "high", "max"]),
        ("dashscope", "qwen3-max", "toggle", ["auto", "off", "on"]),
        ("volcengine", "doubao-seed-1-6-thinking", "toggle", ["auto", "off", "on"]),
        ("zhipu", "glm-5", "effort", ["auto", "minimal", "low", "medium", "high", "xhigh"]),
        ("moonshot", "kimi-k3", "effort", ["auto", "low", "high", "max"]),
        ("minimax", "MiniMax-M2.1", "none", ["auto"]),
        ("qianfan", "ernie-4.5-turbo-128k-thinking", "toggle", ["auto", "off", "on"]),
        ("hunyuan", "hunyuan-t1", "effort", ["auto", "low", "medium", "high"]),
    ],
)
def test_official_catalog_resolves_truthful_native_controls(
    provider,
    model_name,
    expected_kind,
    expected_options,
):
    capability_service = importlib.import_module("services.ai_reasoning_service")

    control = capability_service.resolve_reasoning_control(provider, model_name)

    assert control["kind"] == expected_kind
    assert control["options"] == expected_options
    assert control["source"] == "official_catalog"
    assert control["status"] == "ready"


@pytest.mark.parametrize(
    ("provider", "metadata", "expected"),
    [
        (
            "openrouter",
            {
                "reasoning": {
                    "supported_efforts": ["low", "high", "max"],
                    "default_effort": "high",
                    "mandatory": True,
                }
            },
            {
                "kind": "effort",
                "options": ["auto", "low", "high", "max"],
                "provider_default": "high",
                "mandatory": True,
            },
        ),
        (
            "claude",
            {
                "capabilities": {
                    "effort": {
                        "supported_efforts": ["low", "medium", "high"],
                        "default_effort": "high",
                    }
                }
            },
            {
                "kind": "effort",
                "options": ["auto", "low", "medium", "high"],
                "provider_default": "high",
                "mandatory": False,
            },
        ),
    ],
)
def test_provider_metadata_takes_precedence_over_the_official_catalog(
    provider,
    metadata,
    expected,
):
    capability_service = importlib.import_module("services.ai_reasoning_service")

    control = capability_service.resolve_reasoning_control(
        provider,
        "provider-model",
        provider_metadata=metadata,
    )

    assert {key: control[key] for key in expected} == expected
    assert control["source"] == "provider"
    assert control["status"] == "ready"


def test_unknown_or_failed_capability_only_exposes_auto():
    capability_service = importlib.import_module("services.ai_reasoning_service")

    unknown = capability_service.resolve_reasoning_control("openai", "future-unknown-model")
    failed = capability_service.failed_reasoning_control(
        RuntimeError("Bearer sk-live-secret at https://internal.provider/v1/models")
    )

    assert unknown == {
        "kind": "none",
        "options": ["auto"],
        "provider_default": None,
        "mandatory": False,
        "source": "unknown",
        "status": "unknown",
    }
    assert failed["options"] == ["auto"]
    assert failed["status"] == "failed"
    assert failed["error"] == "模型能力获取失败"
    assert "secret" not in json.dumps(failed, ensure_ascii=False)
    assert "internal.provider" not in json.dumps(failed, ensure_ascii=False)


@pytest.mark.parametrize(
    ("provider", "model_name", "reasoning", "expected_fragment", "forbidden_keys"),
    [
        ("openai", "gpt-5.2", "high", {"reasoning_effort": "high"}, []),
        ("openrouter", "openai/gpt-5.2", "high", {"reasoning": {"effort": "high"}}, []),
        ("ollama", "gpt-oss:20b", "medium", {"think": "medium"}, []),
        ("claude", "claude-opus-4-6", "high", {"output_config": {"effort": "high"}}, ["temperature"]),
        ("deepseek", "deepseek-chat", "on", {"thinking": {"type": "enabled"}}, ["temperature"]),
        ("dashscope", "qwen3-max", "on", {"enable_thinking": True}, []),
        ("volcengine", "doubao-seed-1-6-thinking", "off", {"thinking": {"type": "disabled"}}, []),
        ("zhipu", "glm-5", "xhigh", {"reasoning_effort": "xhigh"}, []),
        ("moonshot", "kimi-k3", "max", {"reasoning_effort": "max"}, []),
        ("qianfan", "ernie-4.5-turbo-128k-thinking", "on", {"thinking": {"type": "enabled"}}, []),
        ("hunyuan", "hunyuan-t1", "low", {"reasoning_effort": "low"}, []),
        ("minimax", "MiniMax-M2.1", "auto", {}, ["reasoning", "reasoning_effort", "think"]),
    ],
)
def test_provider_payload_maps_reasoning_without_approximation(
    db_session,
    provider,
    model_name,
    reasoning,
    expected_fragment,
    forbidden_keys,
):
    ai_client = importlib.import_module("services.ai_client")
    model = _seed_model(
        db_session,
        name=f"{provider}-{model_name}",
        provider=provider,
        model_name=model_name,
    )

    payload = ai_client._provider_payload(
        model,
        [{"role": "user", "content": "hello"}],
        [],
        stream=False,
        reasoning=reasoning,
    )

    for key, value in expected_fragment.items():
        assert payload[key] == value
    for key in forbidden_keys:
        assert key not in payload


def test_ai_models_response_exposes_default_and_reasoning_contract(db_session):
    _seed_user(db_session)
    model = _seed_model(db_session)
    from models import AIPlatformSetting

    db_session.add(AIPlatformSetting(id=1, default_chat_model_id=model.id, updated_by=1))
    db_session.commit()

    item = ai_chat_service.list_available_models(db_session)[0]

    assert item["is_default"] is True
    assert item["reasoning_control"] == {
        "kind": "effort",
        "options": ["auto", "low", "medium", "high"],
        "provider_default": "medium",
        "mandatory": False,
        "source": "official_catalog",
        "status": "ready",
        "updated_at": "2026-07-23T10:00:00",
    }


def test_admin_can_set_default_model_and_omitted_model_uses_it(
    api_client_factory,
    db_session,
):
    _seed_user(db_session)
    model = _seed_model(db_session)
    client = api_client_factory(
        [ai.router, ai_admin.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    initial = client.get("/storage-pulse/api/admin/ai-settings")
    updated = client.patch(
        "/storage-pulse/api/admin/ai-settings",
        json={"default_chat_model_id": model.id},
    )
    created = client.post(
        "/storage-pulse/api/ai/conversations",
        json={"title": "默认模型对话"},
    )

    assert initial.status_code == 200
    assert initial.json()["default_chat_model_id"] is None
    assert updated.status_code == 200
    assert updated.json()["default_chat_model_id"] == model.id
    assert created.status_code == 201
    assert created.json()["model_id"] == model.id


def test_missing_default_model_returns_clear_configuration_error(
    api_client_factory,
    db_session,
):
    _seed_user(db_session)
    client = api_client_factory(
        [ai.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    response = client.post(
        "/storage-pulse/api/ai/conversations",
        json={"title": "没有默认模型"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "管理员尚未配置默认聊天模型"


def test_default_model_cannot_be_disabled_or_deleted(
    api_client_factory,
    db_session,
):
    _seed_user(db_session)
    model = _seed_model(db_session)
    from models import AIPlatformSetting

    db_session.add(AIPlatformSetting(id=1, default_chat_model_id=model.id, updated_by=1))
    db_session.commit()
    client = api_client_factory(
        [ai_admin.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    disabled = client.patch(
        f"/storage-pulse/api/admin/ai-models/{model.id}",
        json={"enabled": False},
    )
    deleted = client.delete(f"/storage-pulse/api/admin/ai-models/{model.id}")

    assert disabled.status_code == 409
    assert disabled.json()["detail"] == "请先更换默认聊天模型"
    assert deleted.status_code == 409
    assert deleted.json()["detail"] == "请先更换默认聊天模型"


def test_unsupported_reasoning_is_rejected_before_provider_call(
    api_client_factory,
    db_session,
    monkeypatch,
):
    _seed_user(db_session)
    model = _seed_model(
        db_session,
        provider="minimax",
        model_name="MiniMax-M2.1",
        control={
            "kind": "none",
            "options": ["auto"],
            "provider_default": None,
            "mandatory": False,
            "source": "official_catalog",
        },
    )
    conversation = AIConversation(user_id=1, model_id=model.id, title="不支持推理档位")
    db_session.add(conversation)
    db_session.commit()
    monkeypatch.setattr(ai, "enforce_ai_rate_limit", lambda _user_id: None)
    provider_called = False

    def should_not_run(*_args, **_kwargs):
        nonlocal provider_called
        provider_called = True
        yield from _completed_stream()

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", should_not_run)
    client = api_client_factory(
        [ai.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    response = client.post(
        f"/storage-pulse/api/ai/conversations/{conversation.id}/messages",
        json={"content": "使用最大推理", "reasoning": "max"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "当前模型不支持推理设置 max"
    assert provider_called is False


def test_message_reasoning_is_persisted_forwarded_and_audited(
    api_client_factory,
    db_session,
    monkeypatch,
):
    _seed_user(db_session)
    model = _seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=model.id, title="逐消息推理")
    db_session.add(conversation)
    db_session.commit()
    monkeypatch.setattr(ai, "enforce_ai_rate_limit", lambda _user_id: None)
    captured = {}

    def capture_reasoning(*_args, **kwargs):
        captured["reasoning"] = kwargs.get("reasoning")
        yield from _completed_stream()

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", capture_reasoning)
    client = api_client_factory(
        [ai.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    response = client.post(
        f"/storage-pulse/api/ai/conversations/{conversation.id}/messages",
        json={"content": "深度分析容量", "reasoning": "high"},
    )

    assert response.status_code == 200
    db_session.expire_all()
    user_message = db_session.scalar(
        select(AIMessage).where(
            AIMessage.conversation_id == conversation.id,
            AIMessage.role == "user",
        )
    )
    audit = db_session.scalar(
        select(AIAuditLog).where(AIAuditLog.conversation_id == conversation.id)
    )
    request_payload = json.loads(audit.request_payload)
    assert captured["reasoning"] == "high"
    assert user_message.reasoning == "high"
    assert request_payload["reasoning_requested"] == "high"
    assert request_payload["reasoning_kind"] == "effort"
    assert request_payload["reasoning_sent"] == "high"
    assert request_payload["content"] == "[REDACTED]"


def test_capability_refresh_failure_is_persisted_and_publicly_sanitized(
    api_client_factory,
    db_session,
    monkeypatch,
):
    _seed_user(db_session)
    model = _seed_model(db_session)

    def fail_discovery(_model):
        raise RuntimeError(
            "Bearer sk-live-secret failed at https://internal.provider/v1/models"
        )

    monkeypatch.setattr(
        ai_config_service,
        "discover_model_capabilities",
        fail_discovery,
        raising=False,
    )
    client = api_client_factory(
        [ai_admin.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    response = client.post(
        f"/storage-pulse/api/admin/ai-models/{model.id}/capabilities/refresh"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reasoning_control"]["options"] == ["auto"]
    assert body["reasoning_control"]["status"] == "failed"
    assert body["capability_error"] == "模型能力获取失败"
    assert "sk-live-secret" not in response.text
    assert "internal.provider" not in response.text
    db_session.expire_all()
    refreshed = db_session.get(AIConfig, model.id)
    assert refreshed.capability_status == "failed"
    assert refreshed.capability_error == "模型能力获取失败"


def test_claude_code_options_only_expose_diskpulse_mcp_tools_and_safe_log_view(
    db_session,
):
    adapter = importlib.import_module("services.claude_code_adapter")
    model = _seed_model(
        db_session,
        provider="claude_code",
        model_name="claude-opus-4-6",
    )

    options = adapter.build_claude_code_options(
        model,
        tool_names=["get_capacity", "get_incident_diagnosis"],
        reasoning="high",
    )
    safe_view = adapter.safe_options_for_log(options)

    assert options["tools"] == []
    assert list(options["mcp_servers"]) == ["diskpulse"]
    assert options["allowed_tools"] == [
        "mcp__diskpulse__get_capacity",
        "mcp__diskpulse__get_incident_diagnosis",
    ]
    assert options["effort"] == "high"
    assert options["env"]["ANTHROPIC_API_KEY"] == "secret-key-1234"
    assert "ANTHROPIC_API_KEY" not in safe_view
    assert "secret-key-1234" not in json.dumps(safe_view, ensure_ascii=False)
