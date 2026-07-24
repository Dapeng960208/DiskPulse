# -*- coding: utf-8 -*-
import importlib.util
import json
import io
import logging
from pathlib import Path
import re

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import APIRouter, FastAPI, Response
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from appConfig import base_config
from dependencies import get_current_user, get_db, require_super_admin
from models import (
    AIConfig,
    AIConversation,
    AIConversationNameAlias,
    AIAuditLog,
    AIMessage,
    Group,
    GroupTag,
    Project,
    ProjectMembership,
    StorageCluster,
    User,
)
from routers import (
    aggregate,
    ai,
    ai_admin,
    audit_events,
    config,
    forecast_incidents,
    group,
    group_tag,
    large_files,
    projects,
    qtrees,
    storage_back_up_records,
    storage_alerts,
    storage_cluster,
    storage_usage,
    users,
    volumes,
)
from schemas.aiSchema import AIModelCreate, AIModelPatch
from schemas import usersSchema
from services import ai_chat_service
from services import ai_config_service
from services import quotaService
from services.ai_client import AIClientError, AIClientToolCall, AICompletionResult
from services.ai_client import AICompletionStreamEvent
from services.ai_rate_limit import enforce_ai_rate_limit
from services.ai_security import decrypt_secret, encrypt_secret, mask_secret
from services.ai_tool_service import _input_model, build_tool_registry, execute_tool
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


def test_platform_settings_enable_name_obfuscation_by_default(db_session):
    settings = ai_config_service.get_platform_settings(db_session)

    assert settings["name_obfuscation_enabled"] is True


def test_name_obfuscation_alias_is_encrypted_and_survives_resource_deletion(db_session):
    from services.ai_name_obfuscation_service import prepare_name_obfuscator

    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    user = _seed_user(db_session)
    model = _seed_model(db_session)
    project_name = "项目-待删除"
    project = Project(id=102, name=project_name)
    root_project = Project(id=103, name="项目")
    conversation = AIConversation(user_id=user.id, model_id=model.id, title="别名续聊")
    db_session.add_all([
        project,
        root_project,
        ProjectMembership(project_id=project.id, user_id=user.id, role="reader"),
        ProjectMembership(project_id=root_project.id, user_id=user.id, role="reader"),
        conversation,
    ])
    db_session.commit()
    message = AIMessage(conversation_id=conversation.id, role="user", content=project_name)
    db_session.add(message)
    db_session.commit()

    obfuscator = prepare_name_obfuscator(
        db_session,
        conversation=conversation,
        current_user=user,
        current_message_id=message.id,
        epoch=1,
    )
    alias = obfuscator.obfuscate_text(project_name)
    overlapping_text = f"{project_name} 归属 {root_project.name}"
    obfuscated_overlapping_text = obfuscator.obfuscate_text(overlapping_text)
    obfuscator.persist()
    stored = db_session.scalar(select(AIConversationNameAlias))

    assert alias.startswith("项目-")
    assert obfuscator.restore_text(obfuscated_overlapping_text) == overlapping_text
    assert project_name not in stored.original_value_encrypted
    assert decrypt_secret(stored.original_value_encrypted) == project_name

    db_session.delete(project)
    db_session.commit()
    resumed = prepare_name_obfuscator(
        db_session,
        conversation=conversation,
        current_user=user,
        current_message_id=message.id,
        epoch=1,
    )

    assert resumed.obfuscate_text(project_name) == alias
    assert resumed.restore_text(alias) == project_name


def test_name_obfuscation_switch_is_partial_and_new_enablement_starts_next_epoch(db_session):
    user = _seed_user(db_session)
    model = _seed_model(db_session)

    initial = ai_config_service.update_platform_settings(
        db_session,
        default_chat_model_id=model.id,
        actor_id=user.id,
    )
    disabled = ai_config_service.update_platform_settings(
        db_session,
        actor_id=user.id,
        name_obfuscation_enabled=False,
    )
    enabled = ai_config_service.update_platform_settings(
        db_session,
        actor_id=user.id,
        name_obfuscation_enabled=True,
    )

    assert initial["default_chat_model_id"] == model.id
    assert disabled["default_chat_model_id"] == model.id
    assert disabled["name_obfuscation_enabled"] is False
    assert enabled["default_chat_model_id"] == model.id
    assert enabled["name_obfuscation_enabled"] is True
    assert ai_config_service.get_name_obfuscation_state(db_session) == (True, 2)


def test_name_obfuscation_failure_prevents_provider_call(db_session, monkeypatch):
    from services.ai_name_obfuscation_service import NameObfuscationError

    user = _seed_user(db_session)
    model = _seed_model(db_session)
    conversation = AIConversation(user_id=user.id, model_id=model.id, title="安全失败")
    db_session.add(conversation)
    db_session.commit()
    provider_calls = []

    def broken_obfuscator(*_args, **_kwargs):
        raise NameObfuscationError("映射不可用")

    def provider_stream(*_args, **_kwargs):
        provider_calls.append(True)
        yield AICompletionStreamEvent(kind="completed", text="不应调用", tool_calls=[])

    monkeypatch.setattr(ai_chat_service, "prepare_name_obfuscator", broken_obfuscator)
    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)

    events = list(
        ai_chat_service.stream_message(
            app=FastAPI(),
            db=db_session,
            conversation_id=conversation.id,
            user_id=user.id,
            current_user=user,
            content="映射故障时不发送",
        )
    )

    assert provider_calls == []
    assert events[-1][0] == "error"


