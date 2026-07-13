# -*- coding: utf-8 -*-
import importlib
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from appConfig import base_config
from celery_tasks.manager import storageAlert as storage_alert_module
from celery_tasks.manager.remoteFileManager import RemoteFileManager
from celery_tasks.manager.storageAlert import StorageAlert
from celery_tasks.manager.storageMonitor import StorageManagement
from crud import storageUsageCrud
import models
from routers import storage_usage
from utils.security import issue_token


NOW = datetime.fromisoformat("2026-07-13T10:00:00")
API_PREFIX = "/storage-pulse/api"


@pytest.fixture
def usage_scope(db_session):
    db_session.add_all(
        [
            models.User(id=1, rd_username="admin", username="Admin", email="admin@example.com"),
            models.User(id=2, rd_username="bob", username="Bob", email="bob@example.com"),
            models.User(id=3, rd_username="carol", username="Carol", email="carol@example.com"),
            models.Project(id=1, name="project-a"),
            models.Project(id=2, name="project-b"),
            models.StorageCluster(
                id=1,
                name="netapp-a",
                storage_type="netapp",
                storage_host="netapp-a.internal",
                storage_user="collector",
                storage_password="secret-a",
            ),
            models.StorageCluster(
                id=2,
                name="isilon-b",
                storage_type="isilon",
                storage_host="isilon-b.internal",
                storage_user="collector",
                storage_password="secret-b",
            ),
        ]
    )
    db_session.flush()
    db_session.add_all(
        [
            models.ProjectStorageEnvironment(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                name="environment-a",
                created_at=NOW,
                updated_at=NOW,
            ),
            models.ProjectStorageEnvironment(
                id=2,
                project_id=2,
                storage_cluster_id=2,
                name="environment-b",
                created_at=NOW,
                updated_at=NOW,
            ),
            models.Volume(id=1, storage_cluster_id=1, name="volume-a", limit=4096),
            models.Volume(id=2, storage_cluster_id=2, name="volume-b", limit=4096),
        ]
    )
    db_session.flush()
    db_session.add(
        models.Qtree(
            id=1,
            storage_cluster_id=1,
            volume_id=1,
            name="null",
            limit=2048,
        )
    )
    db_session.flush()
    db_session.add_all(
        [
            models.Group(
                id=1,
                project_id=1,
                project_environment_id=1,
                storage_cluster_id=1,
                volume_id=1,
                name="volume-group",
                linux_path="/data/volume-group",
                limit=1024,
            ),
            models.Group(
                id=2,
                project_id=1,
                project_environment_id=1,
                storage_cluster_id=1,
                qtree_id=1,
                in_charge_user_id=2,
                name="qtree-group",
                linux_path="/data/qtree-group",
                limit=1024,
            ),
            models.Group(
                id=3,
                project_id=2,
                project_environment_id=2,
                storage_cluster_id=2,
                volume_id=2,
                name="other-group",
                linux_path="/data/other-group",
                limit=1024,
            ),
        ]
    )
    db_session.flush()
    db_session.add_all(
        [
            models.StorageUsage(
                id=1,
                storage_cluster_id=1,
                user_id=1,
                group_id=1,
                linux_path="/data/volume-group/admin",
                used=30,
                use_ratio=30,
                updated_at=NOW,
            ),
            models.StorageUsage(
                id=2,
                storage_cluster_id=1,
                user_id=2,
                group_id=2,
                linux_path="/data/qtree-group/bob",
                used=20,
                use_ratio=20,
                updated_at=NOW,
            ),
            models.StorageUsage(
                id=3,
                storage_cluster_id=2,
                user_id=1,
                group_id=3,
                linux_path="/data/other-group/admin",
                used=10,
                use_ratio=10,
                updated_at=NOW,
            ),
            models.StorageBackUpRecord(
                id=1,
                user_id=1,
                source_path="/legacy/source/admin",
                destination_path="/legacy/project-a/volume-group/admin",
                start_time=NOW,
                end_time=NOW,
                status=2,
            ),
        ]
    )
    db_session.commit()
    return db_session


@pytest.fixture
def usage_api(api_client_factory, session_factory, usage_scope, monkeypatch):
    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["admin"])
    monkeypatch.setattr(
        storage_usage,
        "create_user_folder_by_storage_usage_id",
        lambda *_args, **_kwargs: None,
    )
    return api_client_factory(
        [storage_usage.router],
        authenticated=True,
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )


@pytest.mark.parametrize(
    ("params", "expected_ids"),
    [
        ({"project_id": 1}, {1, 2}),
        ({"project_environment_id": 1}, {1, 2}),
        ({"group_id": 1}, {1}),
        ({"storage_cluster_id": 2}, {3}),
        ({"user_id": 2}, {2}),
    ],
)
def test_storage_usage_list_filters_complete_environment_scope(usage_api, params, expected_ids):
    response = usage_api.get(f"{API_PREFIX}/storage-usages/", params=params)

    assert response.status_code == 200
    assert {item["id"] for item in response.json()["content"]} == expected_ids


def test_storage_usage_response_uses_redacted_environment_and_target_summaries(usage_api):
    response = usage_api.get(f"{API_PREFIX}/storage-usages/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"] == {"id": 1, "name": "project-a"}
    assert payload["project_environment"] == {"id": 1, "name": "environment-a"}
    assert payload["storage_cluster"] == {
        "id": 1,
        "name": "netapp-a",
        "storage_type": "netapp",
    }
    assert payload["storage_target"] == {"type": "volume", "id": 1, "name": "volume-a"}


def test_storage_usage_create_and_update_derive_cluster_and_target_from_group(usage_api):
    created = usage_api.post(
        f"{API_PREFIX}/storage-usages/",
        json={"user_id": 3, "group_id": 1},
    )

    assert created.status_code == 200
    assert created.json()["storage_cluster"]["id"] == 1
    assert created.json()["storage_target"] == {
        "type": "volume",
        "id": 1,
        "name": "volume-a",
    }

    updated = usage_api.put(
        f"{API_PREFIX}/storage-usages/{created.json()['id']}",
        json={
            "user_id": 3,
            "group_id": 2,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["storage_cluster"]["id"] == 1
    assert updated.json()["storage_target"] == {
        "type": "qtree",
        "id": 1,
        "name": "null",
    }


def test_storage_usage_export_starts_with_traceable_environment_columns(usage_scope):
    exported = storageUsageCrud.get_export_data(usage_scope, project_environment_id=1)

    assert list(exported.columns[:8]) == [
        "项目",
        "项目环境",
        "存储集群",
        "存储类型",
        "项目组",
        "Volume",
        "Qtree",
        "路径",
    ]
    assert set(exported["项目环境"]) == {"environment-a"}


def test_storage_usage_export_preserves_legacy_rows_without_group(usage_scope):
    usage_scope.add(
        models.StorageUsage(
            id=4,
            storage_cluster_id=1,
            user_id=1,
            group_id=None,
            linux_path="/legacy/orphan/admin",
            used=5,
            use_ratio=5,
            updated_at=NOW,
        )
    )
    usage_scope.commit()

    exported = storageUsageCrud.get_export_data(usage_scope)

    legacy = exported.loc[exported["路径"] == "/legacy/orphan/admin"].iloc[0]
    assert legacy["项目环境"] == ""
    assert legacy["Volume"] == ""
    assert legacy["Qtree"] == ""


@pytest.mark.parametrize(
    ("group_id", "expected_type", "expected_target_id"),
    [(1, "volume", 1), (2, "qtree", 1)],
)
def test_shared_group_target_resolver_handles_volume_and_qtree(
    usage_scope, group_id, expected_type, expected_target_id
):
    target_module = importlib.import_module("utils.storageTarget")
    group = usage_scope.get(models.Group, group_id)

    resolved = target_module.resolve_group_storage_target(group)

    assert set(resolved) == {"target_type", "target", "volume", "storage_cluster"}
    assert resolved["target_type"] == expected_type
    assert resolved["target"].id == expected_target_id
    assert resolved["volume"].id == 1
    assert resolved["storage_cluster"].id == 1


def test_group_expansion_dispatches_by_bound_target_id_not_qtree_name(usage_scope, monkeypatch):
    manager = object.__new__(StorageManagement)
    manager.db = usage_scope
    manager.logger = Mock()
    expand_volume = Mock(return_value=(True, "volume expanded"))
    expand_qtree = Mock(return_value=(True, "qtree expanded"))
    monkeypatch.setattr(manager, "_expand_volume", expand_volume)
    monkeypatch.setattr(manager, "_expand_qtree", expand_qtree)
    monkeypatch.setattr(manager, "_create_alert", Mock())

    assert manager._expand_group(group_id=1, size=1) == (True, "volume expanded")
    expand_volume.assert_called_once_with(volume_id=1, size=1)

    assert manager._expand_group(group_id=2, size=1) == (True, "qtree expanded")
    expand_qtree.assert_called_once_with(qtree_id=1, size=1)


def test_group_alert_data_includes_volume_bound_groups(usage_scope, monkeypatch):
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.config = SimpleNamespace()
    monkeypatch.setattr(storage_alert_module, "get_high_avg_usage", lambda **_kwargs: [(1, 91.0)])

    alarm_data = alert.get_project_group_alarm_data(threshold=90, end_time=NOW)

    assert list(alarm_data) == ["admin"]
    assert alarm_data["admin"][0][0].id == 1


def test_group_alert_persists_minimal_project_environment_context(usage_scope):
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.logger = Mock()
    group = usage_scope.get(models.Group, 1)

    alert.write_alerts_to_mysql(
        data=[(group, 91.0)],
        model=models.Group,
        threshold=80,
        description_template="项目组{name}使用率达到{avg_use_ratio}%",
    )

    stored = usage_scope.query(models.StorageAlerts).one()
    assert stored.related_info == {
        "project": {"id": 1, "name": "project-a"},
        "project_environment": {"id": 1, "name": "environment-a"},
        "group": {"id": 1, "name": "volume-group"},
    }


def test_environment_alert_is_stored_against_project_storage_environment(usage_scope):
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.logger = Mock()
    environment = usage_scope.get(models.ProjectStorageEnvironment, 1)

    alert.write_alerts_to_mysql(
        data=[(environment, 88.0)],
        model=models.ProjectStorageEnvironment,
        threshold=80,
        description_template="环境{name}使用率达到{avg_use_ratio}%",
    )

    stored = usage_scope.query(models.StorageAlerts).one()
    assert stored.related_type == "ProjectStorageEnvironment"
    assert stored.related_id == 1


def test_project_weekly_report_keeps_flat_groups_and_sections_by_environment(usage_scope):
    usage_scope.add(
        models.ProjectStorageEnvironment(
            id=3,
            project_id=1,
            storage_cluster_id=2,
            name="environment-c",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    usage_scope.flush()
    usage_scope.add(
        models.Group(
            id=4,
            project_id=1,
            project_environment_id=3,
            storage_cluster_id=2,
            volume_id=2,
            name="volume-group",
            linux_path="/data/environment-c/volume-group",
            limit=1024,
        )
    )
    usage_scope.commit()

    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.logger = Mock()
    alert.config = SimpleNamespace(mail_to="ops@example.com")
    alert.model = "dev"
    alert.email = Mock()
    project = usage_scope.get(models.Project, 1)
    alert.get_project_alarm_data = Mock(return_value={"admin": [(project, 55.0)]})
    alert.add_email_company_info = lambda data: data
    alert.write_alerts_to_mysql = Mock()

    alert.project_alarm_weekly()

    sent = alert.email.send_email_via_template.call_args.kwargs
    assert sent["recipient"] == ["ops@example.com"]
    project_data = sent["data"]["project_usages"][0]
    assert {group["id"] for group in project_data["group_usages"]} == {1, 2, 4}

    sections = {
        section["project_environment"]["id"]: section
        for section in project_data["environment_usages"]
    }
    assert sections[1]["project_environment"] == {"id": 1, "name": "environment-a"}
    assert {group["id"] for group in sections[1]["group_usages"]} == {1, 2}
    assert {group["name"] for group in sections[1]["group_usages"]} == {
        "volume-group",
        "qtree-group",
    }
    assert sections[3]["project_environment"] == {"id": 3, "name": "environment-c"}
    assert {group["id"] for group in sections[3]["group_usages"]} == {4}
    assert {group["name"] for group in sections[3]["group_usages"]} == {"volume-group"}


def test_project_weekly_template_renders_environment_sections():
    template = (
        Path(__file__).resolve().parents[1]
        / "utils"
        / "mailTools"
        / "template"
        / "projectAlarmWeekly.html"
    ).read_text(encoding="utf-8")

    assert "project.environment_usages" in template
    assert "environment.project_environment.name" in template
    assert "environment.group_usages" in template


def test_new_backup_path_includes_environment_without_moving_legacy_record(usage_scope):
    manager = object.__new__(RemoteFileManager)
    manager.db = usage_scope
    manager.storage_config = SimpleNamespace(back_up_dir="/backup")
    manager.logger = Mock()

    destination = manager.get_back_up_destination_path_by_id(storage_usage_id=1)

    assert destination == os.path.join(
        "/backup", "project-a", "environment-a", "volume-group", "admin"
    )
    assert usage_scope.get(models.StorageBackUpRecord, 1).destination_path == (
        "/legacy/project-a/volume-group/admin"
    )
