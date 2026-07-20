# -*- coding: utf-8 -*-
"""RED contract for request correlation and append-only unified audit events."""

import importlib
import importlib.util
import io
import json
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from alembic.migration import MigrationContext
from alembic.operations import Operations

from appConfig import base_config
from models import AIConfig, AIConversation, AuditEvent, Group, GroupTag, Project, StorageCluster, User
from services import ai_chat_service, audit_service, project_membership_service
from services.ai_client import AICompletionStreamEvent


def _uuid(value: str) -> str:
    return str(UUID(value))


def _correlation_client() -> TestClient:
    correlation = importlib.import_module("middleware.correlation")
    app = FastAPI()
    app.add_middleware(correlation.CorrelationIdMiddleware)

    @app.get("/correlation")
    def correlation_view(request: Request):
        context = request.state.audit_context
        return {
            "request_id": str(context.request_id),
            "trace_id": str(context.trace_id),
            "operation_id": str(context.operation_id),
        }

    return TestClient(app)


def test_correlation_middleware_preserves_valid_request_and_trace_ids():
    client = _correlation_client()
    request_id = "2a48f1f1-78ea-49c1-b3bc-2712720e4c86"
    trace_id = "1e8de2cf-9bdf-4242-a40c-794ce52694ec"

    response = client.get(
        "/correlation",
        headers={"X-Request-ID": request_id, "X-Trace-ID": trace_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
    assert response.headers["X-Trace-ID"] == trace_id
    assert response.json()["request_id"] == request_id
    assert response.json()["trace_id"] == trace_id
    assert _uuid(response.json()["operation_id"])


def test_correlation_middleware_replaces_invalid_ids_with_safe_uuids():
    client = _correlation_client()

    response = client.get(
        "/correlation",
        headers={"X-Request-ID": "not-a-uuid", "X-Trace-ID": "../../secret"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "not-a-uuid"
    assert response.headers["X-Trace-ID"] != "../../secret"
    assert _uuid(response.headers["X-Request-ID"])
    assert _uuid(response.headers["X-Trace-ID"])
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert response.json()["trace_id"] == response.headers["X-Trace-ID"]


def test_audit_redaction_removes_secrets_paths_and_raw_prompt_content():
    audit_service = importlib.import_module("services.audit_service")
    payload = {
        "Authorization": "Bearer private-token",
        "nested": {"apiKey": "provider-secret"},
        "linux_path": "/mnt/diskpulse/private/alice",
        "prompt": "请总结 alice 的私有目录配额",
        "response_payload": {"content": "模型原始回复"},
        "response": "设备原始响应",
        "raw_response": "设备原始 raw 响应",
        "device_response": "设备原始 device 响应",
        "body": "设备原始响应体",
        "hard_limit": 1024,
    }

    redacted = audit_service.redact_audit_payload(payload)
    serialized = json.dumps(redacted, ensure_ascii=False)

    for forbidden in (
        "private-token",
        "provider-secret",
        "/mnt/diskpulse/private/alice",
        "请总结 alice 的私有目录配额",
        "模型原始回复",
        "设备原始响应",
        "设备原始 raw 响应",
        "设备原始 device 响应",
        "设备原始响应体",
    ):
        assert forbidden not in serialized
    assert redacted["hard_limit"] == 1024
    assert payload["Authorization"] == "Bearer private-token"


def test_append_audit_event_creates_a_new_redacted_event_without_committing():
    audit_service = importlib.import_module("services.audit_service")

    class RecordingSession:
        def __init__(self):
            self.added = []
            self.flushed = False

        def add(self, event):
            self.added.append(event)

        def flush(self):
            self.flushed = True

        def commit(self):  # pragma: no cover - assertion guard for transaction ownership
            raise AssertionError("append_audit_event must not commit the caller transaction")

    context = audit_service.AuditContext(
        request_id="0a79076d-4bc8-4d20-b78c-60e214617515",
        trace_id="ca277c09-4d55-4328-859c-975b8bdac736",
        operation_id="6b16544a-75a5-42df-9728-0c2e214f3097",
        actor_user_id=7,
    )
    db = RecordingSession()

    event = audit_service.append_audit_event(
        db,
        context=context,
        phase="result",
        action="quota.adjust",
        resource_type="storage_usage",
        resource_id=42,
        project_id=9,
        outcome="success",
        before_summary={"linux_path": "/mnt/diskpulse/private/alice", "hard_limit": 100},
        after_summary={"linux_path": "/mnt/diskpulse/private/alice", "hard_limit": 120},
        metadata={"token": "do-not-store"},
    )

    assert db.added == [event]
    assert db.flushed is True
    assert str(event.request_id) == str(context.request_id)
    assert str(event.trace_id) == str(context.trace_id)
    assert str(event.operation_id) == str(context.operation_id)
    assert event.actor_user_id == 7
    assert event.action == "quota.adjust"
    assert event.resource_type == "storage_usage"
    assert event.resource_id == 42
    assert event.project_id == 9
    assert event.phase == "result"
    assert event.outcome == "success"
    persisted = json.dumps(
        {"before": event.before_summary, "after": event.after_summary, "metadata": event.event_metadata},
        ensure_ascii=False,
    )
    assert "/mnt/diskpulse/private/alice" not in persisted
    assert "do-not-store" not in persisted


def test_project_member_creation_appends_correlated_audit_event(db_session):
    """A project-admin write records the actor and request correlation values."""
    base_config.set("super_admin_usernames", ["admin"])
    actor = User(id=1, username="Admin User", rd_username="admin")
    member = User(id=2, username="Reader User", rd_username="reader")
    project = Project(id=3, name="project-3")
    db_session.add_all([actor, member, project])
    db_session.commit()

    context = audit_service.AuditContext(
        request_id="9cbaece5-30c2-4b6c-94b0-55c9f5df2d15",
        trace_id="143b7cc2-f3c5-4e48-818b-33d4697fc801",
        operation_id="1adcb3a0-34d0-4172-aa3f-1d5cc2d2b582",
        actor_user_id=actor.id,
    )

    project_membership_service.create_membership(
        db_session,
        project_id=project.id,
        user_id=member.id,
        role="reader",
        current_user=actor,
        audit_context=context,
    )
    events = db_session.query(AuditEvent).order_by(AuditEvent.occurred_at, AuditEvent.id).all()
    assert [(event.action, event.resource_type, event.resource_id) for event in events] == [
        ("project.membership.create", "project_membership", member.id),
    ]
    assert all(event.phase == "result" and event.outcome == "success" for event in events)
    assert all(event.actor_user_id == actor.id for event in events)
    assert events[0].project_id == project.id
    assert all(event.request_id == context.request_id and event.trace_id == context.trace_id for event in events)


def test_ai_conversation_creation_appends_correlated_unscoped_audit_event(db_session):
    """AI lifecycle records stay user/conversation/model scoped and do not bind a project."""
    actor = User(id=1, username="Admin User", rd_username="admin")
    model = AIConfig(
        id=4,
        name="audit-model",
        provider="openai",
        model="test-model",
        enabled=True,
        enable_chat=True,
    )
    db_session.add_all([actor, model])
    db_session.commit()
    context = audit_service.AuditContext(
        request_id="9cbaece5-30c2-4b6c-94b0-55c9f5df2d15",
        trace_id="143b7cc2-f3c5-4e48-818b-33d4697fc801",
        operation_id="1adcb3a0-34d0-4172-aa3f-1d5cc2d2b582",
        actor_user_id=actor.id,
    )

    conversation = ai_chat_service.create_conversation(
        db_session,
        actor.id,
        "audit lifecycle title",
        model.id,
        audit_context=context,
    )

    event = db_session.query(AuditEvent).one()
    assert (event.action, event.resource_type, event.resource_id) == (
        "ai.conversation.create",
        "ai_conversation",
        conversation["id"],
    )
    assert (event.phase, event.outcome, event.actor_user_id, event.project_id) == ("result", "success", actor.id, None)
    assert (event.request_id, event.trace_id) == (context.request_id, context.trace_id)
    assert "audit lifecycle title" not in json.dumps(event.after_summary, ensure_ascii=False)


def test_ai_conversation_delete_appends_correlated_unscoped_audit_event(db_session):
    actor = User(id=1, username="Admin User", rd_username="admin")
    model = AIConfig(
        id=4,
        name="audit-model",
        provider="openai",
        model="test-model",
        enabled=True,
        enable_chat=True,
    )
    conversation = AIConversation(id=5, user_id=actor.id, model_id=model.id, title="private title")
    db_session.add_all([actor, model, conversation])
    db_session.commit()
    context = audit_service.AuditContext(
        request_id="9cbaece5-30c2-4b6c-94b0-55c9f5df2d15",
        trace_id="143b7cc2-f3c5-4e48-818b-33d4697fc801",
        operation_id="1adcb3a0-34d0-4172-aa3f-1d5cc2d2b582",
        actor_user_id=actor.id,
    )

    ai_chat_service.delete_conversation(
        db_session,
        conversation.id,
        actor.id,
        audit_context=context,
    )

    event = db_session.query(AuditEvent).one()
    assert (event.action, event.resource_type, event.resource_id) == (
        "ai.conversation.delete",
        "ai_conversation",
        conversation.id,
    )
    assert (event.phase, event.outcome, event.actor_user_id, event.project_id) == ("result", "success", actor.id, None)
    assert "private title" not in json.dumps(event.before_summary, ensure_ascii=False)


def test_ai_message_lifecycle_appends_unscoped_redacted_audit_event(db_session, monkeypatch):
    actor = User(id=1, username="Admin User", rd_username="admin")
    model = AIConfig(
        id=4,
        name="audit-model",
        provider="openai",
        model="test-model",
        enabled=True,
        enable_chat=True,
    )
    conversation = AIConversation(id=5, user_id=actor.id, model_id=model.id, title="message audit")
    db_session.add_all([actor, model, conversation])
    db_session.commit()
    context = audit_service.AuditContext(
        request_id="9cbaece5-30c2-4b6c-94b0-55c9f5df2d15",
        trace_id="143b7cc2-f3c5-4e48-818b-33d4697fc801",
        operation_id="1adcb3a0-34d0-4172-aa3f-1d5cc2d2b582",
        actor_user_id=actor.id,
    )

    def provider_stream(*_args, **_kwargs):
        yield AICompletionStreamEvent(kind="delta", text="已处理")
        yield AICompletionStreamEvent(kind="completed", text="已处理", tool_calls=[], stop_reason="final")

    monkeypatch.setattr(ai_chat_service, "chat_completion_stream", provider_stream)
    list(
        ai_chat_service.stream_message(
            app=FastAPI(),
            db=db_session,
            conversation_id=conversation.id,
            user_id=actor.id,
            content="do not store this private prompt",
            current_user=actor,
            audit_context=context,
        )
    )

    events = db_session.query(AuditEvent).order_by(AuditEvent.occurred_at, AuditEvent.id).all()
    assert [(event.phase, event.outcome) for event in events] == [("attempt", "success"), ("result", "success")]
    assert all(event.action == "ai.message.send" and event.project_id is None for event in events)
    assert all(event.resource_id == conversation.id and event.actor_user_id == actor.id for event in events)
    assert "do not store this private prompt" not in json.dumps(
        [event.before_summary for event in events] + [event.after_summary for event in events], ensure_ascii=False
    )


def test_audit_event_list_serializes_numeric_resource_ids_as_strings(
    api_client_factory,
    session_factory,
):
    from routers import audit_events
    from utils.security import issue_token

    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["audit-admin"])
    session = session_factory()
    try:
        session.add_all(
            [
                User(id=1, rd_username="audit-admin", username="Audit Admin"),
                AuditEvent(
                    id="32d85a48-2667-4ee7-b369-5c4d670eb610",
                    operation_id="54248ded-a2cb-45b5-b464-b5c12a2dc90d",
                    phase="result",
                    actor_type="user",
                    actor_user_id=1,
                    action="quota.adjust",
                    resource_type="storage_usage",
                    resource_id=296,
                    outcome="success",
                    request_id="c57c77c9-46ed-4c3f-92fc-bfd6d9e7eae6",
                    trace_id="ee874b8d-e657-45eb-b6f2-c0a7c4cefb39",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    client = api_client_factory(
        [audit_events.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    response = client.get("/storage-pulse/api/v1/audit-events")

    assert response.status_code == 200
    assert response.json()["content"][0]["resource_id"] == "296"


def test_audit_event_list_resolves_actor_resource_and_indirect_project_associations(
    api_client_factory,
    session_factory,
):
    """Storage-cluster events explain their current resource-to-project path."""
    from routers import audit_events
    from utils.security import issue_token

    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["audit-admin"])
    session = session_factory()
    try:
        session.add_all(
            [
                User(id=1, rd_username="audit-admin", username="Audit Admin"),
                User(id=9, rd_username="collector", username="Storage Collector"),
                Project(id=10, name="芯片设计平台"),
                Project(id=11, name="仿真平台"),
                GroupTag(id=1, name="生产"),
                StorageCluster(id=2, name="华东存储集群", storage_type="netapp"),
                Group(id=20, name="芯片设计组", project_id=10, storage_cluster_id=2, group_tag_id=1, enable_monitoring=False),
                Group(id=21, name="仿真组", project_id=11, storage_cluster_id=2, group_tag_id=1, enable_monitoring=False),
                AuditEvent(
                    id="7af3cbd9-2be4-41f7-8af9-9892f5071c2b",
                    operation_id="9b017ba9-5f17-4bc2-9cd9-411d2fb3b2e6",
                    phase="result",
                    actor_type="system",
                    actor_user_id=9,
                    action="storage.collection.run",
                    resource_type="storage_cluster",
                    resource_id=2,
                    outcome="success",
                    request_id="4fc57bc6-59c5-4f69-8318-33aafd1ec6fd",
                    trace_id="ec6ae0f4-c3a4-4e31-8a1b-b7ab88eb5f07",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    client = api_client_factory(
        [audit_events.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    response = client.get("/storage-pulse/api/v1/audit-events")

    assert response.status_code == 200
    event = response.json()["content"][0]
    assert event["actor"] == {"id": 9, "display_name": "collector"}
    assert event["resource"] == {
        "type": "storage_cluster",
        "id": "2",
        "name": "华东存储集群",
    }
    assert event["related_projects"] == [
        {"id": 10, "name": "芯片设计平台"},
        {"id": 11, "name": "仿真平台"},
    ]
    assert event["relation_path"] == "存储集群 → 项目组 → 项目"


def test_audit_event_detail_is_available_only_within_the_authorized_project_scope(
    api_client_factory,
    session_factory,
):
    from routers import audit_events
    from models import ProjectMembership
    from utils.security import issue_token

    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", [])
    session = session_factory()
    try:
        session.add_all(
            [
                User(id=1, rd_username="project-admin", username="Project Admin"),
                Project(id=1, name="project-a"),
                ProjectMembership(project_id=1, user_id=1, role="project_admin"),
                AuditEvent(
                    id="32d85a48-2667-4ee7-b369-5c4d670eb610",
                    operation_id="54248ded-a2cb-45b5-b464-b5c12a2dc90d",
                    phase="result",
                    actor_type="user",
                    action="project.membership.create",
                    resource_type="project_membership",
                    project_id=1,
                    outcome="success",
                    request_id="c57c77c9-46ed-4c3f-92fc-bfd6d9e7eae6",
                    trace_id="ee874b8d-e657-45eb-b6f2-c0a7c4cefb39",
                ),
                AuditEvent(
                    id="4e09b244-3c38-4633-a45b-eed7ed8b0b64",
                    operation_id="d4c91d72-21a4-4f58-9536-617633fad767",
                    phase="result",
                    actor_type="user",
                    action="ai.conversation.create",
                    resource_type="ai_conversation",
                    outcome="success",
                    request_id="f685e514-cde5-420d-8c22-04af0ee97fa1",
                    trace_id="a6dd42d9-ecd9-4740-8ec8-bd84e5a77767",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    client = api_client_factory(
        [audit_events.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )
    scoped = client.get(f"/storage-pulse/api/v1/audit-events/32d85a48-2667-4ee7-b369-5c4d670eb610")
    unscoped = client.get(f"/storage-pulse/api/v1/audit-events/4e09b244-3c38-4633-a45b-eed7ed8b0b64")

    assert scoped.status_code == 200
    assert scoped.json()["id"] == "32d85a48-2667-4ee7-b369-5c4d670eb610"
    assert unscoped.status_code == 403


def _audit_migration_module():
    migration_path = Path(__file__).resolve().parents[1] / "migrate" / "versions" / "000000000009_project_rbac_unified_audit.py"
    spec = importlib.util.spec_from_file_location("unified_audit_migration", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_migration(migration, context, method_name):
    with Operations.context(context):
        getattr(migration, method_name)()


def test_unified_audit_migration_prevents_sqlite_updates_and_deletes():
    migration = _audit_migration_module()
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as connection:
        metadata = sa.MetaData()
        sa.Table("users", metadata, sa.Column("id", sa.Integer(), primary_key=True))
        sa.Table(
            "projects",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("in_charge_user_id", sa.Integer()),
            sa.Column("pt_user_id", sa.Integer()),
        )
        metadata.create_all(connection)
        connection.commit()
        _run_migration(migration, MigrationContext.configure(connection), "upgrade")
        connection.execute(
            text(
                """
                INSERT INTO audit_events (
                    id, operation_id, phase, occurred_at, actor_type, action,
                    resource_type, outcome, request_id, trace_id
                ) VALUES (
                    '32d85a48-2667-4ee7-b369-5c4d670eb610',
                    '54248ded-a2cb-45b5-b464-b5c12a2dc90d',
                    'result', CURRENT_TIMESTAMP, 'user', 'quota.adjust',
                    'storage_usage', 'success',
                    'c57c77c9-46ed-4c3f-92fc-bfd6d9e7eae6',
                    'ee874b8d-e657-45eb-b6f2-c0a7c4cefb39'
                )
                """
            )
        )
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(text("UPDATE audit_events SET action = 'changed'"))
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(text("DELETE FROM audit_events"))


@pytest.mark.parametrize("dialect_name", ["sqlite", "postgresql", "mysql"])
def test_unified_audit_migration_compiles_without_online_database_access(dialect_name):
    migration = _audit_migration_module()
    output = io.StringIO()
    context = MigrationContext.configure(
        dialect_name=dialect_name,
        opts={"as_sql": True, "output_buffer": output},
    )

    _run_migration(migration, context, "upgrade")

    sql = output.getvalue()
    assert "CREATE TABLE audit_events" in sql
    source = Path(migration.__file__).read_text(encoding="utf-8")
    assert "if context.as_sql" in source
    if dialect_name == "sqlite":
        assert "CREATE TRIGGER trg_audit_events_no_update" in sql