def test_chat_obfuscates_nested_tool_names_and_restores_tool_execution_and_sse(
    db_session,
    monkeypatch,
):
    user = _seed_user(db_session)
    model = _seed_model(db_session)
    conversation = AIConversation(user_id=user.id, model_id=model.id, title="名称混淆")
    project = Project(id=101, name="项目-星河")
    cluster = StorageCluster(id=201, name="集群-北斗", storage_type="netapp")
    group_tag = GroupTag(id=251, name="研发标签")
    group = Group(
        id=301,
        project_id=project.id,
        storage_cluster_id=cluster.id,
        group_tag_id=group_tag.id,
        name="项目组-研发",
        enable_monitoring=False,
    )
    membership = ProjectMembership(project_id=project.id, user_id=user.id, role="reader")
    db_session.add_all([conversation, project, cluster, group_tag, group, membership])
    db_session.commit()
    db_session.refresh(conversation)

    app = FastAPI()
    router = APIRouter()
    executed_arguments = []

    @router.get(
        "/resources/{resource_name}",
        openapi_extra={
            "ai_exposed": True,
            "ai_name": "get_named_resource",
            "ai_description": "查询命名资源",
        },
    )
    def get_named_resource(resource_name: str):
        executed_arguments.append(resource_name)
        return {
            "data": {
                "name": project.name,
                "children": [
                    {
                        "name": cluster.name,
                        "used_ratio": 16.03,
                        "children": [{"name": group.name, "used": 0.01}],
                    }
                ],
            }
        }

    app.include_router(router)
    provider_requests = []

    def provider_stream(_model, messages, *, tools=None):
        provider_requests.append(messages)
        serialized = json.dumps(messages, ensure_ascii=False)
        project_alias = re.search(r"项目-[A-Z0-9]{4,}", serialized)
        if len(provider_requests) == 1:
            yield AICompletionStreamEvent(
                kind="completed",
                tool_calls=[
                    AIClientToolCall(
                        tool_id="named-resource",
                        name="get_named_resource",
                        arguments={"resource_name": project_alias.group(0) if project_alias else "项目-UNKNOWN"},
                    )
                ],
                stop_reason="tool_calls",
            )
            return
        assert "used_ratio" in serialized and "16.03" in serialized
        assert "used" in serialized and "0.01" in serialized
        cluster_alias = re.search(r"集群-[A-Z0-9]{4,}", serialized)
        response_text = f"{project_alias.group(0)} 的关联资源是 {cluster_alias.group(0)}"
        yield AICompletionStreamEvent(kind="delta", text=response_text[:7])
        yield AICompletionStreamEvent(kind="delta", text=response_text[7:])
        yield AICompletionStreamEvent(kind="completed", text="", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)
    events = list(
        ai_chat_service.stream_message(
            app=app,
            db=db_session,
            conversation_id=conversation.id,
            user_id=user.id,
            current_user=user,
            content=f"请查询 {project.name} 的关联资源",
        )
    )

    provider_payloads = [json.dumps(messages, ensure_ascii=False) for messages in provider_requests]
    assert all(project.name not in payload for payload in provider_payloads)
    assert all(cluster.name not in payload for payload in provider_payloads)
    assert all(group.name not in payload for payload in provider_payloads)
    assert executed_arguments == [project.name]
    assert all(
        re.search(r"(?:项目|集群)-[A-Z0-9]{4,}", data["text"]) is None
        for event, data in events
        if event == "delta"
    )
    tool_finished = next(data for event, data in events if event == "tool_call_finished")
    assert tool_finished["result"]["data"]["children"][0]["name"] == cluster.name
    completed = next(data for event, data in events if event == "completed")
    assert completed["message"]["content"] == f"{project.name} 的关联资源是 {cluster.name}"


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


