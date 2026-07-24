# -*- coding: utf-8 -*-
import importlib
import asyncio
import json
from queue import Queue
from threading import Event
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import httpx
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import select

from appConfig import base_config
from models import AIConfig, AIConversation, AIAuditLog, AIMessage, User
from routers import ai, ai_admin
from schemas.aiSchema import AIModelCreate, AIModelPatch, ConversationCreate, MessageCreate
from services import ai_chat_service, ai_config_service
from services.ai_client import AIClientError, AICompletionStreamEvent
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
    model.capability_updated_at = datetime(2026, 7, 23, 10, 0, 0, tzinfo=timezone.utc)
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
        "name_obfuscation_enabled",
        "name_obfuscation_epoch",
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
    migration_sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
        if "ai_platform_settings" in path.read_text(encoding="utf-8")
    }
    reasoning_sources = [
        source for source in migration_sources.values() if "capability_cache" in source
    ]
    assert len(reasoning_sources) == 1
    assert "reasoning" in reasoning_sources[0]
    obfuscation_sources = [
        source for source in migration_sources.values()
        if "ai_conversation_name_aliases" in source
    ]
    # Later migrations may alter the same settings table; require the feature
    # migration itself instead of treating it as the permanent Alembic head.
    assert any("000000000024" in source for source in obfuscation_sources)
    assert "name_obfuscation_enabled" in obfuscation_sources[0]


