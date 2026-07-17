# -*- coding: utf-8 -*-
from datetime import datetime
import importlib.util
import io
from pathlib import Path

import models
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI

from appConfig import base_config
from utils.security import issue_token


API_PREFIX = "/storage-pulse/api"


def _conversation_scope_migration():
    path = Path(__file__).resolve().parents[1] / "migrate" / "versions" / "000000000010_ai_conversation_project_scope.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _auth_client(api_client_factory, router, user_id: int):
    return api_client_factory(
        [router],
        headers={"Authorization": f"Bearer {issue_token(user_id)}"},
    )


def test_ai_conversation_optionally_binds_an_authorized_project_and_keeps_null_scope(
    api_client_factory,
    session_factory,
):
    from routers import ai

    base_config.set("jwt.secret_key", "test-secret")
    session = session_factory()
    try:
        session.add_all(
            [
                models.User(id=1, rd_username="reader", username="Reader"),
                models.Project(id=1, name="allowed"),
                models.Project(id=2, name="forbidden"),
                models.ProjectMembership(project_id=1, user_id=1, role="reader"),
                models.AIConfig(
                    id=1,
                    name="chat-model",
                    provider="openai",
                    model="example",
                    enabled=True,
                    enable_chat=True,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()
    client = _auth_client(api_client_factory, ai.router, user_id=1)

    allowed = client.post(
        f"{API_PREFIX}/ai/conversations",
        json={"title": "project conversation", "model_id": 1, "project_id": 1},
    )
    unscoped = client.post(
        f"{API_PREFIX}/ai/conversations",
        json={"title": "personal conversation", "model_id": 1},
    )
    forbidden = client.post(
        f"{API_PREFIX}/ai/conversations",
        json={"title": "cross project", "model_id": 1, "project_id": 2},
    )

    assert allowed.status_code == 201
    assert allowed.json()["project_id"] == 1
    assert unscoped.status_code == 201
    assert unscoped.json()["project_id"] is None
    assert forbidden.status_code == 403


def test_null_project_conversation_has_no_project_tool_context(db_session):
    from services import ai_chat_service

    db_session.add_all(
        [
            models.User(id=1, rd_username="reader", username="Reader"),
            models.AIConfig(
                id=1,
                name="chat-model",
                provider="openai",
                model="example",
                enabled=True,
                enable_chat=True,
            ),
        ]
    )
    db_session.commit()
    conversation = ai_chat_service.create_conversation(db_session, 1, "personal", 1)

    assert conversation["project_id"] is None
    assert ai_chat_service._tool_registry_for_conversation(FastAPI(), None, None) == {}


def test_ai_conversation_project_scope_migration_handles_sqlite_and_supported_dialects():
    for dialect_name in ("sqlite", "postgresql", "mysql"):
        migration = _conversation_scope_migration()
        output = io.StringIO()
        migration.op = Operations(
            MigrationContext.configure(
                dialect_name=dialect_name,
                opts={"as_sql": True, "output_buffer": output},
            )
        )
        migration.upgrade()
        migration.downgrade()
        assert "project_id" in output.getvalue().lower()

    migration = _conversation_scope_migration()
    metadata = sa.MetaData()
    sa.Table("projects", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table(
        "ai_conversations",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    with sa.create_engine("sqlite://").begin() as connection:
        metadata.create_all(connection)
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assert "project_id" in {
            column["name"] for column in sa.inspect(connection).get_columns("ai_conversations")
        }
        migration.downgrade()
        assert "project_id" not in {
            column["name"] for column in sa.inspect(connection).get_columns("ai_conversations")
        }


def test_project_reader_lists_only_its_project_storage_usages_before_pagination(
    api_client_factory,
    session_factory,
):
    from routers import storage_usage

    base_config.set("jwt.secret_key", "test-secret")
    session = session_factory()
    try:
        session.add_all(
            [
                models.User(id=1, rd_username="reader", username="Reader"),
                models.User(id=2, rd_username="other", username="Other"),
                models.Project(id=1, name="allowed"),
                models.Project(id=2, name="forbidden"),
                models.ProjectMembership(project_id=1, user_id=1, role="reader"),
                models.StorageCluster(id=1, name="cluster-a", storage_type="netapp", is_active=True),
                models.GroupTag(id=1, name="production"),
                models.Group(
                    id=1,
                    project_id=1,
                    storage_cluster_id=1,
                    group_tag_id=1,
                    name="allowed-group",
                    enable_monitoring=False,
                ),
                models.Group(
                    id=2,
                    project_id=2,
                    storage_cluster_id=1,
                    group_tag_id=1,
                    name="forbidden-group",
                    enable_monitoring=False,
                ),
                models.StorageUsage(
                    id=1,
                    storage_cluster_id=1,
                    user_id=1,
                    group_id=1,
                    linux_path="/data/allowed/reader",
                    updated_at=datetime.now(),
                ),
                models.StorageUsage(
                    id=2,
                    storage_cluster_id=1,
                    user_id=2,
                    group_id=2,
                    linux_path="/data/forbidden/other",
                    updated_at=datetime.now(),
                ),
            ]
        )
        session.commit()
    finally:
        session.close()
    client = _auth_client(api_client_factory, storage_usage.router, user_id=1)

    response = client.get(f"{API_PREFIX}/storage-usages/?page=1&size=1")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [row["id"] for row in response.json()["content"]] == [1]


def test_group_owner_can_adjust_only_its_group_and_its_user_directories(
    api_client_factory,
    monkeypatch,
    session_factory,
):
    from routers import group, storage_usage
    from services import quotaService

    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", [])
    session = session_factory()
    try:
        session.add_all(
            [
                models.User(id=1, rd_username="owner", username="Owner"),
                models.User(id=2, rd_username="other-owner", username="Other Owner"),
                models.Project(id=1, name="project-a"),
                models.StorageCluster(id=1, name="cluster-a", storage_type="netapp", is_active=True),
                models.GroupTag(id=1, name="production"),
                models.Group(
                    id=1,
                    project_id=1,
                    storage_cluster_id=1,
                    group_tag_id=1,
                    in_charge_user_id=1,
                    name="owned-group",
                    enable_monitoring=False,
                ),
                models.Group(
                    id=2,
                    project_id=1,
                    storage_cluster_id=1,
                    group_tag_id=1,
                    in_charge_user_id=2,
                    name="other-group",
                    enable_monitoring=False,
                ),
                models.StorageUsage(
                    id=1,
                    storage_cluster_id=1,
                    user_id=1,
                    group_id=1,
                    linux_path="/data/owned/owner",
                    updated_at=datetime.now(),
                ),
            ]
        )
        session.commit()
    finally:
        session.close()
    monkeypatch.setattr(
        quotaService,
        "adjust_group_quota",
        lambda _db, group_id, request, current_user=None: {
            "id": group_id,
            "resource_type": "group",
            "storage_type": "netapp",
            "hard_limit": request.hard_limit_gib,
            "soft_limit": request.soft_limit_gib,
            "unit": "GiB",
            "soft_grace_seconds": None,
        },
    )
    monkeypatch.setattr(
        quotaService,
        "adjust_storage_usage_quota",
        lambda _db, storage_usage_id, request, current_user=None: {
            "id": storage_usage_id,
            "resource_type": "storage_usage",
            "storage_type": "netapp",
            "hard_limit": request.hard_limit_gib,
            "soft_limit": request.soft_limit_gib,
            "unit": "GiB",
            "soft_grace_seconds": None,
        },
    )
    client = api_client_factory(
        [group.router, storage_usage.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )
    payload = {"hard_limit": 120, "unit": "GiB"}

    own_group = client.patch(f"{API_PREFIX}/groups/1/quota", json=payload)
    own_directory = client.patch(f"{API_PREFIX}/storage-usages/1/quota", json=payload)
    other_group = client.patch(f"{API_PREFIX}/groups/2/quota", json=payload)

    assert own_group.status_code == 200
    assert own_directory.status_code == 200
    assert other_group.status_code == 403
