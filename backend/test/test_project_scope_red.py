# -*- coding: utf-8 -*-
from datetime import datetime

import models

from appConfig import base_config
from schemas.aiSchema import ConversationCreate
from utils.security import issue_token


API_PREFIX = "/storage-pulse/api"


def _auth_client(api_client_factory, router, user_id: int):
    return api_client_factory(
        [router],
        headers={"Authorization": f"Bearer {issue_token(user_id)}"},
    )


def test_ai_conversation_is_owner_scoped_without_project_binding(
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
                models.User(id=2, rd_username="other", username="Other"),
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

    created = client.post(
        f"{API_PREFIX}/ai/conversations",
        json={"title": "personal conversation", "model_id": 1},
    )

    assert "project_id" not in ConversationCreate.model_fields
    assert "project_id" not in models.AIConversation.__table__.columns
    assert created.status_code == 201
    assert "project_id" not in created.json()

    other_client = _auth_client(api_client_factory, ai.router, user_id=2)
    assert other_client.get(f"{API_PREFIX}/ai/conversations/{created.json()['id']}").status_code == 404


def test_ai_accessible_storage_usage_endpoint_dynamically_filters_current_user_projects_before_pagination(
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
        lambda _db, group_id, request, current_user=None, audit_context=None: {
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
        lambda _db, storage_usage_id, request, current_user=None, audit_context=None: {
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