@pytest.mark.parametrize(
    ("provider", "model_name", "expected_kind", "expected_options"),
    [
        ("openai", "gpt-5.2", "effort", ["auto", "none", "low", "medium", "high", "xhigh"]),
        ("ollama", "gpt-oss:20b", "effort", ["auto", "low", "medium", "high"]),
        ("deepseek", "deepseek-reasoner", "effort", ["auto", "high", "max"]),
        ("deepseek", "deepseek-v4-pro", "effort", ["auto", "high", "max"]),
        ("deepseek", "deepseek-v4-flash", "effort", ["auto", "high", "max"]),
        ("dashscope", "qwen3-max", "toggle", ["auto", "off", "on"]),
        ("volcengine", "doubao-seed-1-6-thinking", "toggle", ["auto", "off", "on"]),
        ("zhipu", "glm-5", "effort", ["auto", "minimal", "low", "medium", "high", "xhigh"]),
        ("moonshot", "kimi-k3", "effort", ["auto", "low", "high", "max"]),
        ("minimax", "MiniMax-M2.1", "none", ["auto"]),
        ("qianfan", "ernie-4.5-turbo-128k-thinking", "toggle", ["auto", "off", "on"]),
        ("hunyuan", "hunyuan-t1", "effort", ["auto", "low", "medium", "high"]),
        ("hunyuan", "hy3-preview", "effort", ["auto", "low", "medium", "high"]),
        ("qianfan", "deepseek-v4-pro", "effort", ["auto", "high", "max"]),
        ("qianfan", "deepseek-v4-flash", "effort", ["auto", "high", "max"]),
        ("qianfan", "gpt-oss-120b", "effort", ["auto", "low", "medium", "high"]),
        ("qianfan", "qwen3-max", "toggle", ["auto", "off", "on"]),
        ("zhipu", "glm-4.7-flash", "toggle", ["auto", "off", "on"]),
        ("moonshot", "kimi-k2.5", "toggle", ["auto", "off", "on"]),
        ("hunyuan", "deepseek-v4-pro", "effort", ["auto", "low", "medium", "high"]),
        ("hunyuan", "deepseek-v3.2", "effort", ["auto", "low", "medium", "high"]),
        ("hunyuan", "glm-5.2", "toggle", ["auto", "off", "on"]),
        ("hunyuan", "kimi-k2.6", "toggle", ["auto", "off", "on"]),
        ("hunyuan", "qwen3.5-plus", "toggle", ["auto", "off", "on"]),
        ("hunyuan", "minimax-m3", "toggle", ["auto", "off", "on"]),
        ("hunyuan", "kimi-k2.7-code", "toggle", ["auto", "on"]),
        ("hunyuan", "minimax-m2.7", "toggle", ["auto", "on"]),
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
        (
            "qianfan",
            "qwen3-max",
            "on",
            {"enable_thinking": True},
            ["thinking", "reasoning_effort"],
        ),
        (
            "qianfan",
            "deepseek-v4-pro",
            "max",
            {"reasoning_effort": "max"},
            ["thinking", "enable_thinking"],
        ),
        (
            "qianfan",
            "gpt-oss-120b",
            "medium",
            {"reasoning_effort": "medium"},
            ["thinking", "enable_thinking"],
        ),
        ("hunyuan", "hunyuan-t1", "low", {"reasoning_effort": "low"}, []),
        (
            "zhipu",
            "glm-4.7-flash",
            "on",
            {"thinking": {"type": "enabled"}},
            ["reasoning_effort", "enable_thinking"],
        ),
        (
            "moonshot",
            "kimi-k2.5",
            "off",
            {"thinking": {"type": "disabled"}},
            ["reasoning_effort", "enable_thinking"],
        ),
        (
            "hunyuan",
            "glm-5.2",
            "on",
            {"thinking": {"type": "enabled"}},
            ["reasoning_effort", "enable_thinking"],
        ),
        (
            "hunyuan",
            "qwen3.5-plus",
            "off",
            {"enable_thinking": False},
            ["reasoning_effort", "thinking"],
        ),
        (
            "hunyuan",
            "minimax-m3",
            "on",
            {"thinking": {"type": "adaptive"}},
            ["reasoning_effort", "enable_thinking"],
        ),
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
        "updated_at": "2026-07-23T10:00:00+00:00",
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
    obfuscation_disabled = client.patch(
        "/storage-pulse/api/admin/ai-settings",
        json={"name_obfuscation_enabled": False},
    )
    created = client.post(
        "/storage-pulse/api/ai/conversations",
        json={"title": "默认模型对话"},
    )

    assert initial.status_code == 200
    assert initial.json()["default_chat_model_id"] is None
    assert initial.json()["name_obfuscation_enabled"] is True
    assert updated.status_code == 200
    assert updated.json()["default_chat_model_id"] == model.id
    assert updated.json()["name_obfuscation_enabled"] is True
    assert obfuscation_disabled.status_code == 200
    assert obfuscation_disabled.json()["default_chat_model_id"] == model.id
    assert obfuscation_disabled.json()["name_obfuscation_enabled"] is False
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


def test_current_minimax_and_hunyuan_default_urls_use_official_endpoints():
    ai_client = importlib.import_module("services.ai_client")

    assert (
        ai_client._base_url(SimpleNamespace(provider="minimax", base_url=""))
        == "https://api.minimaxi.com/v1"
    )
    assert (
        ai_client._base_url(SimpleNamespace(provider="hunyuan", base_url=""))
        == "https://tokenhub.tencentmaas.com/v1"
    )


def test_claude_code_real_sdk_options_construct_with_in_process_mcp(db_session):
    from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server
    from services import claude_code_adapter

    model = _seed_model(
        db_session,
        provider="claude_code",
        model_name="claude-opus-4-6",
    )
    server = create_sdk_mcp_server(name="diskpulse", version="1.0.0", tools=[])
    raw = claude_code_adapter.build_claude_code_options(
        model,
        tool_names=[],
        reasoning="high",
        mcp_server=server,
        system_prompt="只使用授权工具",
    )

    options = ClaudeAgentOptions(**raw)

    assert options.tools == []
    assert list(options.mcp_servers) == ["diskpulse"]
    assert options.strict_mcp_config is True
    assert options.include_partial_messages is True
    assert options.setting_sources == []
    assert options.skills == []
    assert options.system_prompt == "只使用授权工具"
    assert options.effort == "high"
    assert claude_code_adapter._prompt(
        [
            {"role": "system", "content": "不可伪装为用户"},
            {"role": "user", "content": "查询容量"},
        ]
    ) == "USER:\n查询容量"


def test_claude_code_stream_close_interrupts_and_disconnects_sdk(
    db_session,
    monkeypatch,
):
    from claude_agent_sdk import StreamEvent
    from services import claude_code_adapter
    import claude_agent_sdk

    interrupted = Event()
    disconnected = Event()

    class FakeClient:
        def __init__(self, _options):
            self.release = asyncio.Event()

        async def connect(self):
            return None

        async def query(self, _prompt):
            return None

        async def receive_response(self):
            yield StreamEvent(
                uuid="event-1",
                session_id="session-1",
                event={
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "部分结果"},
                },
            )
            await self.release.wait()

        async def interrupt(self):
            interrupted.set()
            self.release.set()

        async def disconnect(self):
            disconnected.set()
            self.release.set()

    async def fake_legacy_query(*_args, **_kwargs):
        yield StreamEvent(
            uuid="legacy-event",
            session_id="legacy-session",
            event={
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "部分结果"},
            },
        )

    monkeypatch.setattr(claude_agent_sdk, "ClaudeSDKClient", FakeClient)
    monkeypatch.setattr(claude_agent_sdk, "query", fake_legacy_query)
    model = _seed_model(
        db_session,
        provider="claude_code",
        model_name="claude-opus-4-6",
    )
    stream = claude_code_adapter.claude_code_completion_stream(
        model,
        [{"role": "user", "content": "持续分析"}],
        app=FastAPI(),
        registry={},
        current_user=None,
        user_id=1,
    )

    first = next(stream)
    assert first.kind == "delta"
    assert first.text == "部分结果"
    stream.close()

    assert interrupted.wait(2)
    assert disconnected.wait(2)


