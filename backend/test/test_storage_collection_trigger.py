# -*- coding: utf-8 -*-
from celery_tasks.tasks.storages import load_collection_snapshot
from models import StorageCluster


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
