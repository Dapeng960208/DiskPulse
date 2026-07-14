# -*- coding: utf-8 -*-
from unittest.mock import patch

from celery_tasks.tasks.storages import load_collection_snapshot
from models import StorageCluster
from routers.storage_cluster import _schedule_storage_collection


def test_load_collection_snapshot_targets_one_cluster(db_session):
    db_session.add_all(
        [
            StorageCluster(id=1, name="netapp-a", storage_type="netapp", is_active=True),
            StorageCluster(id=2, name="isilon-b", storage_type="isilon", is_active=True),
        ]
    )
    db_session.commit()

    snapshot = load_collection_snapshot(db_session, storage_cluster_id=2)

    assert [row["storage_cluster_id"] for row in snapshot] == [2]


def test_schedule_storage_collection_dispatches_target_cluster():
    with patch("celery_tasks.tasks.storages.storages_schedule_fetching_task.delay") as delay:
        _schedule_storage_collection(42)

    delay.assert_called_once_with(42)


def test_schedule_failure_is_logged_without_rolling_back_cluster(caplog):
    with patch(
        "celery_tasks.tasks.storages.storages_schedule_fetching_task.delay",
        side_effect=RuntimeError("broker unavailable"),
    ):
        _schedule_storage_collection(42)

    assert "Failed to schedule storage collection for cluster 42" in caplog.text