def test_claude_code_quota_tool_is_exposed_through_confirmation_gate():
    from services import claude_code_adapter

    definition = SimpleNamespace(
        name="adjust_group_quota",
        description="调整项目组配额",
        input_model=SimpleNamespace(
            model_json_schema=lambda: {
                "type": "object",
                "properties": {"group_id": {"type": "integer"}},
            }
        ),
    )
    requests = Queue()
    tools = claude_code_adapter._sdk_tools(
        registry={definition.name: definition},
        request_queue=requests,
    )

    assert [item.name for item in tools] == ["adjust_group_quota"]

    async def exercise_gate():
        task = asyncio.create_task(tools[0].handler({"group_id": 7}))
        request = await asyncio.to_thread(requests.get, True, 1)
        assert request.tool_name == "adjust_group_quota"
        assert request.arguments == {"group_id": 7}
        request.respond(
            {
                "ok": True,
                "data": {
                    "confirmation_required": {
                        "confirmation_id": "confirm-1",
                    }
                },
            }
        )
        return await task

    result = asyncio.run(exercise_gate())
    payload = json.loads(result["content"][0]["text"])
    assert payload["data"]["confirmation_required"]["confirmation_id"] == "confirm-1"


@pytest.mark.parametrize(
    ("model_name", "expected_options"),
    [
        ("gpt-5", ["auto", "minimal", "low", "medium", "high"]),
        ("gpt-5-2025-08-07", ["auto", "minimal", "low", "medium", "high"]),
        ("gpt-5.1", ["auto", "none", "low", "medium", "high"]),
        ("gpt-5.2-2025-12-11", ["auto", "none", "low", "medium", "high", "xhigh"]),
        ("gpt-5.4", ["auto", "none", "low", "medium", "high", "xhigh"]),
        ("gpt-5.4-mini-2026-03-17", ["auto", "none", "low", "medium", "high", "xhigh"]),
        ("gpt-5.5", ["auto", "none", "low", "medium", "high", "xhigh"]),
        ("gpt-5.5-2026-04-23", ["auto", "none", "low", "medium", "high", "xhigh"]),
        ("gpt-5.6", ["auto", "none", "low", "medium", "high", "xhigh", "max"]),
        ("gpt-5.6-terra", ["auto", "none", "low", "medium", "high", "xhigh", "max"]),
    ],
)
def test_openai_chat_completion_catalog_uses_explicit_current_families(
    model_name,
    expected_options,
):
    capability_service = importlib.import_module("services.ai_reasoning_service")

    control = capability_service.resolve_reasoning_control("openai", model_name)

    assert control["kind"] == "effort"
    assert control["options"] == expected_options


@pytest.mark.parametrize(
    "model_name",
    ["gpt-5.2-pro", "gpt-5.4-pro", "gpt-5.5-pro", "gpt-5.99"],
)
def test_openai_responses_only_or_unknown_models_are_not_claimed_for_chat(model_name):
    capability_service = importlib.import_module("services.ai_reasoning_service")

    control = capability_service.resolve_reasoning_control("openai", model_name)

    assert control["kind"] == "none"
    assert control["options"] == ["auto"]