def test_all_ai_exposed_route_parameter_schemas_are_unambiguous():
    """Every AI tool field must expose one scalar contract and truthful nullability."""
    from main import app as production_app

    issues = []
    scalar_types = {"array", "boolean", "integer", "number", "object", "string"}

    for route in production_app.routes:
        if not isinstance(route, APIRoute):
            continue
        metadata = route.openapi_extra or {}
        if metadata.get("ai_exposed") is not True:
            continue
        tool_name = metadata.get("ai_name") or route.name
        model, _ = _input_model(tool_name, route)
        schema = model.model_json_schema()
        required = set(schema.get("required") or [])
        for field_name, field_schema in (schema.get("properties") or {}).items():
            branches = [
                field_schema,
                *(field_schema.get("anyOf") or []),
                *(field_schema.get("oneOf") or []),
            ]
            has_model_reference = any(
                isinstance(branch, dict) and "$ref" in branch for branch in branches
            )
            field_types = {
                branch.get("type")
                for branch in branches
                if isinstance(branch, dict) and branch.get("type") in scalar_types
            }
            non_null_types = field_types - {"null"}
            if not non_null_types and not has_model_reference:
                issues.append(f"{tool_name}.{field_name}: missing JSON Schema type")
            elif len(non_null_types) > 1 and non_null_types != {"integer", "number"}:
                issues.append(
                    f"{tool_name}.{field_name}: incompatible types {sorted(non_null_types)}"
                )
            allows_null = any(
                isinstance(branch, dict) and branch.get("type") == "null"
                for branch in branches
            )
            if (
                field_name not in required
                and "default" in field_schema
                and field_schema["default"] is None
                and not allows_null
            ):
                issues.append(
                    f"{tool_name}.{field_name}: defaults to null but schema rejects null"
                )

    assert issues == []


def test_dynamic_tool_registry_filters_route_configured_response_fields():
    app = FastAPI()
    router = APIRouter()
    blacklist_fields = frozenset({"id", "username", "email", "department", "in_charge_user"})

    @router.get(
        "/users",
        openapi_extra={
            "ai_exposed": True,
            "ai_name": "list_safe_users",
            "ai_blacklist_fields": list(blacklist_fields),
        },
    )
    def list_safe_users():
        return {
            "content": [
                {
                    "id": 1,
                    "rd_username": "developer-a",
                    "username": "private-name",
                    "email": "developer-a@example.com",
                    "department": "private-department",
                    "profile": {
                        "id": 2,
                        "rd_username": "developer-b",
                        "username": "private-name-b",
                        "email": "developer-b@example.com",
                    },
                    "in_charge_user": {
                        "rd_username": "project-owner",
                        "username": "private-owner-name",
                    },
                }
            ],
            "total": 1,
        }

    app.include_router(router)
    registry = build_tool_registry(app)

    assert registry["list_safe_users"].blacklist_fields == blacklist_fields
    assert execute_tool(app=app, registry=registry, tool_name="list_safe_users", arguments={}) == {
        "ok": True,
        "data": {
            "items": [
                {
                    "rd_username": "developer-a",
                    "profile": {"rd_username": "developer-b"},
                }
            ],
            "total": 1,
        },
    }


def test_user_project_and_group_tools_configure_privacy_blacklists(monkeypatch):
    app = FastAPI()
    for router in (users.router, projects.router, group.router):
        app.include_router(router)

    original_get = base_config.get

    def configured_get(key, default=None):
        return ["ai-admin"] if key == "super_admin_usernames" else original_get(key, default)

    monkeypatch.setattr(base_config, "get", configured_get)
    admin = User(id=101, username="ai-admin", rd_username="ai-admin")
    registry = build_tool_registry(app, current_user=admin)

    user_response_fields = set(usersSchema.User.model_fields) | set(usersSchema.User.model_computed_fields)
    expected_user_blacklist = frozenset(user_response_fields - {"rd_username"})
    assert registry["list_users"].blacklist_fields == expected_user_blacklist
    assert registry["get_user"].blacklist_fields == expected_user_blacklist
    assert registry["update_user"].blacklist_fields == expected_user_blacklist

    expected_project_blacklist = frozenset({"in_charge_user", "in_charge_user_id", "recipients", "recipient_ids"})
    for tool_name in ("list_projects", "get_project"):
        assert registry[tool_name].blacklist_fields == expected_project_blacklist

    expected_group_blacklist = expected_project_blacklist | {"alert_cc_user_ids", "associated_mail_groups"}
    for tool_name in ("list_groups", "get_group", "get_group_realtime"):
        assert registry[tool_name].blacklist_fields == expected_group_blacklist


