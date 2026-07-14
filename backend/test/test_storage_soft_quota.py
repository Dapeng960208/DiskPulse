# -*- coding: utf-8 -*-
from datetime import datetime

import models
from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from crud.storageUsageCrud import get_export_data


NOW = datetime(2026, 6, 30, 10, 0, 0)
GB = 1024**3


class DummyLogger:
    def info(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass


class FakeNetAppClient:
    def get_quota_reports(self):
        return [
            {
                "type": "user",
                "volume": {"name": "vol-a"},
                "qtree": {"name": "qtree-a"},
                "users": [{"name": "alice", "id": 1001}],
                "space": {
                    "used": {"total": 20 * GB},
                    "hard_limit": 100 * GB,
                    "soft_limit": 80 * GB,
                },
                "files": {"used": {"total": 10}, "hard_limit": 1000},
            },
            {
                "type": "tree",
                "volume": {"name": "vol-a"},
                "qtree": {"name": "qtree-a"},
                "space": {
                    "used": 50 * GB,
                    "hard_limit": 200 * GB,
                    "soft_limit": 150 * GB,
                },
            },
        ]


class FakeIsilonClient:
    def get_quotas(self):
        return [
            {
                "type": "default-user",
                "path": "/ifs/team",
                "thresholds": {"hard": 100 * GB, "soft": 80 * GB},
                "usage": {"logical": 0},
            },
            {
                "type": "user",
                "path": "/ifs/team",
                "linked": True,
                "persona": {"name": "alice"},
                "thresholds": {"hard": 0, "soft": 0},
                "usage": {"logical": 20 * GB},
            },
            {
                "type": "directory",
                "path": "/ifs/team",
                "linked": False,
                "thresholds": {"hard": 500 * GB, "soft": 400 * GB},
                "usage": {"logical": 125 * GB},
            },
        ]


def seed_quota_data(db_session, storage_type):
    cluster = models.StorageCluster(
        id=1,
        name="cluster-a",
        storage_type=storage_type,
        storage_host="storage.local",
        storage_port=443,
        is_active=True,
    )
    project = models.Project(id=1, name="alpha", limit=100, used=20, use_ratio=20)
    group_tag = models.GroupTag(id=1, name="production")
    user = models.User(id=1, rd_username="alice", uid=1001, updated_at=NOW)
    volume = models.Volume(
        id=1,
        storage_cluster_id=1,
        name="vol-a" if storage_type == "netapp" else "/ifs/team",
        vserver="svm-a",
        aggregate="aggr-a",
        state="online",
        type="rw",
        limit=200,
        used=50,
        use_ratio=25,
        soft_limit=150,
        soft_use_ratio=33.33,
        updated_at=NOW,
    )
    qtree = models.Qtree(
        id=1,
        storage_cluster_id=1,
        volume_id=1,
        name="qtree-a" if storage_type == "netapp" else "null",
        limit=200,
        used=50,
        use_ratio=25,
        soft_limit=150,
        soft_use_ratio=33.33,
        style="unix",
        oplocks="enabled",
        status="normal",
        updated_at=NOW,
    )
    group = models.Group(
        id=1,
        project_id=1,
        storage_cluster_id=1,
        group_tag_id=1,
        qtree_id=1,
        name="alpha-team",
        linux_path="/data/alpha",
        limit=100,
        used=20,
        use_ratio=20,
        soft_limit=80,
        soft_use_ratio=25,
        updated_at=NOW,
    )
    db_session.add_all([cluster, project, group_tag, user, volume, qtree, group])
    db_session.commit()


def build_monitor(db_session, storage_type):
    monitor = StoragePulseMonitor(db_session, DummyLogger(), storage_cluster_id=1)
    monitor.storage_type = storage_type
    return monitor


def test_netapp_user_and_tree_quotas_capture_soft_limits(db_session):
    seed_quota_data(db_session, "netapp")
    monitor = build_monitor(db_session, "netapp")
    monitor.client = FakeNetAppClient()
    qtree = db_session.query(models.Qtree).filter_by(id=1).one()
    group = db_session.query(models.Group).filter_by(id=1).one()

    quotas = monitor._fetch_user_quotas_netapp(
        {("vol-a", "qtree-a"): qtree},
        {qtree.id: [group]},
        {"alice": 1},
        {"1001": db_session.query(models.User).filter_by(id=1).one()},
        {},
    )

    assert len(quotas) == 1
    assert quotas[0].limit == 100
    assert quotas[0].soft_limit == 80
    assert quotas[0].use_ratio == 20
    assert quotas[0].soft_use_ratio == 25
    assert qtree.soft_limit == 150
    assert qtree.soft_use_ratio == 33.33


def test_isilon_linked_user_and_directory_quotas_capture_soft_limits(db_session):
    seed_quota_data(db_session, "netapp")
    db_session.query(models.StorageCluster).filter_by(id=1).update({"storage_type": "isilon"})
    db_session.query(models.Volume).filter_by(id=1).update({"name": "/ifs/team"})
    db_session.query(models.Group).filter_by(id=1).update(
        {"volume_id": 1, "qtree_id": None}
    )
    db_session.commit()

    monitor = build_monitor(db_session, "isilon")
    monitor.client = FakeIsilonClient()
    volume = db_session.query(models.Volume).filter_by(id=1).one()
    group = db_session.query(models.Group).filter_by(id=1).one()

    volumes, quotas = monitor._fetch_user_quotas_isilon(
        {"/ifs/team": volume},
        {volume.id: [group]},
        {"alice": 1},
        {"1001": db_session.query(models.User).filter_by(id=1).one()},
        {},
    )

    assert len(quotas) == 1
    assert quotas[0].limit == 100
    assert quotas[0].soft_limit == 80
    assert quotas[0].soft_use_ratio == 25
    assert len(volumes) == 1
    assert volumes[0].limit == 500
    assert volumes[0].soft_limit == 400
    assert volumes[0].soft_use_ratio == 31.25


def test_storage_usage_export_includes_soft_quota_columns(db_session):
    seed_quota_data(db_session, "netapp")
    db_session.add(
        models.StorageUsage(
            id=1,
            storage_cluster_id=1,
            user_id=1,
            group_id=1,
            linux_path="/data/alpha/alice",
            limit=100,
            used=20,
            use_ratio=20,
            soft_limit=80,
            soft_use_ratio=25,
            file_used=10,
            file_limit=1000,
            updated_at=NOW,
        )
    )
    db_session.commit()

    df = get_export_data(db_session)

    assert "软限额" in df.columns
    assert "软使用率" in df.columns
    assert df.iloc[0]["软限额"] == 80
    assert df.iloc[0]["软使用率"] == 25
