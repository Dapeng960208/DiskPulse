# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from models import Group, GroupTag, Project, StorageAlerts, StorageCluster, User, Volume


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

    now = datetime.now()
    db.add_all([
        StorageAlerts(
            source="diskpulse",
            alert_type="alert",
            event_type="trigger",
            related_type="Group",
            related_id=group.id,
            updated_at=now - timedelta(days=1),
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


def test_dashboard_service_builds_global_and_project_overviews(db_session, monkeypatch):
    from services import dashboardService

    project = seed_dashboard_data(db_session)
    monkeypatch.setattr(
        dashboardService.dashboardCrud,
        "get_capacity_trend",
        lambda **_kwargs: [[datetime(2026, 7, 16), 590], [datetime(2026, 7, 17), 600]],
    )

    global_overview = dashboardService.get_dashboard_overview(db_session)
    assert global_overview["scope"]["mode"] == "global"
    assert global_overview["summary"] == {
        "limit_gb": 1000.0,
        "used_gb": 600.0,
        "available_gb": 400.0,
        "use_ratio": 60.0,
        "storage_cluster_count": 1,
        "alert_count": 1,
    }
    assert [item["name"] for item in global_overview["capacity_items"]] == ["项目 A"]
    assert global_overview["capacity_trend"][-1]["used_gb"] == 600.0
    assert sum(item["count"] for item in global_overview["alert_trend"]) == 1

    project_overview = dashboardService.get_dashboard_overview(db_session, project_id=project.id)
    assert project_overview["scope"]["mode"] == "project"
    assert project_overview["scope"]["project_name"] == "项目 A"
    assert project_overview["summary"]["limit_gb"] == 300.0
    assert project_overview["summary"]["used_gb"] == 200.0
    assert project_overview["summary"]["storage_cluster_count"] == 1
    assert [item["name"] for item in project_overview["capacity_items"]] == ["项目组 A"]
    assert project_overview["summary"]["alert_count"] == 1


def test_dashboard_service_keeps_snapshots_when_questdb_is_unavailable(db_session, monkeypatch):
    from services import dashboardService

    seed_dashboard_data(db_session)

    def fail_trend(**_kwargs):
        raise RuntimeError("questdb unavailable")

    monkeypatch.setattr(dashboardService.dashboardCrud, "get_capacity_trend", fail_trend)
    overview = dashboardService.get_dashboard_overview(db_session)

    assert overview["summary"]["used_gb"] == 600.0
    assert overview["capacity_trend"] == []


def test_dashboard_service_returns_not_found_for_unknown_project(db_session):
    from services import dashboardService

    with pytest.raises(HTTPException) as error:
        dashboardService.get_dashboard_overview(db_session, project_id=999)

    assert error.value.status_code == 404


def test_dashboard_router_validates_project_id(
    api_client_factory, auth_headers, db_session, monkeypatch
):
    from routers import dashboard

    overview = {
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
        "capacity_trend": [],
        "capacity_items": [],
        "alert_trend": [],
    }
    monkeypatch.setattr(dashboard.dashboardService, "get_dashboard_overview", lambda _db, project_id=None: overview)
    db_session.add(User(id=1, username="dashboard-user"))
    db_session.commit()
    client = api_client_factory([dashboard.router], headers=auth_headers)

    assert client.get("/storage-pulse/api/dashboard/overview?project_id=0").status_code == 422
    assert client.get("/storage-pulse/api/dashboard/overview").status_code == 200