def test_sensitive_ai_tools_have_response_blacklists_or_are_not_registered(monkeypatch):
    app = FastAPI()
    for router in (
        aggregate.router,
        ai_admin.router,
        audit_events.router,
        config.router,
        forecast_incidents.router,
        large_files.router,
        qtrees.router,
        storage_alerts.router,
        storage_back_up_records.router,
        storage_cluster.router,
        storage_usage.router,
        volumes.router,
    ):
        app.include_router(router)

    original_get = base_config.get

    def configured_get(key, default=None):
        return ["ai-admin"] if key == "super_admin_usernames" else original_get(key, default)

    monkeypatch.setattr(base_config, "get", configured_get)
    admin = User(id=101, username="ai-admin", rd_username="ai-admin")
    registry = build_tool_registry(app, current_user=admin)

    user_directory_blacklist = frozenset(
        {
            "access",
            "alert_cc_user_ids",
            "associated_mail_groups",
            "back_path",
            "device",
            "gid",
            "in_charge_user",
            "in_charge_user_id",
            "inode",
            "linux_path",
            "user",
            "user_id",
        }
    )
    audit_blacklist = frozenset(
        {"actor", "actor_user_id", "after_summary", "before_summary", "metadata", "resource"}
    )
    storage_alert_blacklist = frozenset({"description", "related_info"})
    storage_config_blacklist = frozenset(
        {
            "back_up_dir",
            "company",
            "domain_name",
            "file_manage_host",
            "file_manage_port",
            "file_manage_user",
            "group_expand",
            "mail_host",
            "mail_port",
            "mail_to",
            "mail_user",
            "person_expand",
        }
    )
    storage_cluster_blacklist = frozenset(
        {
            "isilon_session_cache_mode",
            "isilon_session_cache_path",
            "protocol",
            "storage_host",
            "storage_port",
            "storage_user",
            "tls_verify",
        }
    )
    ai_model_blacklist = frozenset(
        {
            "api_key_configured",
            "api_key_masked",
            "base_url",
            "capability_error",
            "created_by",
            "system_prompt",
            "updated_by",
        }
    )

    for tool_name in ("list_storage_usages", "get_storage_usage", "get_storage_usage_realtime"):
        assert registry[tool_name].blacklist_fields == user_directory_blacklist
    for tool_name in ("list_audit_events", "get_audit_event"):
        assert registry[tool_name].blacklist_fields == audit_blacklist
    assert registry["list_incidents"].blacklist_fields == frozenset({"assigned_user_id"})
    assert registry["list_storage_alerts"].blacklist_fields == storage_alert_blacklist
    assert registry["get_storage_config"].blacklist_fields == storage_config_blacklist
    for tool_name in ("list_ai_models", "create_ai_model", "update_ai_model"):
        assert registry[tool_name].blacklist_fields == ai_model_blacklist
    for tool_name in (
        "list_storage_clusters",
        "create_storage_cluster",
        "get_storage_cluster",
        "update_storage_cluster",
        "get_storage_cluster_realtime",
        "list_aggregates",
        "get_aggregate",
        "get_aggregate_realtime",
        "update_aggregate",
        "list_volumes",
        "get_volume",
        "get_volume_realtime",
        "list_qtrees",
        "get_qtree",
        "get_qtree_realtime",
    ):
        assert registry[tool_name].blacklist_fields == storage_cluster_blacklist

    assert {"list_large_files", "list_storage_backup_records"}.isdisjoint(registry)


def test_cluster_analysis_tools_are_super_admin_only_at_registration_and_execution(monkeypatch):
    app = FastAPI()
    for router in (
        storage_cluster.router,
        aggregate.router,
        volumes.router,
        qtrees.router,
        forecast_incidents.router,
    ):
        app.include_router(router)

    original_get = base_config.get

    def configured_get(key, default=None):
        return ["ai-admin"] if key == "super_admin_usernames" else original_get(key, default)

    monkeypatch.setattr(base_config, "get", configured_get)
    reader = User(id=101, username="reader", rd_username="reader", email="reader@example.com")
    admin = User(id=102, username="ai-admin", rd_username="ai-admin", email="admin@example.com")

    reader_registry = build_tool_registry(app, current_user=reader)
    admin_registry = build_tool_registry(app, current_user=admin)

    expected = {
        "get_storage_cluster_realtime": ("/storage-clusters/{storage_cluster_id}/realtime", "GET"),
        "get_storage_cluster_capacity_change": (
            "/storage-clusters/{storage_cluster_id}/analytics/capacity-change",
            "GET",
        ),
        "get_storage_cluster_error_severity": (
            "/storage-clusters/{storage_cluster_id}/analytics/error-severity",
            "GET",
        ),
        "get_storage_cluster_top_latency": (
            "/storage-clusters/{storage_cluster_id}/analytics/top-latency",
            "GET",
        ),
        "get_storage_cluster_repeated_faults": (
            "/storage-clusters/{storage_cluster_id}/analytics/repeated-faults",
            "GET",
        ),
        "list_storage_cluster_system_events": (
            "/storage-clusters/{storage_cluster_id}/analytics/system-events",
            "GET",
        ),
        "get_storage_cluster_system_event": (
            "/storage-clusters/{storage_cluster_id}/analytics/system-events/{event_id}",
            "GET",
        ),
        "get_aggregate_realtime": ("/aggregates/{aggregate_id}/realtime", "GET"),
        "list_aggregate_storage_trees": ("/aggregates/storage-trees/", "GET"),
        "get_aggregate_storage_tree": ("/aggregates/{aggregate_id}/storage-tree", "GET"),
        "get_volume_realtime": ("/volumes/{volume_id}/realtime", "GET"),
        "list_qtrees": ("/qtrees/", "GET"),
        "get_qtree": ("/qtrees/{qtree_id}", "GET"),
        "get_qtree_realtime": ("/qtrees/{qtree_id}/realtime", "GET"),
        "get_storage_cluster_exhaustion_risk": (
            "/v1/capacity-predictions/{asset_type}/{asset_id}/risk",
            "GET",
        ),
        "list_storage_cluster_forecasts": ("/v1/forecasts", "GET"),
        "list_performance_anomalies": ("/v1/anomalies", "GET"),
        "list_incidents": ("/v1/incidents", "GET"),
        "get_incident_diagnosis": ("/v1/incidents/{incident_id}/diagnosis", "GET"),
    }
    assert not (set(expected) & set(reader_registry))
    assert {
        name: (admin_registry[name].route_path, admin_registry[name].method)
        for name in expected
    } == expected
    assert all(admin_registry[name].system_management is True for name in expected)
    analytics_tools = {
        "get_storage_cluster_capacity_change",
        "get_storage_cluster_error_severity",
        "get_storage_cluster_top_latency",
        "get_storage_cluster_repeated_faults",
        "list_storage_cluster_system_events",
    }
    for name in analytics_tools:
        schema = admin_registry[name].input_model.model_json_schema()
        assert {"start_time", "end_time"} <= set(schema["properties"])
        assert "最近 24 小时" in schema["properties"]["start_time"]["description"]
        assert "最近 24 小时" in schema["properties"]["end_time"]["description"]
        assert {"start_time", "end_time"}.isdisjoint(schema.get("required", []))
        assert admin_registry[name].input_model.model_validate({"storage_cluster_id": 1})
    assert execute_tool(
        app=app,
        registry=admin_registry,
        tool_name="get_storage_cluster_capacity_change",
        arguments={},
        current_user=reader,
    ) == {"ok": False, "error": "系统管理工具仅限超级管理员"}


