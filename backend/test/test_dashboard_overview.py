# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from models import (
    Group,
    GroupTag,
    Project,
    StorageAlerts,
    StorageCluster,
    StorageUsage,
    User,
    Volume,
)


def seed_dashboard_data(db):
    cluster = StorageCluster(
        name="cluster-a",
        storage_type="netapp",
        is_active=True,
        limit=1000,
        used=600,
        use_ratio=60,
    )
    inactive_cluster = StorageCluster(
        name="cluster-off",
        storage_type="isilon",
        is_active=False,
        limit=500,
        used=450,
        use_ratio=90,
    )
    project = Project(name="项目 A", limit=300, used=200, use_ratio=66.67)
    common = Project(name="Common", is_common=True, limit=100, used=50, use_ratio=50)
    tag = GroupTag(name="研发")
    db.add_all([cluster, inactive_cluster, project, common, tag])
    db.flush()

    volume = Volume(name="volume-a", storage_cluster_id=cluster.id, limit=200, used=120)
    db.add(volume)
    db.flush()
    group = Group(
        name="项目组 A",
        project_id=project.id,
        storage_cluster_id=cluster.id,
        group_tag_id=tag.id,
        volume_id=volume.id,
        enable_monitoring=True,
        limit=120,
        used=90,
        use_ratio=75,
    )
    db.add(group)
    db.flush()

    alice = User(username="Alice", rd_username="alice")
    bob = User(username="Bob", rd_username="bob")
    db.add_all([alice, bob])
    db.flush()
    db.add_all([
        StorageUsage(
            storage_cluster_id=cluster.id,
            group_id=group.id,
            user_id=alice.id,
            linux_path="/project-a/alice-1",
            limit=50,
            used=25,
        ),
        StorageUsage(
            storage_cluster_id=cluster.id,
            group_id=group.id,
            user_id=alice.id,
            linux_path="/project-a/alice-2",
            limit=30,
            used=15,
        ),
        StorageUsage(
            storage_cluster_id=cluster.id,
            group_id=group.id,
            user_id=bob.id,
            linux_path="/project-a/bob",
            limit=40,
            used=30,
        ),
    ])

    now = datetime.now()
    db.add_all([
        StorageAlerts(
            source="diskpulse",
            alert_type="alert",
            event_type="trigger",
            alert_level="important",
            related_type="Group",
            related_id=group.id,
            updated_at=now - timedelta(days=1),
        ),
        StorageAlerts(
            source="diskpulse",
            alert_type="alert",
            event_type="trigger",
            alert_level="serious",
            related_type="Group",
            related_id=group.id,
            updated_at=now - timedelta(days=2),
        ),
        StorageAlerts(
            source="diskpulse",
            alert_type="quota_adjustment",
            event_type="trigger",
            related_type="Group",
            related_id=group.id,
            updated_at=now - timedelta(days=1),
        ),
        StorageAlerts(
            source="vendor",
            alert_type="alert",
            event_type="trigger",
            related_type="Group",
            related_id=group.id,
            updated_at=now - timedelta(days=1),
        ),
    ])
    db.commit()
    return project


