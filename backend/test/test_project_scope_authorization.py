# -*- coding: utf-8 -*-
from datetime import datetime
from io import BytesIO

import models

from appConfig import base_config
from utils.security import issue_token


API_PREFIX = "/storage-pulse/api"


def _seed_scoped_resources(session):
    session.add_all(
        [
            models.User(id=1, rd_username="reader", username="Reader"),
            models.User(id=2, rd_username="other", username="Other"),
            models.User(id=3, rd_username="admin", username="Admin"),
            models.User(id=4, rd_username="project-admin", username="Project Admin"),
            models.Project(id=1, name="allowed-project", limit=100, used=20),
            models.Project(id=2, name="forbidden-project", limit=100, used=30),
            models.ProjectMembership(project_id=1, user_id=1, role="reader"),
            models.ProjectMembership(project_id=1, user_id=4, role="project_admin"),
            models.StorageCluster(
                id=1,
                name="cluster-a",
                storage_type="netapp",
                is_active=True,
                limit=200,
                used=50,
            ),
            models.GroupTag(id=1, name="production"),
            models.Group(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                in_charge_user_id=1,
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
            models.LargeFiles(
                id=1,
                user_id=1,
                group_id=1,
                linux_path="/data/allowed/reader/large.bin",
                size=100,
                updated_at=datetime.now(),
                created_at=datetime.now(),
            ),
            models.LargeFiles(
                id=2,
                user_id=2,
                group_id=2,
                linux_path="/data/forbidden/other/secret.bin",
                size=200,
                updated_at=datetime.now(),
                created_at=datetime.now(),
            ),
            models.StorageAlerts(
                id=1,
                source="diskpulse",
                alert_level="important",
                alert_type="capacity",
                threshold=80,
                avg_use_ratio=81,
                related_type="Group",
                related_id=1,
                updated_at=datetime.now(),
            ),
            models.StorageAlerts(
                id=2,
                source="diskpulse",
                alert_level="serious",
                alert_type="capacity",
                threshold=90,
                avg_use_ratio=91,
                related_type="Group",
                related_id=2,
                updated_at=datetime.now(),
            ),
            models.StorageAlerts(
                id=3,
                source="diskpulse",
                alert_level="info",
                alert_type="device",
                threshold=0,
                avg_use_ratio=0,
                related_type="node",
                related_id=99,
                updated_at=datetime.now(),
            ),
        ]
    )
    session.commit()


def _client(api_client_factory, routers, user_id):
    return api_client_factory(
        routers,
        headers={"Authorization": f"Bearer {issue_token(user_id)}"},
    )


def test_project_reader_cannot_bypass_scope_through_group_or_storage_usage_routes(
    api_client_factory,
    monkeypatch,
    session_factory,
):
    from routers import group, storage_usage

    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["admin"])
    session = session_factory()
    try:
        _seed_scoped_resources(session)
    finally:
        session.close()

    export_called = False

    def _export(*_args, **_kwargs):
        nonlocal export_called
        export_called = True
        return BytesIO(b"private export")

    monkeypatch.setattr(storage_usage.storageUsageCrud, "export_storage_usage_to_excel", _export)
    monkeypatch.setattr(
        storage_usage.storageUsageCrud,
        "get_storage_usages_real_time_data_by_id",
        lambda *_args, **_kwargs: [],
    )
    client = _client(api_client_factory, [group.router, storage_usage.router], user_id=1)

    groups = client.get(f"{API_PREFIX}/groups/?page=1&size=20")
    forbidden_group = client.get(f"{API_PREFIX}/groups/2")
    forbidden_usage = client.get(f"{API_PREFIX}/storage-usages/2")
    forbidden_usage_trend = client.get(f"{API_PREFIX}/storage-usages/2/realtime")
    forbidden_export = client.get(f"{API_PREFIX}/storage-usages/export/?export_type=excel")

    assert groups.status_code == 200
    assert [row["id"] for row in groups.json()["content"]] == [1]
    assert forbidden_group.status_code == 403
    assert forbidden_usage.status_code == 403
    assert forbidden_usage_trend.status_code == 403
    assert forbidden_export.status_code == 403
    assert export_called is False