def test_audit_tools_register_as_read_only_and_execute_with_request_user(db_session, monkeypatch):
    from services import audit_service

    app = FastAPI()
    app.include_router(audit_events.router)
    reader = User(id=101, username="reader", rd_username="reader", email="reader@example.com")
    calls = []
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: reader
    monkeypatch.setattr(
        audit_service,
        "list_visible_audit_events",
        lambda _db, **kwargs: calls.append(kwargs) or ([], 0),
    )
    monkeypatch.setattr(audit_service, "serialize_audit_events", lambda *_args, **_kwargs: [])

    registry = build_tool_registry(app, current_user=reader)

    assert {
        name: (registry[name].route_path, registry[name].method, registry[name].system_management)
        for name in ("list_audit_events", "get_audit_event")
    } == {
        "list_audit_events": ("/v1/audit-events", "GET", False),
        "get_audit_event": ("/v1/audit-events/{event_id}", "GET", False),
    }
    assert execute_tool(
        app=app,
        registry=registry,
        tool_name="list_audit_events",
        arguments={"project_id": 7, "page": 1, "size": 20},
        current_user=reader,
    ) == {"ok": True, "data": {"items": [], "total": 0}}
    assert calls[0]["current_user"] is reader
    assert calls[0]["project_id"] == 7


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
        group.router,
        storage_usage.router,
        forecast_incidents.router,
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
        "list_aggregates": ("/aggregates/", "GET"),
        "get_aggregate": ("/aggregates/{aggregate_id}", "GET"),
        "update_aggregate": ("/aggregates/{aggregate_id}", "PUT"),
        "list_volumes": ("/volumes/", "GET"),
        "get_volume": ("/volumes/{volume_id}", "GET"),
        "get_volume_performance_monitoring": ("/volumes/{volume_id}/monitoring/ai", "GET"),
        "list_group_tags": ("/group-tags", "GET"),
        "create_group_tag": ("/group-tags", "POST"),
        "get_group_tag": ("/group-tags/{group_tag_id}", "GET"),
        "update_group_tag": ("/group-tags/{group_tag_id}", "PUT"),
        "list_users": ("/users/", "GET"),
        "get_user": ("/users/{user_id}", "GET"),
        "update_user": ("/users/{user_id}", "PUT"),
        "list_ai_models": ("/admin/ai-models", "GET"),
        "create_ai_model": ("/admin/ai-models", "POST"),
        "update_ai_model": ("/admin/ai-models/{model_id}", "PATCH"),
        "get_storage_config": ("/config/storage", "GET"),
        "adjust_group_quota": ("/groups/{group_id}/quota", "PATCH"),
        "adjust_storage_usage_quota": ("/storage-usages/{storage_usage_id}/quota", "PATCH"),
        "get_storage_cluster_realtime": ("/storage-clusters/{storage_cluster_id}/realtime", "GET"),
        "get_storage_cluster_capacity_change": (
            "/storage-clusters/{storage_cluster_id}/analytics/capacity-change",
            "GET",
        ),
        "get_storage_cluster_error_severity": (
            "/storage-clusters/{storage_cluster_id}/analytics/error-severity",
            "GET",
        ),
        "get_storage_cluster_top_latency": (
            "/storage-clusters/{storage_cluster_id}/analytics/top-latency",
            "GET",
        ),
        "get_storage_cluster_repeated_faults": (
            "/storage-clusters/{storage_cluster_id}/analytics/repeated-faults",
            "GET",
        ),
        "list_storage_cluster_system_events": (
            "/storage-clusters/{storage_cluster_id}/analytics/system-events",
            "GET",
        ),
        "get_storage_cluster_system_event": (
            "/storage-clusters/{storage_cluster_id}/analytics/system-events/{event_id}",
            "GET",
        ),
        "get_aggregate_realtime": ("/aggregates/{aggregate_id}/realtime", "GET"),
        "list_aggregate_storage_trees": ("/aggregates/storage-trees/", "GET"),
        "get_aggregate_storage_tree": ("/aggregates/{aggregate_id}/storage-tree", "GET"),
        "get_volume_realtime": ("/volumes/{volume_id}/realtime", "GET"),
        "list_qtrees": ("/qtrees/", "GET"),
        "get_qtree": ("/qtrees/{qtree_id}", "GET"),
        "get_qtree_realtime": ("/qtrees/{qtree_id}/realtime", "GET"),
        "get_storage_cluster_exhaustion_risk": (
            "/v1/capacity-predictions/{asset_type}/{asset_id}/risk",
            "GET",
        ),
        "list_storage_cluster_forecasts": ("/v1/forecasts", "GET"),
        "list_performance_anomalies": ("/v1/anomalies", "GET"),
        "list_incidents": ("/v1/incidents", "GET"),
        "get_incident_diagnosis": ("/v1/incidents/{incident_id}/diagnosis", "GET"),
    }
    admin_registry = build_tool_registry(app, current_user=admin)
    reader_registry = build_tool_registry(app, current_user=reader)

    assert {
        name: (definition.route_path, definition.method)
        for name, definition in admin_registry.items()
        if definition.system_management
    } == expected
    assert not (set(expected) & set(reader_registry))
    assert not {
        "delete_storage_cluster",
        "create_aggregate",
        "delete_aggregate",
        "create_volume",
        "update_volume",
        "delete_volume",
            "create_qtree",
            "update_qtree",
        "delete_qtree",
        "delete_group_tag",
        "create_user",
        "delete_user",
        "delete_ai_model",
        "update_storage_config",
        "delete_storage_backup_record",
        "list_ai_audits",
        "get_ai_audit",
        "get_ai_audit_conversation",
    } & set(admin_registry)
    assert not any(
        definition.system_management and (definition.route_path, definition.method) in {
            ("/users/login", "POST"),
            ("/users/logout", "POST"),
            ("/users/current/profile", "GET"),
            ("/users/sync-ldap", "POST"),
            ("/storage-clusters/{storage_cluster_id}/analytics/export", "GET"),
            ("/admin/ai-models/{model_id}/test", "POST"),
            ("/admin/ai-audits", "GET"),
            ("/admin/ai-audits/conversations/{conversation_id}", "GET"),
            ("/admin/ai-audits/{audit_id}", "GET"),
            ("/storage-back-up-records/{storage_back_up_record_id}/rollback", "POST"),
        }
        for definition in admin_registry.values()
    )


