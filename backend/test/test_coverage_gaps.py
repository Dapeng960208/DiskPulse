# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import models
from crud import (
    configCrud,
    groupCrud,
    largeFilesCrud,
    projectsCrud,
    storageAlertCrud,
    storageBackUpRecordCrud,
    storageClusterCrud,
    storageUsageCrud,
)
from schemas.configSchemas import StorageConf
from schemas.storageClusterSchema import StorageClusterUpdate
from schemas.storageUsageSchema import StorageUsageCreate, StorageUsageUpdate


NOW = datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc)


def seed_storage_graph(db):
    user = models.User(id=1, rd_username="alice", username="Alice")
    second_user = models.User(id=2, rd_username="bob", username="Bob")
    project = models.Project(id=1, name="alpha", limit=100, used=20, use_ratio=20)
    cluster = models.StorageCluster(
        id=1,
        name="cluster-a",
        storage_type="netapp",
        storage_host="storage-a",
    )
    unused_cluster = models.StorageCluster(
        id=2,
        name="cluster-unused",
        storage_type="netapp",
        storage_host="storage-b",
    )
    tag = models.GroupTag(id=1, name="production")
    volume = models.Volume(
        id=1,
        storage_cluster_id=1,
        name="vol-a",
        vserver="svm-a",
        aggregate="aggr-a",
        state="online",
        type="rw",
        limit=100,
        used=20,
        use_ratio=20,
        updated_at=NOW,
    )
    qtree = models.Qtree(
        id=1,
        storage_cluster_id=1,
        volume_id=1,
        name="qtree-a",
        limit=80,
        used=10,
        use_ratio=12.5,
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
        limit=80,
        used=10,
        use_ratio=12.5,
        enable_monitoring=True,
    )
    usage = models.StorageUsage(
        id=1,
        storage_cluster_id=1,
        user_id=1,
        group_id=1,
        linux_path="/data/alpha/alice",
        limit=40,
        used=10,
        use_ratio=25,
        soft_limit=30,
        soft_use_ratio=33.3,
        updated_at=NOW,
        access_time=NOW,
        modify_time=NOW,
    )
    alerts = [
        models.StorageAlerts(
            id=1,
            storage_cluster_id=1,
            source="diskpulse",
            alert_level="warning",
            alert_type="usage",
            description="usage alert",
            threshold=80,
            avg_use_ratio=85,
            related_id=1,
            related_type="StorageUsage",
            updated_at=NOW,
        ),
        models.StorageAlerts(
            id=2,
            storage_cluster_id=1,
            source="diskpulse",
            alert_level="warning",
            alert_type="usage",
            description="group alert",
            threshold=80,
            avg_use_ratio=85,
            related_id=1,
            related_type="Group",
            updated_at=NOW,
        ),
        models.StorageAlerts(
            id=3,
            storage_cluster_id=1,
            source="diskpulse",
            alert_level="warning",
            alert_type="usage",
            description="project alert",
            threshold=80,
            avg_use_ratio=85,
            related_id=1,
            related_type="Project",
            updated_at=NOW,
        ),
    ]
    backup = models.StorageBackUpRecord(
        id=1,
        user_id=1,
        source_path="/data/alpha/alice",
        destination_path="/backup/alpha/alice",
        start_time=NOW,
        end_time=NOW,
    )
    large_file = models.LargeFiles(
        id=1,
        user_id=1,
        group_id=1,
        linux_path="/data/alpha/alice/big.bin",
        size=2048,
        file_type="bin",
        updated_at=NOW,
        created_at=NOW,
    )
    db.add_all(
        [
            user,
            second_user,
            project,
            cluster,
            unused_cluster,
            tag,
            volume,
            qtree,
            group,
            usage,
            *alerts,
            backup,
            large_file,
        ]
    )
    db.commit()


def test_configuration_and_storage_resource_crud_gaps(db_session, monkeypatch):
    assert configCrud.get_storage_config(db_session).name == "storage conf"
    updated = configCrud.update_storage_config(
        db_session,
        StorageConf(name="mail-config", mail_host="mail.example.com"),
    )
    assert updated.name == "mail-config"

    seed_storage_graph(db_session)
    large_files, total = largeFilesCrud.get_large_files(
        db_session,
        page=1,
        size=10,
        nameLike="big",
        prop="size",
        order="descending",
        user_id=1,
        group_id=1,
    )
    assert (len(large_files), total) == (1, 1)

    fake_item = SimpleNamespace(
        linux_path="/data/alpha/alice/big.bin",
        size=2048,
        file_type="bin",
        updated_at=NOW,
        user=SimpleNamespace(rd_username="alice"),
        group=SimpleNamespace(name="alpha-team"),
    )
    monkeypatch.setattr(
        largeFilesCrud.largeFileSchema.LargeFileList,
        "model_validate",
        lambda _value: fake_item,
    )
    assert largeFilesCrud.export_large_files(db_session).getbuffer().nbytes > 0

    records, total = storageBackUpRecordCrud.get_storage_back_up_records(
        db_session,
        page=1,
        size=10,
        nameLike="alice",
        prop="end_time",
        order="descending",
        user_id=1,
    )
    assert (len(records), total) == (1, 1)
    assert storageBackUpRecordCrud.get_storage_back_up_record_by_id(db_session, 1).id == 1


