# -*- coding: utf-8 -*-
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest
from urllib3.exceptions import InsecureRequestWarning

from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from celery_tasks.tasks.storages import load_collection_snapshot, run_collection_round
from models import AuditEvent, StorageCluster, Volume
from routers.storage_cluster import _schedule_storage_collection
from services.audit_service import AuditContext
from services.storageClusterService import schedule_storage_collection


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
                isilon_session_cache_mode="file",
                isilon_session_cache_path=".isilon_cache/isilon-b.json",
                is_active=True,
            ),
        ]
    )
    db_session.commit()

    snapshot = load_collection_snapshot(db_session, storage_cluster_id=2)

    assert [row["storage_cluster_id"] for row in snapshot] == [2]
    assert snapshot[0]["protocol"] == "http"
    assert snapshot[0]["tls_verify"] is False
    assert snapshot[0]["isilon_session_cache_mode"] == "file"
    assert snapshot[0]["isilon_session_cache_path"] == ".isilon_cache/isilon-b.json"


def test_schedule_storage_collection_dispatches_target_cluster(caplog):
    with caplog.at_level("INFO", logger="services.storageClusterService"):
        with patch("celery_tasks.tasks.storages.storages_schedule_fetching_task.delay") as delay:
            _schedule_storage_collection(42)

    delay.assert_called_once_with(42)
    assert "Storage collection scheduled for cluster 42" in caplog.text
    assert any(
        record.name == "services.storageClusterService"
        and record.getMessage() == "Storage collection scheduled for cluster 42"
        for record in caplog.records
    )


def test_schedule_storage_collection_passes_request_correlation_to_task():
    context = AuditContext(
        request_id=uuid4(),
        trace_id=uuid4(),
        operation_id=uuid4(),
        actor_user_id=7,
    )

    with patch("celery_tasks.tasks.storages.storages_schedule_fetching_task.delay") as delay:
        schedule_storage_collection(42, audit_context=context)

    delay.assert_called_once_with(
        42,
        audit_context_payload={
            "request_id": context.request_id,
            "trace_id": context.trace_id,
            "operation_id": context.operation_id,
            "actor_type": "user",
            "actor_user_id": 7,
        },
    )


def test_schedule_failure_is_logged_without_rolling_back_cluster(caplog):
    with caplog.at_level("ERROR", logger="services.storageClusterService"):
        with patch(
            "celery_tasks.tasks.storages.storages_schedule_fetching_task.delay",
            side_effect=RuntimeError("broker unavailable"),
        ):
            _schedule_storage_collection(42)

    assert "Failed to schedule storage collection for cluster 42" in caplog.text
    assert any(
        record.name == "services.storageClusterService"
        and record.getMessage() == "Failed to schedule storage collection for cluster 42"
        for record in caplog.records
    )


@pytest.mark.parametrize(
    (
        "storage_type",
        "client_name",
        "port",
        "protocol",
        "tls_verify",
        "expected_warning",
        "suppress_insecure_warning",
    ),
    [
        ("netapp", "NetAppClient", 80, "http", False, "storage API uses unencrypted HTTP", False),
        ("isilon", "IsilonClient", 8080, "https", True, None, False),
        (
            "netapp",
            "NetAppClient",
            443,
            "https",
            False,
            "TLS certificate verification is disabled",
            True,
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
    suppress_insecure_warning,
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

    with (
        patch(f"celery_tasks.manager.storagePulseMonitor.{client_name}") as client_class,
        patch("celery_tasks.manager.storagePulseMonitor.disable_warnings") as disable_warnings,
    ):
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

    expected = dict(
        hostname="snapshot.local",
        username="snapshot-user",
        password="snapshot-secret",
        port=port,
        logger=logger,
        protocol=protocol,
        tls_verify=tls_verify,
    )
    if storage_type == "isilon":
        expected.update(
            session_cache_mode="none",
            session_cache_path=None,
        )
    client_class.assert_called_once_with(**expected)
    if expected_warning is None:
        logger.warning.assert_not_called()
    else:
        assert expected_warning in logger.warning.call_args.args[0]
    if suppress_insecure_warning:
        disable_warnings.assert_called_once_with(InsecureRequestWarning)
    else:
        disable_warnings.assert_not_called()


def test_isilon_monitor_passes_session_cache_settings(db_session):
    db_session.add(
        StorageCluster(
            id=1,
            name="isilon-a",
            storage_type="isilon",
            storage_host="storage.local",
            storage_port=8080,
            storage_user="svc",
            storage_password="secret",
            isilon_session_cache_mode="redis",
            is_active=True,
        )
    )
    db_session.commit()

    with patch("celery_tasks.manager.storagePulseMonitor.IsilonClient") as client_class:
        StoragePulseMonitor(
            db_session,
            Mock(),
            storage_cluster_id=1,
            snapshot={
                "storage_type": "isilon",
                "storage_cluster_name": "isilon-a",
                "storage_host": "snapshot.local",
                "storage_port": 8080,
                "storage_user": "snapshot-user",
                "storage_password": "snapshot-secret",
                "protocol": "https",
                "tls_verify": True,
                "isilon_session_cache_mode": "redis",
                "isilon_session_cache_path": None,
                "rows": (),
            },
        ).setup()

    assert client_class.call_args.kwargs["session_cache_mode"] == "redis"
    assert client_class.call_args.kwargs["session_cache_path"] is None


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


@pytest.mark.parametrize("fails", [False, True], ids=["success", "failure"])
def test_collection_round_writes_service_audit_result_without_snapshot_secrets(session_factory, fails):
    with session_factory() as db:
        db.add(StorageCluster(id=1, name="isilon-a", storage_type="isilon", is_active=True))
        db.commit()
        snapshot = load_collection_snapshot(db, storage_cluster_id=1)

    class Monitor:
        def __init__(self, _db, _logger, _cluster):
            pass

        def collect_postgres(self):
            if fails:
                raise RuntimeError("collector-private-error")
            return {"storage_usage_ids": (11,), "group_ids": (12,)}

        def close(self):
            pass

    context = AuditContext(
        request_id=uuid4(),
        trace_id=uuid4(),
        operation_id=uuid4(),
        actor_user_id=7,
    )
    if fails:
        with pytest.raises(RuntimeError, match="all storage clusters failed"):
            run_collection_round(
                snapshot,
                session_factory=session_factory,
                monitor_factory=Monitor,
                questdb_writer=lambda *_args: None,
                audit_context=context,
            )
    else:
        run_collection_round(
            snapshot,
            session_factory=session_factory,
            monitor_factory=Monitor,
            questdb_writer=lambda *_args: None,
            audit_context=context,
        )

    with session_factory() as db:
        events = db.query(AuditEvent).order_by(AuditEvent.occurred_at, AuditEvent.id).all()
    assert [(event.phase, event.outcome) for event in events] == [
        ("attempt", "success"),
        ("result", "failure" if fails else "success"),
    ]
    assert all((event.action, event.resource_type, event.resource_id, event.actor_type) == (
        "storage.collection.run",
        "storage_cluster",
        1,
        "user",
    ) for event in events)
    assert events[1].reason_code == ("collection_failed" if fails else None)
    assert {event.request_id for event in events} == {context.request_id}
    assert {event.trace_id for event in events} == {context.trace_id}
    assert {event.operation_id for event in events} == {context.operation_id}
    assert all(UUID(event.request_id) and UUID(event.trace_id) and UUID(event.operation_id) for event in events)
    assert "collector-private-error" not in str(events[1].event_metadata)