def test_quota_adjustment_tools_require_admin_at_registration_and_execution(monkeypatch):
    app = FastAPI()
    app.include_router(group.router)
    app.include_router(storage_usage.router)
    calls = []

    app.dependency_overrides[require_super_admin] = lambda: None
    app.dependency_overrides[get_db] = lambda: object()
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: admin
    monkeypatch.setattr(
        quotaService,
        "adjust_group_quota",
        lambda _db, group_id, request, current_user=None, audit_context=None: calls.append(("group", group_id, request)) or {
            "id": group_id,
            "resource_type": "group",
            "storage_type": "netapp",
            "hard_limit": request.hard_limit_gib,
        },
    )
    monkeypatch.setattr(
        quotaService,
        "adjust_storage_usage_quota",
        lambda _db, storage_usage_id, request, current_user=None, audit_context=None: calls.append(("storage_usage", storage_usage_id, request)) or {
            "id": storage_usage_id,
            "resource_type": "storage_usage",
            "storage_type": "netapp",
            "hard_limit": request.hard_limit_gib,
        },
    )
    original_get = base_config.get

    def configured_get(key, default=None):
        return ["ai-admin"] if key == "super_admin_usernames" else original_get(key, default)

    monkeypatch.setattr(base_config, "get", configured_get)
    admin = User(id=102, username="ai-admin", rd_username="ai-admin", email="admin@example.com")
    reader = User(id=101, username="reader", rd_username="reader", email="reader@example.com")
    admin_registry = build_tool_registry(app, current_user=admin)

    assert {"adjust_group_quota", "adjust_storage_usage_quota"} <= set(admin_registry)
    assert not {"adjust_group_quota", "adjust_storage_usage_quota"} & set(
        build_tool_registry(app, current_user=reader)
    )
    assert execute_tool(
        app=app,
        registry=admin_registry,
        tool_name="adjust_group_quota",
        arguments={"group_id": 7, "body": {"hard_limit": 2, "unit": "TiB"}},
        current_user=reader,
    ) == {"ok": False, "error": "系统管理工具仅限超级管理员"}
    assert calls == []

    group_result = execute_tool(
        app=app,
        registry=admin_registry,
        tool_name="adjust_group_quota",
        arguments={"group_id": 7, "body": {"hard_limit": 2, "unit": "TiB"}},
        current_user=admin,
    )
    usage_result = execute_tool(
        app=app,
        registry=admin_registry,
        tool_name="adjust_storage_usage_quota",
        arguments={"storage_usage_id": 9, "body": {"hard_limit": 120, "unit": "GiB"}},
        current_user=admin,
    )

    assert group_result["ok"] is True
    assert {
        key: group_result["data"][key]
        for key in ("id", "resource_type", "storage_type", "hard_limit")
    } == {
        "id": 7,
        "resource_type": "group",
        "storage_type": "netapp",
        "hard_limit": 2048,
    }
    assert usage_result["ok"] is True
    assert {
        key: usage_result["data"][key]
        for key in ("id", "resource_type", "storage_type", "hard_limit")
    } == {
        "id": 9,
        "resource_type": "storage_usage",
        "storage_type": "netapp",
        "hard_limit": 120,
    }
    assert [(kind, identifier, request.hard_limit_gib) for kind, identifier, request in calls] == [
        ("group", 7, 2048),
        ("storage_usage", 9, 120),
    ]
    assert execute_tool(
        app=app,
        registry=admin_registry,
        tool_name="adjust_group_quota",
        arguments={"group_id": 7, "body": {"hard_limit": 120, "unit": "GiB", "unexpected": True}},
        current_user=admin,
    )["error"] == "工具参数无效"


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
    assert client.post(
        "/storage-pulse/api/admin/ai-models/discover",
        json={"provider": "openai", "base_url": "https://ai.example.com/v1", "api_key": "secret-key-1234"},
    ).status_code == 403


