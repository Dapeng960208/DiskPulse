# -*- coding: utf-8 -*-
import sys
import unittest
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import Base
import models
from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from crud.storageUsageCrud import get_export_data


NOW = datetime(2026, 6, 30, 10, 0, 0)
GB = 1024 ** 3


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


class StorageSoftQuotaTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        self.seed_data("netapp")

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def seed_data(self, storage_type):
        cluster = models.StorageCluster(
            id=1,
            name="cluster-a",
            storage_type=storage_type,
            storage_host="storage.local",
            storage_port=443,
            is_active=True,
        )
        project = models.Project(id=1, name="alpha", limit=100, used=20, use_ratio=20)
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
        self.db.add_all([cluster, project, user, volume, qtree, group])
        self.db.commit()

    def build_monitor(self, storage_type):
        monitor = StoragePulseMonitor(self.db, DummyLogger(), storage_cluster_id=1)
        monitor.storage_type = storage_type
        return monitor

    def test_netapp_user_and_tree_quotas_capture_soft_limits(self):
        monitor = self.build_monitor("netapp")
        monitor.client = FakeNetAppClient()
        qtree = self.db.query(models.Qtree).filter_by(id=1).one()
        group = self.db.query(models.Group).filter_by(id=1).one()

        quotas = monitor._fetch_user_quotas_netapp(
            {("vol-a", "qtree-a"): qtree},
            {qtree.id: [group]},
            {"alice": 1},
            {"1001": self.db.query(models.User).filter_by(id=1).one()},
            {},
        )

        self.assertEqual(len(quotas), 1)
        self.assertEqual(quotas[0].limit, 100)
        self.assertEqual(quotas[0].soft_limit, 80)
        self.assertEqual(quotas[0].use_ratio, 20)
        self.assertEqual(quotas[0].soft_use_ratio, 25)
        self.assertEqual(qtree.soft_limit, 150)
        self.assertEqual(qtree.soft_use_ratio, 33.33)

    def test_isilon_linked_user_and_directory_quotas_capture_soft_limits(self):
        self.db.query(models.StorageCluster).filter_by(id=1).update({"storage_type": "isilon"})
        self.db.query(models.Volume).filter_by(id=1).update({"name": "/ifs/team"})
        self.db.query(models.Qtree).filter_by(id=1).update({"name": "null"})
        self.db.commit()

        monitor = self.build_monitor("isilon")
        monitor.client = FakeIsilonClient()
        qtree = self.db.query(models.Qtree).filter_by(id=1).one()
        group = self.db.query(models.Group).filter_by(id=1).one()

        volumes, quotas = monitor._fetch_user_quotas_isilon(
            {("/ifs/team", "null"): qtree},
            {qtree.id: [group]},
            {"alice": 1},
            {"1001": self.db.query(models.User).filter_by(id=1).one()},
            {},
        )

        self.assertEqual(len(quotas), 1)
        self.assertEqual(quotas[0].limit, 100)
        self.assertEqual(quotas[0].soft_limit, 80)
        self.assertEqual(quotas[0].soft_use_ratio, 25)
        self.assertEqual(len(volumes), 1)
        self.assertEqual(volumes[0].limit, 500)
        self.assertEqual(volumes[0].soft_limit, 400)
        self.assertEqual(volumes[0].soft_use_ratio, 31.25)

    def test_storage_usage_export_includes_soft_quota_columns(self):
        self.db.add(
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
        self.db.commit()

        df = get_export_data(self.db)

        self.assertIn("软限额", df.columns)
        self.assertIn("软使用率", df.columns)
        self.assertEqual(df.iloc[0]["软限额"], 80)
        self.assertEqual(df.iloc[0]["软使用率"], 25)


if __name__ == "__main__":
    unittest.main()