def test_dashboard_service_builds_independent_global_and_project_data(db_session, monkeypatch):
    from services import dashboardService

    project = seed_dashboard_data(db_session)
    monkeypatch.setattr(
        dashboardService.dashboardCrud,
        "get_capacity_trend",
        lambda **_kwargs: [[datetime(2026, 7, 16), 590], [datetime(2026, 7, 17), 600]],
    )

    global_summary = dashboardService.get_summary(db_session)
    assert global_summary["scope"]["mode"] == "global"
    assert global_summary["summary"] == {
        "limit_gb": 1000.0,
        "used_gb": 600.0,
        "available_gb": 400.0,
        "use_ratio": 60.0,
        "storage_cluster_count": 1,
        "alert_count": 2,
    }
    assert [item["name"] for item in dashboardService.get_capacity_items(db_session)] == ["项目 A"]
    assert dashboardService.get_capacity_items(db_session, use_ratio_min=70) == []
    assert dashboardService.get_capacity_trend(db_session)[-1]["used_gb"] == 600.0
    assert dashboardService.get_alert_levels(db_session) == [
        {"level": "important", "name": "重要", "count": 1},
        {"level": "serious", "name": "严重", "count": 1},
    ]

    project_summary = dashboardService.get_summary(db_session, project_id=project.id)
    assert project_summary["scope"]["mode"] == "project"
    assert project_summary["scope"]["project_name"] == "项目 A"
    assert project_summary["summary"]["limit_gb"] == 300.0
    assert project_summary["summary"]["used_gb"] == 200.0
    assert project_summary["summary"]["storage_cluster_count"] == 1
    assert [item["name"] for item in dashboardService.get_capacity_items(db_session, project.id)] == ["项目组 A"]
    assert [
        item["name"]
        for item in dashboardService.get_capacity_items(
            db_session,
            project.id,
            use_ratio_min=70,
            use_ratio_max=80,
        )
    ] == ["项目组 A"]
    assert project_summary["summary"]["alert_count"] == 2

    top_users = dashboardService.get_top_users(db_session, project.id)
    assert top_users == [
        {"id": top_users[0]["id"], "name": "alice", "used_gb": 40.0},
        {"id": top_users[1]["id"], "name": "bob", "used_gb": 30.0},
    ]


def test_dashboard_service_keeps_snapshots_when_questdb_is_unavailable(db_session, monkeypatch):
    from services import dashboardService

    seed_dashboard_data(db_session)

    def fail_trend(**_kwargs):
        raise RuntimeError("questdb unavailable")

    monkeypatch.setattr(dashboardService.dashboardCrud, "get_capacity_trend", fail_trend)
    assert dashboardService.get_summary(db_session)["summary"]["used_gb"] == 600.0
    assert dashboardService.get_capacity_trend(db_session) == []


def test_global_capacity_trend_binds_cluster_symbol_ids(monkeypatch):
    from crud import dashboardCrud

    captured = {}

    class FakeQuestDB:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, query, params):
            captured["query"] = str(query)
            captured["params"] = params
            return SimpleNamespace(all=lambda: [])

    monkeypatch.setattr(
        dashboardCrud,
        "get_active_clusters",
        lambda _db: [SimpleNamespace(id=2), SimpleNamespace(id=1)],
    )
    monkeypatch.setattr(dashboardCrud, "QuestDBSession", FakeQuestDB)

    dashboardCrud.get_capacity_trend(
        db=object(),
        project_id=None,
        start_time=datetime(2026, 6, 18),
        end_time=datetime(2026, 7, 17),
    )

    assert captured["params"]["cluster_ids"] == ["2", "1"]
    assert "IN (2, 1)" not in captured["query"]


@pytest.mark.parametrize("project_id", [None, 9])
def test_capacity_trend_binds_aware_questdb_times_as_utc_strings(monkeypatch, project_id):
    from crud import dashboardCrud

    captured = {}

    class FakeQuestDB:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, _query, params):
            captured["params"] = params
            return SimpleNamespace(all=lambda: [])

    monkeypatch.setattr(
        dashboardCrud,
        "get_active_clusters",
        lambda _db: [SimpleNamespace(id=2)],
    )
    monkeypatch.setattr(dashboardCrud, "QuestDBSession", FakeQuestDB)

    dashboardCrud.get_capacity_trend(
        db=object(),
        project_id=project_id,
        start_time=datetime(2026, 6, 18, tzinfo=timezone.utc),
        end_time=datetime(2026, 7, 17, tzinfo=timezone.utc),
    )

    assert captured["params"]["start_time"] == "2026-06-18T00:00:00Z"
    assert captured["params"]["end_time"] == "2026-07-17T00:00:00Z"


