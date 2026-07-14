# -*- coding: utf-8 -*-
import importlib
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import event

from appConfig import base_config
from celery_tasks.manager import remoteFileManager as remote_file_manager_module
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


@contextmanager
def capture_select_statements(db):
    statements = []
    engine = db.get_bind()

    def record_select(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(" ".join(statement.lower().split()))

    event.listen(engine, "before_cursor_execute", record_select)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record_select)


def selects_from(statements, table_name):
    return [statement for statement in statements if f" from {table_name}" in statement]


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


def test_user_alert_batches_questdb_ids_and_preloads_current_storage_scope(
    usage_scope, monkeypatch
):
    usage_scope.query(models.User).update({models.User.is_alert: True})
    usage_scope.commit()
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.config = SimpleNamespace()
    monkeypatch.setattr(
        storage_alert_module,
        "get_high_avg_usage",
        lambda **_kwargs: [(1, 91.0), (2, 92.0), (3, 93.0)],
    )
    usage_scope.expire_all()

    with capture_select_statements(usage_scope) as statements:
        alarm_data = alert.get_user_alarm_data(threshold=90, end_time=NOW)
        resolved = [
            importlib.import_module("utils.storageTarget").resolve_group_storage_target(
                storage_usage.group
            )
            for items in alarm_data.values()
            for storage_usage, _avg_use_ratio in items
        ]

    assert sum(len(items) for items in alarm_data.values()) == 3
    assert {item["target"].id for item in resolved} == {1, 2}
    assert len(selects_from(statements, "storage_usages")) == 1
    assert len(selects_from(statements, "users")) <= 1
    assert len(selects_from(statements, "groups")) <= 1
    assert len(selects_from(statements, "project_storage_environments")) <= 1
    assert len(selects_from(statements, "volumes")) <= 1
    assert len(selects_from(statements, "qtrees")) <= 1


def test_group_alert_resolves_questdb_ids_with_one_batched_group_query(
    usage_scope, monkeypatch
):
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.config = SimpleNamespace()
    monkeypatch.setattr(
        storage_alert_module,
        "get_high_avg_usage",
        lambda **_kwargs: [(1, 91.0), (2, 92.0), (3, 93.0)],
    )
    usage_scope.expire_all()

    with capture_select_statements(usage_scope) as statements:
        alarm_data = alert.get_project_group_alarm_data(threshold=90, end_time=NOW)

    assert sum(len(items) for items in alarm_data.values()) == 3
    assert len(selects_from(statements, "groups")) == 1


def test_disabled_group_is_excluded_from_group_and_user_alarm_data(
    usage_scope, monkeypatch
):
    group = usage_scope.get(models.Group, 1)
    group.enable_monitoring = False
    usage_scope.get(models.User, 1).is_alert = True
    usage_scope.commit()
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.config = SimpleNamespace()
    monkeypatch.setattr(
        storage_alert_module,
        "get_high_avg_usage",
        lambda **_kwargs: [(1, 91.0)],
    )

    assert alert.get_project_group_alarm_data(threshold=90, end_time=NOW) == {}
    assert alert.get_user_alarm_data(threshold=90, end_time=NOW) == {}