def test_minimax_protocol_is_selected_only_by_explicit_anthropic_base(db_session):
    ai_client = importlib.import_module("services.ai_client")
    openai_model = _seed_model(
        db_session,
        name="minimax-openai",
        provider="minimax",
        model_name="MiniMax-M2.1",
    )
    anthropic_model = _seed_model(
        db_session,
        name="minimax-anthropic",
        provider="minimax",
        model_name="MiniMax-M2.1",
    )
    anthropic_model.base_url = "https://api.minimaxi.com/anthropic"

    openai_payload = ai_client._provider_payload(
        openai_model,
        [{"role": "system", "content": "system"}, {"role": "user", "content": "q"}],
        [],
        stream=False,
    )
    anthropic_payload = ai_client._provider_payload(
        anthropic_model,
        [{"role": "system", "content": "system"}, {"role": "user", "content": "q"}],
        [],
        stream=False,
    )

    assert ai_client.provider_protocol(openai_model) == "openai"
    assert ai_client.provider_protocol(anthropic_model) == "claude"
    assert openai_payload["messages"][0]["role"] == "system"
    assert anthropic_payload["system"] == "system"
    assert anthropic_payload["messages"] == [{"role": "user", "content": "q"}]
    assert "x-api-key" in ai_client._headers(anthropic_model)
    assert "Authorization" not in ai_client._headers(anthropic_model)


@pytest.mark.parametrize(
    ("provider", "model_name", "reasoning", "expected"),
    [
        ("openrouter", "openai/gpt-5.2", "high", {"effort": "high"}),
        ("ollama", "thinking-model", "on", True),
        ("claude", "claude-opus-4-6", "high", {"effort": "high"}),
        ("dashscope", "qwen3-max", "off", False),
        ("zhipu", "glm-4.7-flash", "on", {"type": "enabled"}),
    ],
)
def test_reasoning_wire_value_matches_the_actual_provider_control(
    db_session,
    provider,
    model_name,
    reasoning,
    expected,
):
    ai_client = importlib.import_module("services.ai_client")
    model = _seed_model(
        db_session,
        name=f"wire-{provider}",
        provider=provider,
        model_name=model_name,
    )

    assert ai_client.reasoning_wire_value(model, reasoning) == expected
    assert ai_client.reasoning_wire_value(model, "auto") is None


def test_audit_persists_openrouter_wire_reasoning_value(
    db_session,
    monkeypatch,
):
    _seed_user(db_session)
    model = _seed_model(
        db_session,
        provider="openrouter",
        model_name="openai/gpt-5.2",
    )
    conversation = AIConversation(
        user_id=1,
        model_id=model.id,
        title="OpenRouter 审计",
    )
    db_session.add(conversation)
    db_session.commit()
    monkeypatch.setattr(
        ai_chat_service,
        "chat_completion_stream",
        _completed_stream,
    )

    list(
        ai_chat_service.stream_message(
            app=FastAPI(),
            db=db_session,
            conversation_id=conversation.id,
            user_id=1,
            content="深度分析",
            reasoning="high",
        )
    )

    audit = db_session.scalar(
        select(AIAuditLog).where(AIAuditLog.conversation_id == conversation.id)
    )
    request_payload = json.loads(audit.request_payload)
    assert request_payload["reasoning_requested"] == "high"
    assert request_payload["reasoning_kind"] == "effort"
    assert request_payload["reasoning_sent"] == {"effort": "high"}


def test_capability_refresh_failure_is_sanitized_and_forces_auto(
    db_session,
    monkeypatch,
):
    model = _seed_model(db_session, provider="openrouter", model_name="openai/gpt-5.2")

    def boom(_model):
        raise RuntimeError("secret-key-1234 leaked provider detail")

    monkeypatch.setattr(ai_config_service, "discover_model_capabilities", boom)

    result = ai_config_service.refresh_model_capabilities(db_session, model)

    assert result["capability_status"] == "failed"
    assert result["capability_error"] == "模型能力获取失败"
    assert "secret-key-1234" not in result["capability_error"]
    assert result["reasoning_control"]["kind"] == "none"
    assert result["reasoning_control"]["options"] == ["auto"]