def test_capacity_trend_interprets_naive_query_times_as_system_wall_time(monkeypatch):
    from crud import dashboardCrud

    captured = {}

    class FakeQuestDB:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, _query, params):
            captured["params"] = params
            return SimpleNamespace(all=lambda: [])

    monkeypatch.setattr(
        dashboardCrud,
        "get_active_clusters",
        lambda _db: [SimpleNamespace(id=2)],
    )
    monkeypatch.setattr(dashboardCrud, "QuestDBSession", FakeQuestDB)

    dashboardCrud.get_capacity_trend(
        db=object(),
        project_id=None,
        start_time=datetime(2026, 6, 18, 8, 0),
        end_time=datetime(2026, 7, 17, 8, 0),
    )

    assert captured["params"]["start_time"] == "2026-06-18T00:00:00Z"
    assert captured["params"]["end_time"] == "2026-07-17T00:00:00Z"


def test_dashboard_service_returns_not_found_for_unknown_project(db_session):
    from services import dashboardService

    with pytest.raises(HTTPException) as error:
        dashboardService.get_summary(db_session, project_id=999)

    assert error.value.status_code == 404


def test_dashboard_router_validates_project_id(
    api_client_factory, auth_headers, db_session, monkeypatch
):
    from routers import dashboard

    from appConfig import base_config

    summary = {
        "scope": {
            "mode": "global",
            "project_id": None,
            "project_name": None,
            "start_time": "2026-06-18T00:00:00",
            "end_time": "2026-07-17T00:00:00",
            "updated_at": "2026-07-17T00:00:00",
        },
        "summary": {
            "limit_gb": 0,
            "used_gb": 0,
            "available_gb": 0,
            "use_ratio": 0,
            "storage_cluster_count": 0,
            "alert_count": 0,
        },
        "trend_meta": {
            "quota_basis": "hard",
            "rule_source": "system",
            "thresholds": {"important": 80, "serious": 90, "emergency": 95},
            "quota_limit_gb": 0,
            "ratio_indicator": "used_ratio",
        },
    }
    monkeypatch.setattr(dashboard.dashboardService, "get_summary", lambda _db, project_id=None: summary)
    monkeypatch.setattr(dashboard.dashboardService, "get_capacity_trend", lambda _db, project_id=None: [])
    monkeypatch.setattr(
        dashboard.dashboardService,
        "get_capacity_items",
        lambda _db, project_id=None, use_ratio_min=None, use_ratio_max=None: [],
    )
    monkeypatch.setattr(dashboard.dashboardService, "get_alert_levels", lambda _db, project_id=None: [])
    monkeypatch.setattr(dashboard.dashboardService, "get_top_users", lambda _db, project_id: [])
    base_config.set("super_admin_usernames", ["dashboard-admin"])
    db_session.add_all(
        [
            User(id=1, username="dashboard-user", rd_username="dashboard-admin"),
            Project(id=1, name="dashboard-project"),
        ]
    )
    db_session.commit()
    client = api_client_factory([dashboard.router], headers=auth_headers)

    assert client.get("/storage-pulse/api/dashboard/overview").status_code == 404
    assert client.get("/storage-pulse/api/dashboard/summary?project_id=0").status_code == 422
    assert client.get("/storage-pulse/api/dashboard/summary").status_code == 200
    assert client.get("/storage-pulse/api/dashboard/capacity-trend").status_code == 200
    assert client.get("/storage-pulse/api/dashboard/capacity-items").status_code == 200
    assert client.get("/storage-pulse/api/dashboard/alert-trend").status_code == 404
    assert client.get("/storage-pulse/api/dashboard/alert-levels").status_code == 200
    assert client.get("/storage-pulse/api/dashboard/top-users").status_code == 422
    assert client.get("/storage-pulse/api/dashboard/top-users?project_id=1").status_code == 200
