# -*- coding: utf-8 -*-
import io
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import Base
import models
from routers import (
    aggregate,
    group,
    large_files,
    projects,
    qtrees,
    storage_alerts,
    storage_back_up_records,
    storage_cluster,
    storage_usage,
    users,
    volumes,
)
from utils.security import issue_token


NOW = "2026-06-30T10:00:00"


class CoreApiTest(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret"}, clear=False)
        self.env_patcher.start()
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        app = FastAPI()
        storage_router = APIRouter(prefix="/storage-pulse/api")
        for router in (
            users.router,
            projects.router,
            storage_cluster.router,
            aggregate.router,
            volumes.router,
            qtrees.router,
            group.router,
            storage_usage.router,
            storage_alerts.router,
            storage_back_up_records.router,
            large_files.router,
        ):
            storage_router.include_router(router)
        app.include_router(storage_router)

        @app.middleware("http")
        async def db_session_middleware(request: Request, call_next):
            request.state.db = self.SessionLocal()
            try:
                return await call_next(request)
            finally:
                request.state.db.close()

        self.client = TestClient(app)
        self.seed_core_data()

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.env_patcher.stop()

    def seed_core_data(self):
        session = self.SessionLocal()
        try:
            user = models.User(
                id=1,
                username="Alice Zhang",
                rd_username="alice",
                email="alice@example.com",
                user_type=2,
                storage_used=12.5,
            )
            project = models.Project(
                id=1,
                name="alpha",
                recipients="1 2",
                is_alert=True,
                status=1,
                limit=100,
                used=40,
                use_ratio=40,
            )
            cluster = models.StorageCluster(
                id=1,
                name="cluster-a",
                storage_type="netapp",
                storage_host="storage.local",
                storage_port=443,
                storage_user="svc",
                storage_password="secret",
                is_active=True,
                limit=1000,
                used=250,
                use_ratio=25,
            )
            aggregate_db = models.Aggregate(
                id=1,
                storage_cluster_id=1,
                name="aggr-a",
                limit=500,
                used=125,
                use_ratio=25,
                updated_at=datetime.fromisoformat(NOW),
            )
            volume = models.Volume(
                id=1,
                storage_cluster_id=1,
                name="vol-a",
                vserver="svm-a",
                aggregate="aggr-a",
                state="online",
                type="rw",
                limit=400,
                used=100,
                use_ratio=25,
                allocated=200,
                updated_at=datetime.fromisoformat(NOW),
            )
            qtree = models.Qtree(
                id=1,
                storage_cluster_id=1,
                volume_id=1,
                name="qtree-a",
                limit=300,
                used=75,
                use_ratio=25,
                style="unix",
                oplocks="enabled",
                status="normal",
                updated_at=datetime.fromisoformat(NOW),
            )
            group_db = models.Group(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                qtree_id=1,
                in_charge_user_id=1,
                name="alpha-team",
                linux_path="/data/alpha",
                back_path="/backup/alpha",
                limit=300,
                used=75,
                use_ratio=25,
                back_up_enabled=True,
                updated_at=datetime.fromisoformat(NOW),
            )
            storage_usage_db = models.StorageUsage(
                id=1,
                storage_cluster_id=1,
                user_id=1,
                group_id=1,
                linux_path="/data/alpha/alice",
                limit=100,
                used=20,
                use_ratio=20,
                file_used=10,
                file_limit=1000,
                updated_at=datetime.fromisoformat(NOW),
                access_time=datetime.fromisoformat(NOW),
                modify_time=datetime.fromisoformat(NOW),
            )
            alert = models.StorageAlerts(
                id=1,
                alert_level="warning",
                alert_type="usage",
                description="usage is high",
                threshold=80,
                avg_use_ratio=85,
                related_id=1,
                related_type="group",
                related_info={"name": "alpha-team"},
                updated_at=datetime.fromisoformat(NOW),
            )
            backup = models.StorageBackUpRecord(
                id=1,
                user_id=1,
                source_path="/data/alpha/alice",
                destination_path="/backup/alpha/alice",
                start_time=datetime.fromisoformat(NOW),
                end_time=datetime.fromisoformat(NOW),
                status=2,
            )
            pending_backup = models.StorageBackUpRecord(
                id=2,
                user_id=1,
                source_path="/data/alpha/pending",
                destination_path="/backup/alpha/pending",
                start_time=datetime.fromisoformat(NOW),
                end_time=datetime.fromisoformat(NOW),
                status=1,
            )
            large_file = models.LargeFiles(
                id=1,
                user_id=1,
                group_id=1,
                linux_path="/data/alpha/alice/big.bin",
                size=2048,
                file_type="bin",
                updated_at=datetime.fromisoformat(NOW),
                created_at=datetime.fromisoformat(NOW),
            )
            session.add_all(
                [
                    user,
                    project,
                    cluster,
                    aggregate_db,
                    volume,
                    qtree,
                    group_db,
                    storage_usage_db,
                    alert,
                    backup,
                    pending_backup,
                    large_file,
                ]
            )
            session.commit()
        finally:
            session.close()

    def test_storage_cluster_crud_and_realtime_contract(self):
        create_response = self.client.post(
            "/storage-pulse/api/storage-clusters/",
            json={
                "name": "cluster-b",
                "storage_type": "isilon",
                "storage_host": "isilon.local",
                "storage_port": 8080,
                "is_active": False,
                "limit": 800,
            },
        )
        self.assertEqual(create_response.status_code, 200)
        cluster_id = create_response.json()["id"]

        list_response = self.client.get(
            "/storage-pulse/api/storage-clusters/",
            params={"nameLike": "cluster", "is_active": "false", "page": 1, "size": 5},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["total"], 1)
        self.assertEqual(list_response.json()["content"][0]["name"], "cluster-b")

        update_response = self.client.put(
            f"/storage-pulse/api/storage-clusters/{cluster_id}",
            json={"name": "cluster-b-renamed", "is_active": True, "used": 200, "use_ratio": 25},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["name"], "cluster-b-renamed")

        with patch("routers.storage_cluster.get_storage_cluster_real_time", return_value=[[NOW, 200]]):
            realtime_response = self.client.get(f"/storage-pulse/api/storage-clusters/{cluster_id}/realtime")
        self.assertEqual(realtime_response.status_code, 200)
        self.assertEqual(realtime_response.json()["data"], [[NOW, 200]])

        delete_response = self.client.delete(f"/storage-pulse/api/storage-clusters/{cluster_id}")
        self.assertEqual(delete_response.status_code, 200)
        missing_response = self.client.get(f"/storage-pulse/api/storage-clusters/{cluster_id}")
        self.assertEqual(missing_response.status_code, 404)

    def test_project_user_and_storage_resource_lists(self):
        users_response = self.client.get(
            "/storage-pulse/api/users/",
            params={"nameLike": "alice", "load_detail": "false"},
            headers={"Authorization": f"Bearer {issue_token(1)}"},
        )
        self.assertEqual(users_response.status_code, 200)
        self.assertEqual(users_response.json()["total"], 1)
        self.assertEqual(users_response.json()["content"][0]["rd_username"], "alice")

        project_response = self.client.get("/storage-pulse/api/projects/1")
        self.assertEqual(project_response.status_code, 200)
        self.assertEqual(project_response.json()["recipient_ids"], [1, 2])

        duplicate_response = self.client.post("/storage-pulse/api/projects/", json={"name": "alpha"})
        self.assertEqual(duplicate_response.status_code, 400)

        for path, expected_name in (
            ("/storage-pulse/api/aggregates/", "aggr-a"),
            ("/storage-pulse/api/volumes/", "vol-a"),
            ("/storage-pulse/api/qtrees/", "qtree-a"),
            ("/storage-pulse/api/groups/", "alpha-team"),
        ):
            response = self.client.get(path, params={"nameLike": expected_name, "page": 1, "size": 10})
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.json()["total"], 1, path)
            self.assertEqual(response.json()["content"][0]["name"], expected_name, path)

    def test_storage_usage_create_list_update_backup_and_export_contracts(self):
        with patch("routers.storage_usage.create_user_folder_by_storage_usage_id", return_value=None):
            create_response = self.client.post(
                "/storage-pulse/api/storage-usages/",
                json={"user_id": 1, "group_id": 1},
            )
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["user_id"], 1)

        list_response = self.client.get(
            "/storage-pulse/api/storage-usages/",
            params={"nameLike": "alice", "user_id": "", "storage_cluster_id": 1},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["total"], 1)

        update_response = self.client.put(
            "/storage-pulse/api/storage-usages/1",
            json={
                "user_id": 1,
                "group_id": 1,
                "linux_path": "/data/alpha/alice",
                "limit": 120,
                "used": 30,
                "use_ratio": 25,
                "file_used": 11,
                "file_limit": 1000,
                "updated_at": NOW,
                "storage_cluster_id": 1,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["limit"], 120)

        with patch("routers.storage_usage.back_up_user_storage_usage_by_storage_usage_id", return_value=None):
            backup_response = self.client.post(
                "/storage-pulse/api/storage-usages/1/back-up",
                json={"closed": True},
            )
        self.assertEqual(backup_response.status_code, 200)

        with patch("crud.storageUsageCrud.export_storage_usage_to_pdf", return_value=io.BytesIO(b"%PDF")):
            pdf_response = self.client.get("/storage-pulse/api/storage-usages/export/", params={"export_type": "pdf"})
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response.headers["content-type"], "application/pdf")

        with patch("crud.storageUsageCrud.export_storage_usage_to_excel", return_value=io.BytesIO(b"xlsx")):
            excel_response = self.client.get(
                "/storage-pulse/api/storage-usages/export/",
                params={"export_type": "excel"},
            )
        self.assertEqual(excel_response.status_code, 200)
        self.assertEqual(
            excel_response.headers["content-type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_alert_backup_and_large_file_interfaces(self):
        alert_response = self.client.get(
            "/storage-pulse/api/storage-alerts/",
            params={"alert_type": "usage", "related_type": "group", "related_id": 1},
        )
        self.assertEqual(alert_response.status_code, 200)
        self.assertEqual(alert_response.json()["total"], 1)

        backup_list_response = self.client.get(
            "/storage-pulse/api/storage-back-up-records/",
            params={"user_id": ""},
        )
        self.assertEqual(backup_list_response.status_code, 200)
        self.assertEqual(backup_list_response.json()["total"], 2)

        blocked_delete_response = self.client.delete("/storage-pulse/api/storage-back-up-records/2")
        self.assertEqual(blocked_delete_response.status_code, 400)

        with patch("routers.storage_back_up_records.delete_storage_back_up_record_by_storage_usage_id", return_value=None):
            delete_response = self.client.delete("/storage-pulse/api/storage-back-up-records/1")
        self.assertEqual(delete_response.status_code, 200)

        large_files_response = self.client.get(
            "/storage-pulse/api/large-files/",
            params={"nameLike": "", "user_id": 1, "group_id": 1},
        )
        self.assertEqual(large_files_response.status_code, 200)
        self.assertEqual(large_files_response.json()["total"], 1)

        with patch("crud.largeFilesCrud.export_large_files", return_value=io.BytesIO(b"xlsx")):
            export_response = self.client.get("/storage-pulse/api/large-files/export/")
        self.assertEqual(export_response.status_code, 200)
        self.assertEqual(
            export_response.headers["content-type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    unittest.main()