def test_group_alarm_batches_independent_top20_storage_usage_queries(
    usage_scope, monkeypatch
):
    usage_scope.query(models.StorageUsage).update({models.StorageUsage.used: 0})
    usage_scope.add_all(
        [
            models.StorageUsage(
                id=100 + (group_id - 1) * 22 + rank,
                storage_cluster_id=1,
                user_id=1,
                group_id=group_id,
                linux_path=f"/data/group-{group_id}/user-{rank}",
                used=float(rank),
                use_ratio=float(rank),
                updated_at=NOW,
            )
            for group_id in (1, 2)
            for rank in range(1, 23)
        ]
    )
    usage_scope.commit()
    groups = [usage_scope.get(models.Group, group_id) for group_id in (1, 2)]
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.logger = Mock()
    alert.config = SimpleNamespace(mail_to="ops@example.com")
    alert.model = "dev"
    alert.email = Mock()
    alert.get_project_group_alarm_data = Mock(
        return_value={"admin": [(groups[0], 91.0), (groups[1], 92.0)]}
    )
    alert.add_email_company_info = lambda data, threshold=None: data
    alert.write_alerts_to_mysql = Mock()
    serialized_usages = []

    class SerializedUsage:
        def __init__(self, storage_usage):
            self.storage_usage = storage_usage

        def model_dump(self):
            payload = {
                "id": self.storage_usage.id,
                "used": self.storage_usage.used,
                "user": self.storage_usage.user.rd_username,
                "group_id": self.storage_usage.group.id,
            }
            serialized_usages.append(payload)
            return payload

    monkeypatch.setattr(
        storage_alert_module.storageUsageSchema.StorageUsage,
        "model_validate",
        SerializedUsage,
    )
    usage_scope.expire_all()

    with capture_select_statements(usage_scope) as statements:
        alert.group_alarm_daily(threshold=90, end_time=NOW)

    top20_by_group = {
        group_id: [usage["used"] for usage in serialized_usages if usage["group_id"] == group_id]
        for group_id in (1, 2)
    }
    assert top20_by_group == {
        1: [float(value) for value in range(22, 2, -1)],
        2: [float(value) for value in range(22, 2, -1)],
    }
    assert len(selects_from(statements, "storage_usages")) == 1
    assert len(selects_from(statements, "users")) <= 1
    assert len(selects_from(statements, "groups")) <= 1


def test_group_alarm_real_storage_usage_schema_completes_email_and_persistence(
    usage_scope,
):
    group = usage_scope.get(models.Group, 1)
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.logger = Mock()
    alert.config = SimpleNamespace(mail_to="ops@example.com")
    alert.model = "dev"
    alert.email = Mock()
    alert.get_project_group_alarm_data = Mock(
        return_value={"admin": [(group, 91.0)]}
    )
    alert.add_email_company_info = lambda data, threshold=None: data
    alert.write_alerts_to_mysql = Mock()

    alert.group_alarm_daily(threshold=90, end_time=NOW)

    assert alert.logger.error.call_args_list == []
    assert alert.email.send_email_via_template.call_count == 1
    assert alert.write_alerts_to_mysql.call_count == 1


