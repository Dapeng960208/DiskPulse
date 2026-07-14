# -*- coding: utf-8 -*-
from unittest.mock import Mock, patch

import pytest

from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from celery_tasks.tasks.storages import load_collection_snapshot, run_collection_round
from models import StorageCluster, Volume
from routers.storage_cluster import _schedule_storage_collection


def test_load_collection_snapshot_targets_one_cluster(db_session):
    db_session.add_all(
        [
            StorageCluster(id=1, name="netapp-a", storage_type="netapp", is_active=True),
            StorageCluster(
                id=2,
                name="isilon-b",
                storage_type="isilon",
                protocol="http",
                tls_verify=False,
                is_active=True,
            ),
        ]
    )
    db_session.commit()

    snapshot = load_collection_snapshot(db_session, storage_cluster_id=2)

    assert [row["storage_cluster_id"] for row in snapshot] == [2]
    assert snapshot[0]["protocol"] == "http"
    assert snapshot[0]["tls_verify"] is False


def test_schedule_storage_collection_dispatches_target_cluster(caplog):
    with caplog.at_level("INFO", logger="uvicorn.error"):
        with patch("celery_tasks.tasks.storages.storages_schedule_fetching_task.delay") as delay:
            _schedule_storage_collection(42)

    delay.assert_called_once_with(42)
    assert "Storage collection scheduled for cluster 42" in caplog.text


def test_schedule_failure_is_logged_without_rolling_back_cluster(caplog):
    with patch(
        "celery_tasks.tasks.storages.storages_schedule_fetching_task.delay",
        side_effect=RuntimeError("broker unavailable"),
    ):
        _schedule_storage_collection(42)

    assert "Failed to schedule storage collection for cluster 42" in caplog.text


@pytest.mark.parametrize(
    (
        "storage_type",
        "client_name",
        "port",
        "protocol",
        "tls_verify",
        "expected_warning",
    ),
    [
        ("netapp", "NetAppClient", 80, "http", False, "storage API uses unencrypted HTTP"),
        ("isilon", "IsilonClient", 8080, "https", True, None),
        (
            "netapp",
            "NetAppClient",
            443,
            "https",
            False,
            "TLS certificate verification is disabled",
        ),
    ],
)
def test_storage_monitor_uses_snapshot_transport_settings(
    db_session,
    storage_type,
    client_name,
    port,
    protocol,
    tls_verify,
    expected_warning,
):
    db_session.add(
        StorageCluster(
            id=1,
            name=f"{storage_type}-a",
            storage_type=storage_type,
            storage_host="storage.local",
            storage_port=port,
            storage_user="svc",
            storage_password="secret",
            is_active=True,
        )
    )
    db_session.commit()
    logger = Mock()

    with patch(
        f"celery_tasks.manager.storagePulseMonitor.{client_name}"
    ) as client_class:
        StoragePulseMonitor(
            db_session,
            logger,
            storage_cluster_id=1,
            snapshot={
                "storage_type": storage_type,
                "storage_cluster_name": f"{storage_type}-a",
                "storage_host": "snapshot.local",
                "storage_port": port,
                "storage_user": "snapshot-user",
                "storage_password": "snapshot-secret",
                "protocol": protocol,
                "tls_verify": tls_verify,
                "rows": (),
            },
        ).setup()

    client_class.assert_called_once_with(
        hostname="snapshot.local",
        username="snapshot-user",
        password="snapshot-secret",
        port=port,
        logger=logger,
        protocol=protocol,
        tls_verify=tls_verify,
    )
    if expected_warning is None:
        logger.warning.assert_not_called()
    else:
        assert expected_warning in logger.warning.call_args.args[0]


def test_failed_collection_rolls_back_resource_changes(session_factory):
    with session_factory() as db:
        db.add(
            StorageCluster(
                id=1,
                name="isilon-a",
                storage_type="isilon",
                is_active=True,
            )
        )
        db.add(
            Volume(
                id=1,
                storage_cluster_id=1,
                name="/ifs/team",
                type="directory_quota",
            )
        )
        db.commit()
        snapshot = load_collection_snapshot(db, storage_cluster_id=1)

    class FailingMonitor:
        def __init__(self, db, _logger, _snapshot):
            self.db = db

        def collect_postgres(self):
            self.db.query(Volume).delete()
            raise RuntimeError("storage API failed")

        def close(self):
            pass

    with pytest.raises(RuntimeError, match="all storage clusters failed"):
        run_collection_round(
            snapshot,
            session_factory=session_factory,
            monitor_factory=FailingMonitor,
        )

    with session_factory() as db:
        assert db.get(Volume, 1) is not None