def test_blank_model_identifier_uses_the_first_discovered_provider_model(db_session, monkeypatch):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    _seed_user(db_session)
    requested_models = []

    def discovered_models(config):
        requested_models.append(config)
        return ["gpt-5.6-sol", "gpt-5.6-mini"]

    monkeypatch.setattr(ai_config_service, "list_provider_models", discovered_models, raising=False)
    payload = AIModelCreate(
        name="自动发现模型",
        provider="openai",
        base_url="https://ai.example.com/v1",
        api_key="secret-key-1234",
        model="",
        enabled=True,
    )

    created = ai_config_service.create_model(db_session, payload, actor_id=1)

    assert created["model"] == "gpt-5.6-sol"
    assert len(requested_models) == 1
    assert requested_models[0].model == ""
    assert decrypt_secret(requested_models[0].api_key_encrypted) == "secret-key-1234"


def test_manual_model_identifier_skips_discovery_and_blank_updates_discover_again(
    db_session,
    monkeypatch,
):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    _seed_user(db_session)
    calls = []

    def discovered_models(config):
        calls.append(config.model)
        return ["gpt-5.6-sol"]

    monkeypatch.setattr(ai_config_service, "list_provider_models", discovered_models)
    manual = ai_config_service.create_model(
        db_session,
        AIModelCreate(name="手工模型", model="manual-model"),
        actor_id=1,
    )

    updated = ai_config_service.update_model(
        db_session,
        manual["id"],
        AIModelPatch(model=""),
        actor_id=1,
    )

    assert manual["model"] == "manual-model"
    assert updated["model"] == "gpt-5.6-sol"
    assert calls == [""]


