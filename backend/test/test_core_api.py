# -*- coding: utf-8 -*-
import io
from datetime import datetime
from unittest.mock import ANY, patch

import pytest

from appConfig import base_config
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
from middleware.correlation import CorrelationIdMiddleware


NOW = "2026-06-30T10:00:00"


class TestCoreApi:
    @pytest.fixture(autouse=True)
    def setup(self, api_client_factory, session_factory):
        base_config.set("jwt.secret_key", "test-secret")
        base_config.set("super_admin_usernames", ["alice"])
        self.SessionLocal = session_factory
        self.client = api_client_factory(
            [
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
            ],
            authenticated=True,
            headers={"Authorization": f"Bearer {issue_token(1)}"},
        )
        self.seed_core_data()

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
                soft_limit=80,
                soft_use_ratio=50,
            )
            high_utilization_project = models.Project(
                id=2,
                name="beta",
                recipients="1",
                is_alert=True,
                status=1,
                limit=100,
                used=75,
                use_ratio=75,
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
            high_utilization_cluster = models.StorageCluster(
                id=2,
                name="cluster-b",
                storage_type="netapp",
                storage_host="storage-b.local",
                storage_port=443,
                is_active=True,
                limit=1000,
                used=750,
                use_ratio=75,
            )
            group_tag = models.GroupTag(id=1, name="production")
            aggregate_db = models.Aggregate(
                id=1,
                storage_cluster_id=1,
                name="aggr-a",
                limit=500,
                used=125,
                use_ratio=25,
                updated_at=datetime.fromisoformat(NOW),
            )
            high_utilization_aggregate = models.Aggregate(
                id=2,
                storage_cluster_id=1,
                name="aggr-b",
                limit=500,
                used=375,
                use_ratio=75,
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
                soft_limit=320,
                soft_use_ratio=31.25,
                allocated=200,
                updated_at=datetime.fromisoformat(NOW),
            )
            high_utilization_volume = models.Volume(
                id=2,
                storage_cluster_id=1,
                name="vol-b",
                vserver="svm-b",
                aggregate="aggr-b",
                state="online",
                type="rw",
                limit=400,
                used=300,
                use_ratio=75,
                soft_limit=320,
                soft_use_ratio=93.75,
                allocated=300,
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
                soft_limit=240,
                soft_use_ratio=31.25,
                style="unix",
                oplocks="enabled",
                status="normal",
                updated_at=datetime.fromisoformat(NOW),
            )
            high_utilization_qtree = models.Qtree(
                id=2,
                storage_cluster_id=1,
                volume_id=2,
                name="qtree-b",
                limit=300,
                used=225,
                use_ratio=75,
                soft_limit=240,
                soft_use_ratio=93.75,
                style="unix",
                oplocks="enabled",
                status="normal",
                updated_at=datetime.fromisoformat(NOW),
            )
            group_db = models.Group(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                qtree_id=1,
                in_charge_user_id=1,
                name="alpha-team",
                linux_path="/data/alpha",
                back_path="/backup/alpha",
                limit=300,
                used=75,
                use_ratio=25,
                soft_limit=240,
                soft_use_ratio=31.25,
                back_up_enabled=True,
                updated_at=datetime.fromisoformat(NOW),
            )
            high_utilization_group = models.Group(
                id=2,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                qtree_id=2,
                in_charge_user_id=1,
                name="beta-team",
                linux_path="/data/beta",
                back_path="/backup/beta",
                limit=300,
                used=225,
                use_ratio=75,
                soft_limit=240,
                soft_use_ratio=93.75,
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
                soft_limit=80,
                soft_use_ratio=25,
                file_used=10,
                file_limit=1000,
                updated_at=datetime.fromisoformat(NOW),
                access_time=datetime.fromisoformat(NOW),
                modify_time=datetime.fromisoformat(NOW),
            )
            high_utilization_storage_usage = models.StorageUsage(
                id=2,
                storage_cluster_id=1,
                user_id=1,
                group_id=2,
                linux_path="/data/beta/alice",
                limit=100,
                used=75,
                use_ratio=75,
                soft_limit=80,
                soft_use_ratio=93.75,
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
                    high_utilization_project,
                    cluster,
                    high_utilization_cluster,
                    group_tag,
                    aggregate_db,
                    high_utilization_aggregate,
                    volume,
                    high_utilization_volume,
                    qtree,
                    high_utilization_qtree,
                    group_db,
                    high_utilization_group,
                    storage_usage_db,
                    high_utilization_storage_usage,
                    alert,
                    backup,
                    pending_backup,
                    large_file,
                ]
            )
            session.commit()
        finally:
            session.close()

    def bind_seeded_group_to_volume(self, storage_type="netapp"):
        session = self.SessionLocal()
        try:
            session.get(models.StorageCluster, 1).storage_type = storage_type
            group_db = session.get(models.Group, 1)
            group_db.volume_id = 1
            group_db.qtree_id = None
            session.commit()
        finally:
            session.close()

    def test_volume_bound_group_realtime_serializes_storage_target(self):
        self.bind_seeded_group_to_volume()

        with patch("crud.groupCrud.get_real_time_data_by_id", return_value=[[NOW, 75]]):
            response = self.client.get("/storage-pulse/api/groups/1/realtime")

        assert response.status_code == 200
        assert response.json()["info"]["storage_target"] == {
            "type": "volume",
            "id": 1,
            "name": "vol-a",
        }

    def test_storage_resource_responses_include_explicit_capacity_units(self):
        resources = [
            ("/storage-pulse/api/aggregates/", {"page": 1, "size": 20}),
            ("/storage-pulse/api/volumes/", {"page": 1, "size": 20}),
            ("/storage-pulse/api/qtrees/", {"page": 1, "size": 20}),
            ("/storage-pulse/api/groups/", {"page": 1, "size": 20}),
            ("/storage-pulse/api/storage-usages/", {"page": 1, "size": 20}),
            ("/storage-pulse/api/projects/", {"page": 1, "size": 20}),
            ("/storage-pulse/api/storage-clusters/", {"page": 1, "size": 20}),
        ]

        for path, params in resources:
            response = self.client.get(path, params=params)

            assert response.status_code == 200
            resource = response.json()["content"][0]
            assert resource["capacity"]["limit"]["unit"] == "GB"
            assert resource["capacity"]["used"]["unit"] == "GB"

    def test_storage_resource_lists_filter_by_inclusive_utilization_range(self):
        resources = [
            ("/storage-pulse/api/storage-clusters/", 2),
            ("/storage-pulse/api/aggregates/", 2),
            ("/storage-pulse/api/volumes/", 2),
            ("/storage-pulse/api/qtrees/", 2),
            ("/storage-pulse/api/groups/", 2),
            ("/storage-pulse/api/storage-usages/", 2),
            ("/storage-pulse/api/projects/", 2),
        ]

        for path, expected_id in resources:
            response = self.client.get(
                path,
                params={"page": 1, "size": 20, "use_ratio_min": 70, "use_ratio_max": 80},
            )

            assert response.status_code == 200
            assert response.json()["total"] == 1
            assert [item["id"] for item in response.json()["content"]] == [expected_id]

    def test_storage_resource_lists_reject_reversed_utilization_range(self):
        paths = [
            "/storage-pulse/api/storage-clusters/",
            "/storage-pulse/api/aggregates/",
            "/storage-pulse/api/volumes/",
            "/storage-pulse/api/qtrees/",
            "/storage-pulse/api/groups/",
            "/storage-pulse/api/storage-usages/",
            "/storage-pulse/api/projects/",
        ]

        for path in paths:
            response = self.client.get(
                path,
                params={"page": 1, "size": 20, "use_ratio_min": 80, "use_ratio_max": 70},
            )

            assert response.status_code == 422

    def test_volume_bound_group_image_resolves_owning_volume(self, tmp_path):
        self.bind_seeded_group_to_volume()
        image_path = tmp_path / "group.png"
        session = self.SessionLocal()
        try:
            with (
                patch(
                    "routers.group.groupCrud.get_group_real_time_data_by_id",
                    return_value=[[NOW, 75]],
                ),
                patch(
                    "routers.group.plot_real_time_line",
                    return_value=str(image_path),
                ),
            ):
                current_user = session.get(models.User, 1)
                response = group.get_storage_usage_image_by_id(
                    1,
                    role="cad",
                    current_user=current_user,
                    db=session,
                )
        finally:
            session.close()

        assert response.path == str(image_path)

    def test_volume_bound_storage_usage_image_resolves_owning_volume(self, tmp_path):
        self.bind_seeded_group_to_volume()
        image_path = tmp_path / "usage.png"
        session = self.SessionLocal()
        try:
            with (
                patch(
                    "routers.storage_usage.storageUsageCrud.get_storage_usages_real_time_data_by_id",
                    return_value=[[NOW, 20]],
                ),
                patch(
                    "routers.storage_usage.plot_real_time_line",
                    return_value=str(image_path),
                ),
            ):
                current_user = session.get(models.User, 1)
                response = storage_usage.get_storage_usage_image_by_id(
                    1,
                    role="cad",
                    current_user=current_user,
                    db=session,
                )
        finally:
            session.close()

        assert response.path == str(image_path)

    def test_deprecated_storage_expansion_route_is_removed(self):
        response = self.client.post(
            "/storage-pulse/api/storage-usages/expand",
            json={"expand_id": 1, "expand_type": "Group", "size": 1},
        )

        assert response.status_code == 405

    def test_storage_cluster_crud_and_realtime_contract(self):
        with patch("routers.storage_cluster._schedule_storage_collection") as schedule_collection:
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
            schedule_collection.assert_not_called()
        assert create_response.status_code == 200
        cluster_id = create_response.json()["id"]

        list_response = self.client.get(
            "/storage-pulse/api/storage-clusters/",
            params={"nameLike": "cluster", "is_active": "false", "page": 1, "size": 5},
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1
        assert list_response.json()["content"][0]["name"] == "cluster-b"

        with patch("routers.storage_cluster._schedule_storage_collection") as schedule_collection:
            update_response = self.client.put(
                f"/storage-pulse/api/storage-clusters/{cluster_id}",
                json={"name": "cluster-b-renamed", "is_active": True, "used": 200, "use_ratio": 25},
            )
            schedule_collection.assert_called_once_with(cluster_id, audit_context=ANY)
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "cluster-b-renamed"

        with patch("routers.storage_cluster.get_storage_cluster_real_time", return_value=[[NOW, 200]]):
            realtime_response = self.client.get(f"/storage-pulse/api/storage-clusters/{cluster_id}/realtime")
        assert realtime_response.status_code == 200
        assert realtime_response.json()["data"] == [[NOW, 200]]

        delete_response = self.client.delete(f"/storage-pulse/api/storage-clusters/{cluster_id}")
        assert delete_response.status_code == 200
        missing_response = self.client.get(f"/storage-pulse/api/storage-clusters/{cluster_id}")
        assert missing_response.status_code == 404

    def test_storage_cluster_transport_fields_create_update_and_list(self):
        with patch("routers.storage_cluster._schedule_storage_collection"):
            create_response = self.client.post(
                "/storage-pulse/api/storage-clusters/",
                json={
                    "name": "transport-cluster",
                    "storage_type": "isilon",
                    "storage_host": "storage.local",
                    "storage_port": 8080,
                    "protocol": "http",
                    "tls_verify": True,
                    "is_active": False,
                },
            )

        assert create_response.status_code == 200
        assert create_response.json()["protocol"] == "http"
        assert create_response.json()["tls_verify"] is False
        cluster_id = create_response.json()["id"]

        with patch("routers.storage_cluster._schedule_storage_collection"):
            update_response = self.client.put(
                f"/storage-pulse/api/storage-clusters/{cluster_id}",
                json={"protocol": "https", "tls_verify": True},
            )

        assert update_response.status_code == 200
        assert update_response.json()["protocol"] == "https"
        assert update_response.json()["tls_verify"] is True

        with patch("routers.storage_cluster._schedule_storage_collection"):
            update_response = self.client.put(
                f"/storage-pulse/api/storage-clusters/{cluster_id}",
                json={"protocol": "http", "tls_verify": True},
            )

        assert update_response.status_code == 200
        assert update_response.json()["protocol"] == "http"
        assert update_response.json()["tls_verify"] is False

        list_response = self.client.get(
            "/storage-pulse/api/storage-clusters/",
            params={"nameLike": "transport-cluster"},
        )
        assert list_response.status_code == 200
        assert list_response.json()["content"][0]["protocol"] == "http"
        assert list_response.json()["content"][0]["tls_verify"] is False

        with patch("routers.storage_cluster._schedule_storage_collection"):
            partial_update_response = self.client.put(
                f"/storage-pulse/api/storage-clusters/{cluster_id}",
                json={"tls_verify": True},
            )

        assert partial_update_response.status_code == 200
        assert partial_update_response.json()["tls_verify"] is False
        with self.SessionLocal() as session:
            assert session.get(models.StorageCluster, cluster_id).tls_verify is False

    def test_storage_cluster_transport_defaults_are_secure(self):
        with patch("routers.storage_cluster._schedule_storage_collection"):
            response = self.client.post(
                "/storage-pulse/api/storage-clusters/",
                json={
                    "name": "default-transport-cluster",
                    "storage_type": "netapp",
                    "is_active": False,
                },
            )

        assert response.status_code == 200
        assert response.json()["protocol"] == "https"
        assert response.json()["tls_verify"] is True

    @pytest.mark.parametrize(
        ("method", "path", "payload"),
        [
            (
                "post",
                "/storage-pulse/api/storage-clusters/",
                {
                    "name": "invalid-protocol-cluster",
                    "storage_type": "netapp",
                    "protocol": "ftp",
                    "is_active": False,
                },
            ),
            (
                "put",
                "/storage-pulse/api/storage-clusters/1",
                {"protocol": "ftp"},
            ),
        ],
    )
    def test_storage_cluster_rejects_invalid_protocol(self, method, path, payload):
        with patch("routers.storage_cluster._schedule_storage_collection"):
            response = getattr(self.client, method)(path, json=payload)

        assert response.status_code == 422

    @pytest.mark.parametrize("payload", [{"protocol": None}, {"tls_verify": None}])
    def test_storage_cluster_rejects_null_transport_fields(self, payload):
        with patch("routers.storage_cluster._schedule_storage_collection"):
            response = self.client.put(
                "/storage-pulse/api/storage-clusters/1",
                json=payload,
            )

        assert response.status_code == 422

    @pytest.mark.parametrize("storage_type", ["netapp", "isilon"])
    def test_active_storage_cluster_create_schedules_collection(self, storage_type):
        with patch("routers.storage_cluster._schedule_storage_collection") as schedule_collection:
            response = self.client.post(
                "/storage-pulse/api/storage-clusters/",
                json={
                    "name": f"{storage_type}-cluster",
                    "storage_type": storage_type,
                    "storage_host": f"{storage_type}.local",
                    "storage_port": 443 if storage_type == "netapp" else 8080,
                    "is_active": True,
                },
            )

        assert response.status_code == 200
        schedule_collection.assert_called_once_with(response.json()["id"], audit_context=ANY)

    def test_active_storage_cluster_create_propagates_http_correlation_to_collection(self):
        request_id = "2a48f1f1-78ea-49c1-b3bc-2712720e4c86"
        trace_id = "1e8de2cf-9bdf-4242-a40c-794ce52694ec"
        self.client.app.add_middleware(CorrelationIdMiddleware)

        with patch("routers.storage_cluster._schedule_storage_collection") as schedule_collection:
            response = self.client.post(
                "/storage-pulse/api/storage-clusters/",
                json={
                    "name": "correlated-cluster",
                    "storage_type": "netapp",
                    "storage_host": "correlated.local",
                    "storage_port": 443,
                    "is_active": True,
                },
                headers={"X-Request-ID": request_id, "X-Trace-ID": trace_id},
            )

        assert response.status_code == 200
        schedule_collection.assert_called_once_with(response.json()["id"], audit_context=ANY)
        context = schedule_collection.call_args.kwargs["audit_context"]
        assert context.request_id == request_id
        assert context.trace_id == trace_id
        assert context.actor_user_id == 1

    def test_project_user_and_storage_resource_lists(self):
        users_response = self.client.get(
            "/storage-pulse/api/users/",
            params={"nameLike": "alice", "load_detail": "false"},
            headers={"Authorization": f"Bearer {issue_token(1)}"},
        )
        assert users_response.status_code == 200
        assert users_response.json()["total"] == 1
        assert users_response.json()["content"][0]["rd_username"] == "alice"

        project_response = self.client.get("/storage-pulse/api/projects/1")
        assert project_response.status_code == 200
        assert project_response.json()["recipient_ids"] == [1, 2]

        duplicate_response = self.client.post("/storage-pulse/api/projects/", json={"name": "alpha"})
        assert duplicate_response.status_code == 400

        for path, expected_name in (
            ("/storage-pulse/api/aggregates/", "aggr-a"),
            ("/storage-pulse/api/volumes/", "vol-a"),
            ("/storage-pulse/api/qtrees/", "qtree-a"),
            ("/storage-pulse/api/groups/", "alpha-team"),
        ):
            response = self.client.get(path, params={"nameLike": expected_name, "page": 1, "size": 10})
            assert response.status_code == 200, path
            assert response.json()["total"] == 1, path
            assert response.json()["content"][0]["name"] == expected_name, path

        volume_response = self.client.get(
            "/storage-pulse/api/volumes/",
            params={"prop": "soft_limit", "order": "descending", "page": 1, "size": 10},
        )
        assert volume_response.status_code == 200
        assert volume_response.json()["content"][0]["soft_limit"] == 320

        qtree_response = self.client.get(
            "/storage-pulse/api/qtrees/",
            params={"prop": "soft_use_ratio", "order": "descending", "page": 1, "size": 10},
        )
        assert qtree_response.status_code == 200
        assert qtree_response.json()["content"][0]["soft_use_ratio"] == 31.25

        group_response = self.client.get(
            "/storage-pulse/api/groups/",
            params={"prop": "soft_limit", "order": "descending", "page": 1, "size": 10},
        )
        assert group_response.status_code == 200
        assert group_response.json()["content"][0]["soft_limit"] == 240

    def test_aggregate_storage_tree_filters_by_cluster(self):
        session = self.SessionLocal()
        try:
            session.add_all(
                [
                    models.StorageCluster(
                        id=2,
                        name="cluster-b",
                        storage_type="netapp",
                        storage_host="storage-b.local",
                        storage_port=443,
                        storage_user="svc",
                        storage_password="secret",
                        is_active=True,
                    ),
                    models.Volume(
                        id=2,
                        storage_cluster_id=2,
                        name="vol-b",
                        vserver="svm-b",
                        aggregate="aggr-b",
                        state="online",
                        type="rw",
                        limit=200,
                        used=50,
                        use_ratio=25,
                        updated_at=datetime.fromisoformat(NOW),
                    ),
                ]
            )
            session.commit()
        finally:
            session.close()

        response = self.client.get(
            "/storage-pulse/api/aggregates/storage-trees/",
            params={"storage_cluster_id": 2},
        )
        assert response.status_code == 200
        assert [item["name"] for item in response.json()["data"]] == ["vol-b"]

        invalid_response = self.client.get(
            "/storage-pulse/api/aggregates/storage-trees/",
            params={"storage_cluster_id": 0},
        )
        assert invalid_response.status_code == 422

    def test_legacy_group_payload_is_rejected(self):
        response = self.client.post(
            "/storage-pulse/api/groups/",
            json={
                "name": "legacy-group",
                "project_id": 1,
                "storage_cluster_id": 1,
                "qtree_id": 1,
            },
        )

        assert response.status_code == 422

    def test_storage_usage_create_list_update_backup_and_export_contracts(self):
        with patch("routers.storage_usage.create_user_folder_by_storage_usage_id", return_value=None):
            create_response = self.client.post(
                "/storage-pulse/api/storage-usages/",
                json={"user_id": 1, "group_id": 1},
            )
        assert create_response.status_code == 200
        assert create_response.json()["user_id"] == 1

        list_response = self.client.get(
            "/storage-pulse/api/storage-usages/",
            params={"nameLike": "alice", "user_id": "", "storage_cluster_id": 1},
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

        update_response = self.client.put(
            "/storage-pulse/api/storage-usages/1",
            json={
                "user_id": 1,
                "group_id": 1,
                "linux_path": "/data/alpha/alice",
                "limit": 120,
                "used": 30,
                "use_ratio": 25,
                "soft_limit": 90,
                "soft_use_ratio": 33.33,
                "file_used": 11,
                "file_limit": 1000,
                "updated_at": NOW,
                "storage_cluster_id": 1,
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["limit"] == 120
        assert update_response.json()["soft_limit"] == 90

        soft_sort_response = self.client.get(
            "/storage-pulse/api/storage-usages/",
            params={"prop": "soft_use_ratio", "order": "descending", "page": 1, "size": 10},
        )
        assert soft_sort_response.status_code == 200
        assert soft_sort_response.json()["content"][0]["soft_use_ratio"] == 33.33

        with patch("routers.storage_usage.back_up_user_storage_usage_by_storage_usage_id", return_value=None):
            backup_response = self.client.post(
                "/storage-pulse/api/storage-usages/1/back-up",
                json={"closed": True},
            )
        assert backup_response.status_code == 200

        with patch("crud.storageUsageCrud.export_storage_usage_to_pdf", return_value=io.BytesIO(b"%PDF")):
            pdf_response = self.client.get("/storage-pulse/api/storage-usages/export/", params={"export_type": "pdf"})
        assert pdf_response.status_code == 200
        assert pdf_response.headers["content-type"] == "application/pdf"

        with patch("crud.storageUsageCrud.export_storage_usage_to_excel", return_value=io.BytesIO(b"xlsx")):
            excel_response = self.client.get(
                "/storage-pulse/api/storage-usages/export/",
                params={"export_type": "excel"},
            )
        assert excel_response.status_code == 200
        assert (
            excel_response.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def test_alert_backup_and_large_file_interfaces(self):
        alert_response = self.client.get(
            "/storage-pulse/api/storage-alerts/",
            params={"alert_type": "usage", "related_type": "group", "related_id": 1},
        )
        assert alert_response.status_code == 200
        assert alert_response.json()["total"] == 1

        backup_list_response = self.client.get(
            "/storage-pulse/api/storage-back-up-records/",
            params={"user_id": ""},
        )
        assert backup_list_response.status_code == 200
        assert backup_list_response.json()["total"] == 2

        blocked_delete_response = self.client.delete("/storage-pulse/api/storage-back-up-records/2")
        assert blocked_delete_response.status_code == 400

        with patch("routers.storage_back_up_records.delete_storage_back_up_record_by_storage_usage_id", return_value=None):
            delete_response = self.client.delete("/storage-pulse/api/storage-back-up-records/1")
        assert delete_response.status_code == 200

        large_files_response = self.client.get(
            "/storage-pulse/api/large-files/",
            params={"nameLike": "", "user_id": 1, "group_id": 1},
        )
        assert large_files_response.status_code == 200
        assert large_files_response.json()["total"] == 1

        with patch("crud.largeFilesCrud.export_large_files", return_value=io.BytesIO(b"xlsx")):
            export_response = self.client.get("/storage-pulse/api/large-files/export/")
        assert export_response.status_code == 200
        assert (
            export_response.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