def test_project_reader_filters_large_files_alerts_and_dashboard_before_pagination(
    api_client_factory,
    session_factory,
):
    from routers import dashboard, large_files, storage_alerts

    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["admin"])
    session = session_factory()
    try:
        _seed_scoped_resources(session)
    finally:
        session.close()

    client = _client(
        api_client_factory,
        [large_files.router, storage_alerts.router, dashboard.router],
        user_id=1,
    )

    large_files_response = client.get(f"{API_PREFIX}/large-files/?page=1&size=20")
    alerts_response = client.get(f"{API_PREFIX}/storage-alerts/?page=1&size=20")
    global_dashboard = client.get(f"{API_PREFIX}/dashboard/summary")
    own_project_dashboard = client.get(f"{API_PREFIX}/dashboard/summary?project_id=1")
    forbidden_project_dashboard = client.get(f"{API_PREFIX}/dashboard/summary?project_id=2")

    assert large_files_response.status_code == 200
    assert [row["linux_path"] for row in large_files_response.json()["content"]] == [
        "/data/allowed/reader/large.bin"
    ]
    assert alerts_response.status_code == 200
    assert [row["id"] for row in alerts_response.json()["content"]] == [1]
    assert global_dashboard.status_code == 403
    assert own_project_dashboard.status_code == 200
    assert forbidden_project_dashboard.status_code == 403


def test_unscoped_device_resource_routes_are_limited_to_super_admin(
    api_client_factory,
    session_factory,
):
    from routers import storage_cluster

    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["admin"])
    session = session_factory()
    try:
        _seed_scoped_resources(session)
    finally:
        session.close()

    reader = _client(api_client_factory, [storage_cluster.router], user_id=1)
    super_admin = _client(api_client_factory, [storage_cluster.router], user_id=3)

    assert reader.get(f"{API_PREFIX}/storage-clusters/").status_code == 403
    assert super_admin.get(f"{API_PREFIX}/storage-clusters/").status_code == 200


def test_project_capabilities_are_calculated_from_the_current_user_role(
    api_client_factory,
    session_factory,
):
    from routers import projects

    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["admin"])
    session = session_factory()
    try:
        _seed_scoped_resources(session)
    finally:
        session.close()

    reader = _client(api_client_factory, [projects.router], user_id=1)
    project_admin = _client(api_client_factory, [projects.router], user_id=4)
    super_admin = _client(api_client_factory, [projects.router], user_id=3)

    assert reader.get(f"{API_PREFIX}/projects/1").json()["capabilities"] == {
        "manage_members": False,
        "view_audit_events": False,
        "manage_project_admins": False,
    }
    assert project_admin.get(f"{API_PREFIX}/projects/1").json()["capabilities"] == {
        "manage_members": True,
        "view_audit_events": True,
        "manage_project_admins": False,
    }
    assert super_admin.get(f"{API_PREFIX}/projects/1").json()["capabilities"] == {
        "manage_members": True,
        "view_audit_events": True,
        "manage_project_admins": True,
    }


def test_quota_capabilities_only_enable_the_responsible_group_owner(
    api_client_factory,
    session_factory,
):
    from routers import group, storage_usage

    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["admin"])
    session = session_factory()
    try:
        _seed_scoped_resources(session)
    finally:
        session.close()

    owner = _client(api_client_factory, [group.router, storage_usage.router], user_id=1)
    other = _client(api_client_factory, [group.router, storage_usage.router], user_id=2)

    assert owner.get(f"{API_PREFIX}/groups/1").json()["capabilities"] == {"adjust_quota": True}
    assert owner.get(f"{API_PREFIX}/storage-usages/1").json()["capabilities"] == {"adjust_quota": True}
    assert other.get(f"{API_PREFIX}/groups/2").json()["capabilities"] == {"adjust_quota": False}