def test_default_model_cannot_be_disabled_or_deleted(db_session):
    model = _seed_model(db_session)
    ai_config_service.update_platform_settings(db_session, model.id, actor_id=1)

    with pytest.raises(Exception) as disable_error:
        ai_config_service.update_model(
            db_session,
            model.id,
            AIModelPatch(enabled=False),
            actor_id=1,
        )
    assert getattr(disable_error.value, "status_code", None) == 409

    with pytest.raises(Exception) as delete_error:
        ai_config_service.delete_model(db_session, model.id)
    assert getattr(delete_error.value, "status_code", None) == 409


def test_platform_default_rejects_disabled_or_chat_forbidden_models(db_session):
    disabled = _seed_model(db_session, name="disabled", model_name="gpt-5.1")
    disabled.enabled = False
    chat_forbidden = _seed_model(db_session, name="no-chat", model_name="gpt-5.4")
    chat_forbidden.enable_chat = False
    db_session.commit()

    for model_id in (disabled.id, chat_forbidden.id, 404):
        with pytest.raises(Exception) as error:
            ai_config_service.update_platform_settings(
                db_session,
                model_id,
                actor_id=1,
            )
        assert getattr(error.value, "status_code", None) == 422


def test_ai_client_error_mapping_and_empty_base_url(db_session, monkeypatch):
    ai_client = importlib.import_module("services.ai_client")
    model = _seed_model(db_session, provider="unknown-provider", model_name="model")
    model.base_url = ""

    with pytest.raises(AIClientError):
        ai_client.chat_completion(model, [{"role": "user", "content": "q"}])

    model.provider = "openai"

    def timeout_post(*_args, **_kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(ai_client.httpx, "post", timeout_post)

    with pytest.raises(AIClientError) as error:
        ai_client.chat_completion(model, [{"role": "user", "content": "q"}])
    assert "超时" in str(error.value)


def test_ai_client_stream_dispatches_claude_code_and_wraps_bad_json(
    db_session,
    monkeypatch,
):
    ai_client = importlib.import_module("services.ai_client")
    model = _seed_model(db_session, provider="claude_code", model_name="claude-opus-4-6")
    seen = {}

    def fake_stream(config, messages, **kwargs):
        seen["reasoning"] = kwargs["reasoning"]
        yield AICompletionStreamEvent(kind="completed", text="ok", tool_calls=[])

    import services.claude_code_adapter as claude_code_adapter

    monkeypatch.setattr(
        claude_code_adapter,
        "claude_code_completion_stream",
        fake_stream,
    )

    events = list(
        ai_client.chat_completion_stream(
            model,
            [{"role": "user", "content": "q"}],
            reasoning="high",
        )
    )

    assert events[-1].text == "ok"
    assert seen["reasoning"] == "high"

    def bad_stream(*_args, **_kwargs):
        raise ValueError("bad provider payload")
        yield

    monkeypatch.setattr(
        claude_code_adapter,
        "claude_code_completion_stream",
        bad_stream,
    )

    with pytest.raises(AIClientError):
        list(ai_client.chat_completion_stream(model, [{"role": "user", "content": "q"}]))


def test_claude_code_log_options_do_not_expose_api_key(db_session):
    from services import claude_code_adapter

    model = _seed_model(
        db_session,
        provider="claude_code",
        model_name="claude-opus-4-6",
    )
    options = claude_code_adapter.build_claude_code_options(
        model,
        tool_names=["read_metric"],
        reasoning="high",
        system_prompt="system",
    )
    safe = claude_code_adapter.safe_options_for_log(options)

    assert options["env"]["ANTHROPIC_API_KEY"] == "secret-key-1234"
    assert "env" not in safe
    assert safe["allowed_tools"] == ["mcp__diskpulse__read_metric"]
    assert safe["effort"] == "high"
    assert safe["strict_mcp_config"] is True


def test_claude_code_default_tool_handler_blocks_quota_writes(monkeypatch):
    from services import claude_code_adapter
    from services import ai_quota_confirmation_service, ai_tool_service

    monkeypatch.setattr(
        ai_quota_confirmation_service,
        "is_quota_write_tool",
        lambda name: name == "quota_write",
    )
    monkeypatch.setattr(
        ai_tool_service,
        "execute_tool",
        lambda **kwargs: {"ok": True, "tool": kwargs["tool_name"]},
    )

    blocked = claude_code_adapter._default_tool_handler(
        app=FastAPI(),
        registry={},
        current_user=None,
        user_id=1,
        tool_name="quota_write",
        arguments={},
    )
    allowed = claude_code_adapter._default_tool_handler(
        app=FastAPI(),
        registry={},
        current_user=None,
        user_id=1,
        tool_name="read_only",
        arguments={},
    )

    assert blocked["ok"] is False
    assert "确认" in blocked["error"]
    assert allowed == {"ok": True, "tool": "read_only"}


def test_claude_code_client_state_cancel_handles_missing_and_failing_client():
    from services import claude_code_adapter

    state = claude_code_adapter._ClientState()
    state.cancel()
    assert state.cancelled.is_set()

    class FakeLoop:
        def is_closed(self):
            return True

    state = claude_code_adapter._ClientState()
    state.bind(FakeLoop(), object())
    state.cancel()
    assert state.cancelled.is_set()


def test_dynamic_capability_discovery_reads_openrouter_and_claude_metadata(
    db_session,
    monkeypatch,
):
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            calls.append("raise")

        def json(self):
            return self._payload

    def fake_get(url, **_kwargs):
        calls.append(url)
        if "/v1/models/" in url:
            return FakeResponse(
                {
                    "capabilities": {
                        "effort": {
                            "supported_efforts": ["low", "high"],
                            "default_effort": "high",
                        }
                    }
                }
            )
        return FakeResponse(
            {
                "data": [
                    {
                        "id": "openai/gpt-5.2",
                        "reasoning": {
                            "supported_efforts": ["low", "medium"],
                            "default_effort": "medium",
                            "mandatory": True,
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr(ai_config_service.httpx, "get", fake_get)
    openrouter = _seed_model(
        db_session,
        name="dynamic-openrouter",
        provider="openrouter",
        model_name="openai/gpt-5.2",
    )
    claude = _seed_model(
        db_session,
        name="dynamic-claude",
        provider="claude",
        model_name="claude-opus-4-6",
    )

    openrouter_control = ai_config_service.discover_model_capabilities(openrouter)
    claude_control = ai_config_service.discover_model_capabilities(claude)

    assert openrouter_control["source"] == "provider"
    assert openrouter_control["mandatory"] is True
    assert openrouter_control["options"] == ["auto", "low", "medium"]
    assert claude_control["source"] == "provider"
    assert claude_control["provider_default"] == "high"


def test_delete_model_success_removes_non_default_model(db_session):
    model = _seed_model(db_session, name="delete-me", model_name="gpt-5.1")

    ai_config_service.delete_model(db_session, model.id)

    assert db_session.get(AIConfig, model.id) is None


def test_test_model_uses_claude_code_adapter_and_refreshes_capability(
    db_session,
    monkeypatch,
):
    model = _seed_model(
        db_session,
        name="test-claude-code",
        provider="claude_code",
        model_name="claude-opus-4-6",
    )
    refreshed = []

    def fake_stream(*_args, **_kwargs):
        yield AICompletionStreamEvent(kind="delta", text="o")
        yield AICompletionStreamEvent(kind="completed", text="ok", tool_calls=[])

    import services.claude_code_adapter as claude_code_adapter

    monkeypatch.setattr(
        claude_code_adapter,
        "claude_code_completion_stream",
        fake_stream,
    )
    monkeypatch.setattr(
        ai_config_service,
        "_refresh_dynamic_capability",
        lambda _db, refreshed_model: refreshed.append(refreshed_model.id),
    )

    result = ai_config_service.test_model(db_session, model.id)

    assert result["ok"] is True
    assert result["reply"] == "ok"
    assert refreshed == [model.id]


def test_ollama_chat_completion_parses_native_tool_calls(db_session, monkeypatch):
    ai_client = importlib.import_module("services.ai_client")
    model = _seed_model(
        db_session,
        name="ollama-chat",
        provider="ollama",
        model_name="llama3.2",
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "read_metric",
                                "arguments": {"metric": "cpu"},
                            }
                        }
                    ],
                }
            }

    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return FakeResponse()

    monkeypatch.setattr(ai_client.httpx, "post", fake_post)

    result = ai_client.chat_completion(
        model,
        [{"role": "user", "content": "q"}],
        tools=[{"type": "function", "function": {"name": "read_metric"}}],
        reasoning="on",
    )

    assert captured["url"].endswith("/api/chat")
    assert captured["json"]["think"] is True
    assert result.stop_reason == "tool_calls"
    assert result.tool_calls[0].arguments == {"metric": "cpu"}