def test_group_alert_reads_current_environment_and_target_by_stable_id(
    usage_scope, session_factory, monkeypatch
):
    with session_factory() as writer:
        writer.add(
            models.ProjectStorageEnvironment(
                id=3,
                project_id=1,
                storage_cluster_id=2,
                name="environment-current",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        group = writer.get(models.Group, 1)
        group.project_environment_id = 3
        group.storage_cluster_id = 2
        group.volume_id = 2
        group.qtree_id = None
        writer.commit()

    monkeypatch.setattr(
        storage_alert_module,
        "get_high_avg_usage",
        lambda **_kwargs: [(1, 91.0)],
    )
    with session_factory() as task_db:
        alert = object.__new__(StorageAlert)
        alert.db = task_db
        alert.config = SimpleNamespace()

        alarm_data = alert.get_project_group_alarm_data(threshold=90, end_time=NOW)
        group = next(iter(alarm_data.values()))[0][0]
        target = importlib.import_module("utils.storageTarget").resolve_group_storage_target(group)

        assert group.project_environment.name == "environment-current"
        assert target["target_type"] == "volume"
        assert target["target"].id == 2
        assert target["storage_cluster"].id == 2


def test_project_alert_batches_questdb_ids_and_preloads_owner(usage_scope, monkeypatch):
    usage_scope.get(models.Project, 1).in_charge_user_id = 2
    usage_scope.get(models.Project, 2).in_charge_user_id = 3
    usage_scope.commit()
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.config = SimpleNamespace()
    monkeypatch.setattr(
        storage_alert_module,
        "get_high_avg_usage",
        lambda **_kwargs: [(1, 51.0), (2, 52.0)],
    )
    usage_scope.expire_all()

    with capture_select_statements(usage_scope) as statements:
        alarm_data = alert.get_project_alarm_data(end_time=NOW)

    assert sum(len(items) for items in alarm_data.values()) == 2
    assert set(alarm_data) == {"bob@example.com", "carol@example.com"}
    assert len(selects_from(statements, "projects")) == 1
    assert len(selects_from(statements, "users")) <= 1


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


def test_group_alert_derives_project_from_environment(usage_scope):
    group = models.Group(
        id=4,
        project_environment_id=1,
        volume_id=1,
        name="environment-only-group",
    )
    usage_scope.add(group)
    usage_scope.commit()
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.logger = Mock()

    alert.write_alerts_to_mysql(
        data=[(group, 91.0)],
        model=models.Group,
        threshold=80,
        description_template="group {name} reached {avg_use_ratio}%",
    )

    stored = usage_scope.query(models.StorageAlerts).one()
    assert stored.related_info["project"] == {"id": 1, "name": "project-a"}


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


def test_system_alert_batches_each_questdb_resource_type_once(usage_scope):
    for volume in usage_scope.query(models.Volume).all():
        volume.vserver = "svm"
        volume.aggregate = "aggregate"
        volume.type = "rw"
        volume.state = "online"
    usage_scope.get(models.Qtree, 1).style = "unix"
    usage_scope.get(models.Qtree, 1).oplocks = "enabled"
    usage_scope.get(models.Qtree, 1).status = "normal"
    usage_scope.add_all(
        [
            models.Aggregate(id=1, storage_cluster_id=1, name="aggregate-a", used=10),
            models.Aggregate(id=2, storage_cluster_id=2, name="aggregate-b", used=20),
            models.Qtree(
                id=2,
                storage_cluster_id=2,
                volume_id=2,
                name="qtree-b",
                limit=2048,
                style="unix",
                oplocks="enabled",
                status="normal",
            ),
        ]
    )
    usage_scope.commit()
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.logger = Mock()
    alert.email = Mock()
    alert.get_system_alarm_data = Mock(
        return_value=(
            [(1, 91.0), (2, 92.0)],
            [(1, 91.0), (2, 92.0)],
            [(1, 91.0), (2, 92.0)],
        )
    )
    alert.write_alerts_to_mysql = Mock()
    alert.add_email_company_info = lambda data, threshold=None: data
    usage_scope.expire_all()

    with capture_select_statements(usage_scope) as statements:
        alert.system_alarm_daily(threshold=90)

    assert alert.email.send_email_via_template.call_count == 1
    assert (
        len(selects_from(statements, "aggregates")),
        len(selects_from(statements, "volumes")),
        len(selects_from(statements, "qtrees")),
    ) == (1, 1, 1)


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


def test_project_weekly_report_keeps_legacy_groups_in_unbound_environment_section(usage_scope):
    usage_scope.add(
        models.Group(
            id=5,
            project_id=1,
            project_environment_id=None,
            storage_cluster_id=1,
            qtree_id=1,
            name="legacy-group",
            linux_path="/legacy/group",
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

    project_data = alert.email.send_email_via_template.call_args.kwargs["data"]["project_usages"][0]
    section = next(
        item
        for item in project_data["environment_usages"]
        if item["project_environment"]["id"] is None
    )
    assert section["project_environment"] == {"id": None, "name": "未绑定环境"}
    assert {group["id"] for group in section["group_usages"]} == {5}


def test_project_weekly_report_batches_groups_and_preloads_environment_and_owner(usage_scope):
    alert = object.__new__(StorageAlert)
    alert.db = usage_scope
    alert.logger = Mock()
    alert.config = SimpleNamespace(mail_to="ops@example.com")
    alert.model = "dev"
    alert.email = Mock()
    alert.add_email_company_info = lambda data: data
    alert.write_alerts_to_mysql = Mock()
    projects = [usage_scope.get(models.Project, project_id) for project_id in (1, 2)]
    alert.get_project_alarm_data = Mock(
        return_value={"admin": [(projects[0], 55.0), (projects[1], 45.0)]}
    )
    usage_scope.expire_all()

    with capture_select_statements(usage_scope) as statements:
        alert.project_alarm_weekly()

    assert len(selects_from(statements, "groups")) == 1
    assert len(selects_from(statements, "project_storage_environments")) <= 1
    assert len(selects_from(statements, "users")) <= 1


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


def test_backup_path_derives_project_from_environment(usage_scope):
    usage_scope.add_all(
        [
            models.Group(
                id=4,
                project_environment_id=1,
                volume_id=1,
                name="environment-only-group",
            ),
            models.StorageUsage(
                id=4,
                storage_cluster_id=1,
                user_id=3,
                group_id=4,
                linux_path="/data/environment-only-group/carol",
                updated_at=NOW,
            ),
        ]
    )
    usage_scope.commit()
    manager = object.__new__(RemoteFileManager)
    manager.db = usage_scope
    manager.storage_config = SimpleNamespace(back_up_dir="/backup")
    manager.logger = Mock()

    destination = manager.get_back_up_destination_path_by_id(storage_usage_id=4)

    assert destination == os.path.join(
        "/backup", "project-a", "environment-a", "environment-only-group", "carol"
    )


def test_backup_by_stable_usage_id_reads_storage_usage_once(usage_scope):
    manager = object.__new__(RemoteFileManager)
    manager.db = usage_scope
    manager.storage_config = SimpleNamespace(
        back_up_enabled=True,
        back_up_dir="/backup",
    )
    manager.logger = Mock()
    manager.directory_exists = Mock(return_value=True)
    usage_scope.expire_all()

    with capture_select_statements(usage_scope) as statements:
        result = manager.back_up_user_directory_by_storage_usage_id(
            storage_usage_id=1,
            closed=True,
        )

    assert result[0] is True
    assert len(selects_from(statements, "storage_usages")) == 1


def test_quit_user_backup_batches_current_usages_and_completed_records(
    usage_scope, session_factory
):
    users = usage_scope.query(models.User).filter(models.User.id.in_([2, 3])).all()
    for user in users:
        user.user_type = 0
        user.quit_days = 40
    usage_scope.add(
        models.StorageUsage(
            id=4,
            storage_cluster_id=1,
            user_id=3,
            group_id=1,
            linux_path="/data/volume-group/carol",
            used=15,
            use_ratio=15,
            updated_at=NOW,
        )
    )
    usage_scope.add(
        models.StorageBackUpRecord(
            id=2,
            user_id=2,
            source_path="/data/qtree-group/bob",
            destination_path="/backup/already-complete/bob",
            start_time=NOW,
            end_time=NOW,
            status=2,
        )
    )
    usage_scope.commit()
    with session_factory() as writer:
        writer.get(models.ProjectStorageEnvironment, 1).name = "environment-current"
        writer.commit()

    with session_factory() as task_db:
        manager = object.__new__(RemoteFileManager)
        manager.db = task_db
        manager.logger = Mock()
        manager.storage_config = SimpleNamespace(
            back_up_enabled=True,
            back_up_quit_days=30,
            back_up_dir="/backup",
            file_manage_user="backup",
            mail_to="",
        )
        manager.email = Mock()
        manager.add_email_company_info = lambda data: data
        manager.directory_exists = Mock(return_value=True)
        manager.rsync_directory = Mock(return_value=True)
        manager.delete_directory = Mock(return_value=True)
        manager.change_owner = Mock(return_value=True)
        manager.change_permissions = Mock(return_value=True)

        with capture_select_statements(task_db) as statements:
            assert manager.back_up_quit_users_storage_usages() is True

        completed = task_db.query(models.StorageBackUpRecord).filter_by(
            source_path="/data/volume-group/carol"
        ).one()
        assert "environment-current" in completed.destination_path
        assert (
            len(selects_from(statements, "storage_usages")),
            len(selects_from(statements, "storage_back_up_records")),
        ) == (1, 1)


def test_delete_backup_reuses_expired_records_without_id_requeries(usage_scope):
    expired_at = NOW.replace(year=2025)
    existing = usage_scope.get(models.StorageBackUpRecord, 1)
    existing.end_time = expired_at
    existing.status = 2
    usage_scope.add(
        models.StorageBackUpRecord(
            id=2,
            user_id=2,
            source_path="/data/qtree-group/bob",
            destination_path="/backup/project/environment/group/bob",
            start_time=expired_at,
            end_time=expired_at,
            status=2,
        )
    )
    usage_scope.commit()
    manager = object.__new__(RemoteFileManager)
    manager.db = usage_scope
    manager.logger = Mock()
    manager.storage_config = SimpleNamespace(
        back_up_enabled=True,
        back_up_duration=30,
        mail_to="",
    )
    manager.email = Mock()
    manager.add_email_company_info = lambda data: data
    manager.delete_directory = Mock(return_value=True)
    usage_scope.expire_all()

    with capture_select_statements(usage_scope) as statements:
        manager.delete_back_up()

    sent = manager.email.send_email_via_template.call_args.kwargs["data"]
    assert {record["id"] for record in sent["storage_back_up_records"]} == {1, 2}
    assert {record["status"] for record in sent["storage_back_up_records"]} == {5}
    assert len(selects_from(statements, "storage_back_up_records")) == 1


def test_bpm_backup_batches_current_usages_records_and_destination_paths(
    usage_scope, session_factory, monkeypatch
):
    users = usage_scope.query(models.User).filter(models.User.id.in_([2, 3])).all()
    for user in users:
        user.user_type = 0
        user.quit_days = 10
    usage_scope.get(models.Group, 1).in_charge_user_id = 2
    usage_scope.add(
        models.StorageUsage(
            id=4,
            storage_cluster_id=1,
            user_id=3,
            group_id=1,
            linux_path="/data/volume-group/carol",
            used=15,
            use_ratio=15,
            updated_at=NOW,
        )
    )
    usage_scope.commit()
    with session_factory() as writer:
        writer.get(models.ProjectStorageEnvironment, 1).name = "environment-current"
        writer.commit()

    class FakeIamApi:
        def __init__(self, **_kwargs):
            pass

        def set_up(self):
            pass

        def initiating_bpm_process(self, data):
            return f"bpm-{data['formData']['storageUsageId']}"

    monkeypatch.setattr(remote_file_manager_module, "IamApi", FakeIamApi)
    with session_factory() as task_db:
        manager = object.__new__(RemoteFileManager)
        manager.db = task_db
        manager.logger = Mock()
        manager.storage_config = SimpleNamespace(
            back_up_enabled=True,
            back_up_quit_days=30,
            back_up_dir="/backup",
        )
        manager.directory_exists = Mock(return_value=True)

        with capture_select_statements(task_db) as statements:
            manager.initiating_quit_users_bpm_process()

        created = task_db.query(models.StorageBackUpRecord).filter(
            models.StorageBackUpRecord.process_uid.isnot(None)
        ).all()
        assert {record.source_path for record in created} == {
            "/data/qtree-group/bob",
            "/data/volume-group/carol",
        }
        assert all("environment-current" in record.destination_path for record in created)
        assert (
            len(selects_from(statements, "storage_usages")),
            len(selects_from(statements, "storage_back_up_records")),
        ) == (1, 1)
