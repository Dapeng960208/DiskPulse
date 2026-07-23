# -*- coding: utf-8 -*-
from datetime import datetime
from unittest.mock import Mock

import pytest
import requests

import models
from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from celery_tasks.tasks import storages
from celery_tasks.tasks.storages import finalize_project_totals
from utils.isilonClient import IsilonClient


NOW = datetime(2026, 7, 14, 10, 0, 0)
GB = 1024**3


def _seed_cluster(db, storage_type="netapp"):
    db.add(
        models.StorageCluster(
            id=1,
            name=f"{storage_type}-a",
            storage_type=storage_type,
            is_active=True,
        )
    )
    db.commit()


def _monitor(db, storage_type="netapp", rows=()):
    return StoragePulseMonitor(
        db,
        Mock(),
        storage_cluster_id=1,
        snapshot={
            "storage_type": storage_type,
            "storage_cluster_name": f"{storage_type}-a",
            "rows": tuple(rows),
        },
    )


def _group_snapshot(group):
    return {
        "group_id": group.id,
        "project_id": group.project_id,
        "storage_cluster_id": group.storage_cluster_id,
        "group_tag_id": group.group_tag_id,
    }


def test_isilon_storage_pools_use_onefs_9_11_endpoint():
    client = object.__new__(IsilonClient)
    client._get = Mock(
        return_value={"storagepools": [{"name": "pool-a", "type": "nodepool"}]}
    )

    assert client.get_storage_pools() == [{"name": "pool-a", "type": "nodepool"}]
    client._get.assert_called_once_with(
        "/16/storagepool/storagepools",
        params={"toplevels": "true"},
    )


def test_isilon_quota_requests_enable_name_resolution_for_local_service_account():
    client = object.__new__(IsilonClient)
    client._get = Mock(return_value={"quotas": []})

    assert client.get_quotas() == []
    client._get.assert_called_once_with(
        "/1/quota/quotas",
        params={
            "limit": 1000,
            "resolve_names": "true",
            "recurse_path_children": "false",
        },
    )


@pytest.mark.parametrize("payload", [{}, {"storagepools": {}}, {"storagepools": None}])
def test_isilon_storage_pools_reject_invalid_envelopes(payload):
    client = object.__new__(IsilonClient)
    client._get = Mock(return_value=payload)

    with pytest.raises(ValueError, match="storagepools"):
        client.get_storage_pools()


def test_isilon_client_close_logs_out_uncached_session():
    client = object.__new__(IsilonClient)
    client.session = Mock()
    client._session_cache_enabled = False
    client._session_url = "https://storage.local:8080/session/1/session"
    client._log = Mock()

    client.close()

    client.session.delete.assert_called_once_with(client._session_url, timeout=15)
    client.session.close.assert_called_once_with()


def test_isilon_client_close_still_closes_when_logout_fails():
    client = object.__new__(IsilonClient)
    client.session = Mock()
    client.session.delete.side_effect = requests.ConnectionError("offline")
    client._session_cache_enabled = False
    client._session_url = "https://storage.local:8080/session/1/session"
    client._log = Mock()

    client.close()

    client.session.close.assert_called_once_with()
    client._log.assert_called_once()


def test_isilon_client_close_preserves_cached_session():
    client = object.__new__(IsilonClient)
    client.session = Mock()
    client._session_cache_enabled = True
    client._session_url = "https://storage.local:8080/session/1/session"
    client._log = Mock()

    client.close()

    client.session.delete.assert_not_called()
    client.session.close.assert_called_once_with()


def test_isilon_capacity_pools_map_real_storage_pool_usage(db_session):
    _seed_cluster(db_session, "isilon")
    monitor = _monitor(db_session, "isilon")
    monitor.client = Mock()
    monitor.client.get_storage_pools.return_value = [
        {
            "name": "pool-a",
            "type": "nodepool",
            "usage": {
                "total_bytes": str(200 * GB),
                "used_bytes": str(50 * GB),
            },
        }
    ]

    pools = monitor.fetch_capacity_pools()

    assert [(pool.name, pool.limit, pool.used, pool.use_ratio) for pool in pools] == [
        ("pool-a", 200.0, 50.0, 25.0)
    ]
    assert all(pool.name != "isilon_cluster" for pool in pools)