def test_alert_project_and_storage_cluster_crud_gaps(db_session):
    seed_storage_graph(db_session)
    alerts, total = storageAlertCrud.get_storage_alerts(
        db_session,
        page=1,
        size=10,
        nameLike="usage",
        prop="updated_at",
        order="descending",
        related_type="StorageUsage",
        related_id=1,
        alert_type="usage",
        event_type="trigger",
        quota_basis="hard",
        delivery_status="legacy",
    )
    assert (len(alerts), total) == (1, 1)

    alerts, total = storageAlertCrud.get_storage_alerts(db_session, page=1, size=10)
    assert (len(alerts), total) == (3, 3)
    assert {alert.project_name for alert in alerts} == {"alpha"}

    total, clusters = storageClusterCrud.get_storage_clusters(
        db_session,
        page=1,
        size=10,
        nameLike="cluster",
        prop="name",
        order="descending",
        is_active=True,
    )
    assert total == 2
    assert clusters[0].name == "cluster-unused"

    updated = storageClusterCrud.update_storage_cluster(
        db_session,
        2,
        StorageClusterUpdate(
            storage_type="isilon",
            protocol="http",
            isilon_session_cache_mode="file",
        ),
    )
    assert updated.tls_verify is False
    assert updated.isilon_session_cache_path == ".isilon_cache/cache.json"

    with pytest.raises(HTTPException, match="referenced by a group"):
        storageClusterCrud.delete_storage_cluster(db_session, 1)
    assert storageClusterCrud.delete_storage_cluster(db_session, 2) is True


def test_project_and_storage_usage_crud_gaps(db_session):
    seed_storage_graph(db_session)
    assert projectsCrud.get_project_by_name(db_session, "alpha").id == 1
    projects, total = projectsCrud.get_projects(
        db_session,
        page=1,
        size=10,
        nameLike="alp",
        project_id=1,
        prop="name",
        order="descending",
        status=1,
    )
    assert (len(projects), total) == (1, 1)
    assert projectsCrud.get_project_storage_summary(db_session)
    assert projectsCrud.get_project_tree_summary(db_session)
    assert projectsCrud.get_project_tree_summary_by_id(db_session, 1, "used")
    assert projectsCrud.get_project_groups_storage_usage(db_session)["alpha"]["data"]

    usages, total = storageUsageCrud.get_storage_usages(
        db_session,
        page=1,
        size=10,
        nameLike="alice",
        prop="used",
        order="descending",
        user_id=1,
        group_id=1,
        storage_cluster_id=1,
        project_id=1,
        group_tag_id=1,
    )
    assert (len(usages), total) == (1, 1)

    is_existing, usage = storageUsageCrud.create_storage_usage(
        db_session,
        StorageUsageCreate(user_id=1, group_id=1),
        "/data/alpha/changed",
    )
    assert is_existing is False and usage.id == 1
    same_path, usage = storageUsageCrud.create_storage_usage(
        db_session,
        StorageUsageCreate(user_id=2, group_id=1),
        "/data/alpha/alice",
    )
    assert same_path is True and usage.id == 1
    created, new_usage = storageUsageCrud.create_storage_usage(
        db_session,
        StorageUsageCreate(user_id=2, group_id=1),
        "/data/alpha/bob",
    )
    assert created is False and new_usage.user_id == 2

    updated = storageUsageCrud.update_storage_usage(
        db_session,
        1,
        StorageUsageUpdate(user_id=1, group_id=1, limit=50),
    )
    assert updated.limit == 50 and updated.storage_cluster_id == 1
    assert storageUsageCrud.serialize_storage_usage(updated)["storage_target"]["type"] == "qtree"
    assert storageUsageCrud.get_export_data(db_session).shape[0] == 2
    assert storageUsageCrud.export_storage_usage_to_excel(db_session).getbuffer().nbytes > 0
    assert storageUsageCrud.delete_storage_usage(db_session, new_usage.id).id == new_usage.id


@pytest.mark.parametrize(
    "data, message",
    [
        ({"project_id": 999, "storage_cluster_id": 1, "group_tag_id": 1, "qtree_id": 1}, "Project"),
        ({"project_id": 1, "storage_cluster_id": 999, "group_tag_id": 1, "qtree_id": 1}, "Storage cluster"),
        ({"project_id": 1, "storage_cluster_id": 1, "group_tag_id": 999, "qtree_id": 1}, "Group tag"),
        ({"project_id": 1, "storage_cluster_id": 1, "group_tag_id": 1, "qtree_id": 999}, "Qtree"),
    ],
)
def test_group_binding_validation_reports_missing_targets(db_session, data, message):
    seed_storage_graph(db_session)
    with pytest.raises(HTTPException, match=message):
        groupCrud._validate_binding(db_session, data)


def test_group_binding_validation_rejects_qtree_for_isilon(db_session):
    seed_storage_graph(db_session)
    db_session.get(models.StorageCluster, 1).storage_type = "isilon"
    db_session.flush()
    with pytest.raises(HTTPException, match="do not support qtree"):
        groupCrud._validate_binding(
            db_session,
            {"project_id": 1, "storage_cluster_id": 1, "group_tag_id": 1, "qtree_id": 1},
        )