def test_super_admin_can_discover_a_sanitized_provider_model_catalog(
    api_client_factory,
    db_session,
    monkeypatch,
):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    admin = _seed_user(db_session, rd_username="alice")
    captured = []

    def discovered_models(config):
        captured.append(config)
        return ["gpt-5.6-sol", "gpt-5.6-mini"]

    monkeypatch.setattr(ai_config_service, "list_provider_models", discovered_models, raising=False)
    client = api_client_factory([ai_admin.router], headers={"Authorization": f"Bearer {issue_token(admin.id)}"})

    response = client.post(
        "/storage-pulse/api/admin/ai-models/discover",
        json={
            "provider": "openai",
            "base_url": "https://ai.example.com/v1",
            "api_key": "secret-key-1234",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "models": ["gpt-5.6-sol", "gpt-5.6-mini"],
        "default_model": "gpt-5.6-sol",
    }
    assert len(captured) == 1
    assert decrypt_secret(captured[0].api_key_encrypted) == "secret-key-1234"
    assert "secret-key-1234" not in response.text


@pytest.mark.parametrize(
    ("provider", "base_url", "response_payload", "expected_url", "expected_models"),
    [
        (
            "openai",
            "https://ai.example.com/v1",
            {"data": [{"id": "gpt-5.6-sol"}, {"id": "gpt-5.6-sol"}, {"id": "gpt-5.6-mini"}]},
            "https://ai.example.com/v1/models",
            ["gpt-5.6-sol", "gpt-5.6-mini"],
        ),
        (
            "ollama",
            "http://localhost:11434/v1",
            {"models": [{"name": "llama3.3"}, {"name": "qwen3"}]},
            "http://localhost:11434/api/tags",
            ["llama3.3", "qwen3"],
        ),
    ],
)
def test_provider_model_listing_normalizes_supported_catalog_envelopes(
    db_session,
    monkeypatch,
    provider,
    base_url,
    response_payload,
    expected_url,
    expected_models,
):
    from services import ai_client

    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    model = _seed_model(db_session)
    model.provider = provider
    model.base_url = base_url
    captured = {}

    class Response:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return response_payload

    def request_catalog(url, *, headers, timeout):
        captured.update(url=url, headers=headers, timeout=timeout)
        return Response()

    monkeypatch.setattr(ai_client.httpx, "get", request_catalog)

    assert ai_client.list_provider_models(model) == expected_models
    assert captured["url"] == expected_url
    assert captured["timeout"] <= 10
    assert captured["headers"].get("Authorization") == "Bearer secret-key-1234"


def test_provider_model_listing_keeps_upstream_errors_sanitized(db_session, monkeypatch):
    from services import ai_client

    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    model = _seed_model(db_session)

    def failed_request(*_args, **_kwargs):
        raise ai_client.httpx.ReadTimeout("secret-key-1234 at internal.example")

    monkeypatch.setattr(ai_client.httpx, "get", failed_request)

    with pytest.raises(AIClientError, match="AI 服务请求超时") as error:
        ai_client.list_provider_models(model)

    assert "secret-key-1234" not in str(error.value)
    assert "internal.example" not in str(error.value)


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


def test_stream_setup_failure_logs_traceable_server_error(db_session, monkeypatch, caplog):
    base_config.set("ai.config_secret_key", "test-ai-config-secret-key")
    _seed_user(db_session)
    model = _seed_model(db_session)
    conversation = AIConversation(user_id=1, model_id=model.id, title="日志失败")
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    def broken_registry(*_args, **_kwargs):
        raise RuntimeError("synthetic setup failure")

    monkeypatch.setattr(ai_chat_service, "build_tool_registry", broken_registry)
    with caplog.at_level(logging.ERROR, logger=ai_chat_service.__name__):
        events = list(
            ai_chat_service.stream_message(
                app=FastAPI(),
                db=db_session,
                conversation_id=conversation.id,
                user_id=1,
                content="记录后端失败日志",
            )
        )

    accepted = next(data for event, data in events if event == "accepted")
    error = events[-1][1]
    assert error["error"] == "AI 服务暂不可用"
    record = next(record for record in caplog.records if record.name == ai_chat_service.__name__)
    assert record.levelno == logging.ERROR
    assert accepted["trace_id"] in record.getMessage()
    assert "RuntimeError" in record.getMessage()
    assert record.exc_info is not None


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


def _name_obfuscation_migration():
    path = Path(__file__).resolve().parents[1] / "migrate" / "versions" / "000000000024_ai_name_obfuscation.py"
    spec = importlib.util.spec_from_file_location("ai_name_obfuscation_migration", path)
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


@pytest.mark.parametrize("dialect_name", ("sqlite", "postgresql", "mysql"))
def test_name_obfuscation_migration_compiles_for_supported_dialects(dialect_name):
    migration = _name_obfuscation_migration()
    output = io.StringIO()
    migration.op = Operations(
        MigrationContext.configure(
            dialect_name=dialect_name,
            opts={"as_sql": True, "output_buffer": output},
        )
    )

    migration.upgrade()

    sql = output.getvalue().lower()
    assert migration.revision == "000000000024"
    assert migration.down_revision == "000000000023"
    assert "ai_conversation_name_aliases" in sql
    assert "name_obfuscation_enabled" in sql


def test_name_obfuscation_migration_upgrades_and_downgrades_sqlite():
    migration = _name_obfuscation_migration()
    metadata = sa.MetaData()
    sa.Table("ai_platform_settings", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("ai_conversations", metadata, sa.Column("id", sa.Integer(), primary_key=True))

    with sa.create_engine("sqlite://").begin() as connection:
        metadata.create_all(connection)
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = sa.inspect(connection)

        assert {
            "name_obfuscation_enabled",
            "name_obfuscation_epoch",
        } <= {column["name"] for column in inspector.get_columns("ai_platform_settings")}
        assert {
            "name_obfuscation_epoch",
            "name_obfuscation_from_message_id",
        } <= {column["name"] for column in inspector.get_columns("ai_conversations")}
        assert "ai_conversation_name_aliases" in inspector.get_table_names()

        migration.downgrade()
        inspector.clear_cache()
        assert "ai_conversation_name_aliases" not in inspector.get_table_names()
        assert "name_obfuscation_enabled" not in {
            column["name"] for column in inspector.get_columns("ai_platform_settings")
        }


def test_ai_migration_adopts_complete_create_all_schema():
    migration = _ai_migration()
    tables = (AIConfig.__table__, AIConversation.__table__, AIMessage.__table__, AIAuditLog.__table__)

    with sa.create_engine("sqlite://").begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))

        migration.upgrade()
        migration.upgrade()

        assert {table.name for table in tables} <= set(sa.inspect(connection).get_table_names())


def test_ai_migration_rejects_partial_create_all_schema():
    migration = _ai_migration()

    with sa.create_engine("sqlite://").begin() as connection:
        AIConfig.__table__.create(connection)
        migration.op = Operations(MigrationContext.configure(connection))

        with pytest.raises(RuntimeError, match="partial AI schema"):
            migration.upgrade()