@pytest.mark.parametrize(
    "invalid_record",
    [
        {"usage": {"total_bytes": str(200 * GB), "used_bytes": str(50 * GB)}},
        {"name": "pool-b", "usage": {"used_bytes": str(50 * GB)}},
        {"name": "pool-b", "usage": {"total_bytes": str(200 * GB)}},
    ],
    ids=["missing-name", "missing-total-bytes", "missing-used-bytes"],
)
def test_isilon_capacity_pools_reject_any_malformed_record(
    db_session, invalid_record
):
    _seed_cluster(db_session, "isilon")
    db_session.add(
        models.Aggregate(
            id=1,
            storage_cluster_id=1,
            name="old-pool",
            limit=100,
            used=25,
        )
    )
    db_session.commit()
    monitor = _monitor(db_session, "isilon")
    monitor.client = Mock()
    monitor.client.get_storage_pools.return_value = [
        {
            "name": "pool-a",
            "usage": {
                "total_bytes": str(200 * GB),
                "used_bytes": str(50 * GB),
            },
        },
        invalid_record,
    ]

    with pytest.raises(ValueError):
        monitor.fetch_capacity_pools()

    assert db_session.get(models.Aggregate, 1).name == "old-pool"


def test_isilon_directory_quota_is_a_storage_space(db_session):
    _seed_cluster(db_session, "isilon")
    monitor = _monitor(db_session, "isilon")
    monitor.client = Mock()
    monitor.client.get_quotas.return_value = [
        {
            "id": "quota-42",
            "type": "directory",
            "path": "/ifs/team",
            "thresholds": {"hard": 500 * GB, "soft": 400 * GB},
            "usage": {"logical": 125 * GB},
        }
    ]

    spaces, quotas = monitor._fetch_user_quotas_isilon({}, {}, {}, {}, {})

    assert quotas == []
    assert len(spaces) == 1
    assert spaces[0].name == "/ifs/team"
    assert spaces[0].type == "directory_quota"
    assert spaces[0].aggregate == ""
    assert spaces[0].performance_object_id == "quota-42"


def test_isilon_user_quota_uses_uid_persona_without_name_resolution(db_session):
    _seed_cluster(db_session, "isilon")
    monitor = _monitor(db_session, "isilon")
    monitor.client = Mock()
    monitor._process_quota_user_isilon = Mock(return_value=None)

    monitor._fetch_user_quotas_isilon(
        {},
        {},
        {},
        {},
        {},
        raw_quotas=[
            {
                "type": "user",
                "path": "/ifs/team",
                "persona": {"id": "UID:12345"},
                "thresholds": {"hard": 100 * GB},
                "usage": {"logical": 25 * GB},
            },
            {
                "type": "user",
                "path": "/ifs/team",
                "persona": {"id": "SID:S-1-5-21-1000"},
                "thresholds": {"hard": 100 * GB},
                "usage": {"logical": 25 * GB},
            },
        ],
    )

    monitor._process_quota_user_isilon.assert_called_once()
    record = monitor._process_quota_user_isilon.call_args.args[0]
    assert record["rd_username"] == "12345"


def test_empty_successful_sync_preserves_existing_resources(db_session):
    _seed_cluster(db_session, "isilon")
    db_session.add(
        models.Volume(
            id=1,
            storage_cluster_id=1,
            name="/ifs/team",
            type="directory_quota",
        )
    )
    db_session.commit()
    monitor = _monitor(db_session, "isilon")

    monitor.sync_data_to_postgres(
        [],
        models.Volume,
        ["name", "storage_cluster_id"],
        delete_redundant=True,
    )

    assert db_session.get(models.Volume, 1) is not None


def test_successful_netapp_collection_migrates_null_qtree_binding_to_volume(db_session):
    _seed_cluster(db_session)
    project = models.Project(id=1, name="project-a")
    tag = models.GroupTag(id=1, name="production")
    volume = models.Volume(
        id=1,
        storage_cluster_id=1,
        name="vol-a",
        limit=200,
        used=50,
        use_ratio=25,
    )
    null_qtree = models.Qtree(
        id=1,
        storage_cluster_id=1,
        volume_id=1,
        name="null",
        limit=200,
        used=50,
        use_ratio=25,
    )
    group = models.Group(
        id=1,
        project_id=1,
        storage_cluster_id=1,
        group_tag_id=1,
        qtree_id=1,
        name="group-a",
    )
    db_session.add_all([project, tag, volume, null_qtree, group])
    db_session.commit()

    monitor = _monitor(db_session, rows=[_group_snapshot(group)])
    monitor.client = Mock()
    monitor.client.get_aggregates.return_value = [
        {
            "name": "aggr-a",
            "space": {
                "block_storage": {"size": 500 * GB, "available": 300 * GB}
            },
        }
    ]
    monitor.client.get_volumes.return_value = [
        {
            "uuid": "volume-uuid-a",
            "name": "vol-a",
            "state": "online",
            "type": "rw",
            "svm": {"name": "svm-a"},
            "aggregates": [{"name": "aggr-a"}],
            "space": {"size": 200 * GB, "available": 150 * GB},
        }
    ]
    monitor.client.get_qtrees.return_value = []
    monitor.client.get_quota_reports.return_value = []

    monitor.execute_data_collection(include_questdb=False)
    db_session.expire_all()

    migrated = db_session.get(models.Group, 1)
    assert (migrated.volume_id, migrated.qtree_id) == (1, None)
    assert db_session.get(models.Qtree, 1) is None
    assert db_session.get(models.Volume, 1).performance_object_id == "volume-uuid-a"


@pytest.mark.parametrize(
    ("storage_type", "target_type", "expected"),
    [
        ("netapp", "volume", (200, 50, 25)),
        ("netapp", "qtree", (80, 20, 25)),
        ("isilon", "volume", (200, 50, 25)),
    ],
)
def test_group_summary_supports_native_storage_targets(
    db_session, storage_type, target_type, expected
):
    _seed_cluster(db_session, storage_type)
    project = models.Project(id=1, name="project-a")
    tag = models.GroupTag(id=1, name="production")
    volume = models.Volume(
        id=1,
        storage_cluster_id=1,
        name="vol-a" if storage_type == "netapp" else "/ifs/team",
        limit=200,
        used=50,
        use_ratio=25,
    )
    qtree = models.Qtree(
        id=1,
        storage_cluster_id=1,
        volume_id=1,
        name="qtree-a",
        limit=80,
        used=20,
        use_ratio=25,
    )
    group = models.Group(
        id=1,
        project_id=1,
        storage_cluster_id=1,
        group_tag_id=1,
        volume_id=1 if target_type == "volume" else None,
        qtree_id=1 if target_type == "qtree" else None,
        name="group-a",
    )
    db_session.add_all([project, tag, volume, qtree, group])
    db_session.commit()

    monitor = _monitor(db_session, storage_type, [_group_snapshot(group)])
    monitor.aggregate_group_usage()
    db_session.expire(group)

    assert (group.limit, group.used, group.use_ratio) == expected


def test_questdb_includes_netapp_groups_bound_to_volumes(db_session):
    _seed_cluster(db_session)
    db_session.add_all(
        [
            models.Project(id=1, name="project-a"),
            models.GroupTag(id=1, name="production"),
            models.Volume(id=1, storage_cluster_id=1, name="vol-a", used=50),
            models.Group(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                volume_id=1,
                name="group-a",
            ),
        ]
    )
    db_session.commit()
    monitor = _monitor(db_session)
    captured = {}
    monitor.insert_metrics_to_questdb = lambda table, rows: captured.setdefault(
        table, [row.id for row in rows]
    )

    monitor.write_questdb()

    assert captured["group"] == [1]


def test_project_totals_are_written_to_project_trend_after_aggregation(db_session):
    _seed_cluster(db_session)
    db_session.add_all(
        [
            models.Project(id=1, name="project-a"),
            models.GroupTag(id=1, name="production"),
            models.Volume(id=1, storage_cluster_id=1, name="vol-a"),
            models.Group(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                volume_id=1,
                name="group-a",
                limit=100,
                soft_limit=80,
                used=25,
            ),
        ]
    )
    db_session.commit()
    refreshed_project_ids = finalize_project_totals(db_session, {1: True}, NOW)
    questdb_session = Mock()

    storages.write_project_usage_metrics(
        db_session,
        refreshed_project_ids,
        collected_at=NOW,
        session_factory=lambda: questdb_session,
    )

    [metric] = questdb_session.add_all.call_args.args[0]
    assert (
        metric.project_id,
        metric.used,
        metric.used_ratio,
        metric.soft_limit,
        metric.soft_use_ratio,
        metric.updated_at,
    ) == ("1", 25, 25, 80, 31.25, NOW - timedelta(hours=8))


def test_project_totals_dedupe_by_target_type_and_id(db_session):
    _seed_cluster(db_session)
    db_session.add_all(
        [
            models.Project(id=1, name="project-a"),
            models.GroupTag(id=1, name="production"),
            models.Volume(id=1, storage_cluster_id=1, name="vol-a"),
            models.Qtree(
                id=1,
                storage_cluster_id=1,
                volume_id=1,
                name="qtree-a",
            ),
        ]
    )
    db_session.flush()
    db_session.add_all(
        [
            models.Group(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                volume_id=1,
                name="volume-a",
                limit=100,
                used=25,
            ),
            models.Group(
                id=2,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                volume_id=1,
                name="volume-a-alias",
                limit=100,
                used=25,
            ),
            models.Group(
                id=3,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                qtree_id=1,
                name="qtree-a",
                limit=30,
                used=10,
            ),
        ]
    )
    db_session.commit()

    finalize_project_totals(db_session, {1: True}, NOW)
    db_session.expire_all()
    project = db_session.get(models.Project, 1)

    assert (project.limit, project.used, project.use_ratio) == (130, 35, 26.92)
