# -*- coding: utf-8 -*-
import importlib
import json
from datetime import datetime, timezone
from unittest.mock import ANY, patch

import pytest
from sqlalchemy.exc import IntegrityError

import models
from routers import storage_cluster
from services import storageHealthAnalyticsService


START = datetime(2026, 7, 20, 16, 0, tzinfo=timezone.utc)
END = datetime(2026, 7, 20, 18, 0, tzinfo=timezone.utc)
EVENT_AT = datetime(2026, 7, 21, 1, 5)


def _contract_module(name: str):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        pytest.fail(f"缺少约定模块 {name}: {error}")


def _definition_model():
    model = getattr(models, "VendorEventDefinition", None)
    assert model is not None, "models.VendorEventDefinition 尚未实现"
    return model


def _field(value, name: str):
    return value.get(name) if isinstance(value, dict) else getattr(value, name)


def _definition(**overrides):
    payload = {
        "storage_type": "netapp",
        "event_code": "disk.offline",
        "association_type": "fault_log",
        "title_zh": "磁盘离线",
        "description_zh": "存储节点报告磁盘已离线。",
        "official_reference_url": "https://docs.netapp.example/events/disk.offline",
    }
    payload.update(overrides)
    return _definition_model()(**payload)


def _add_vendor_alert(
    db,
    *,
    alert_id: int,
    event_code: str,
    fingerprint: str,
    severity: str,
    description: str,
    external_event_id: str | None = None,
):
    db.add(
        models.StorageAlerts(
            id=alert_id,
            storage_cluster_id=1,
            source="netapp",
            external_event_id=external_event_id or f"event-{alert_id}",
            fingerprint=fingerprint,
            severity=severity,
            alert_level=severity,
            alert_type="vendor_event",
            description=description,
            related_type="node",
            related_info={
                "event_code": event_code,
                "object_id": "node-a",
                "raw": {"secret": f"raw-payload-{alert_id}"},
            },
            updated_at=EVENT_AT,
        )
    )


def test_vendor_event_definition_enforces_vendor_and_code_uniqueness(db_session):
    db_session.add_all([_definition(), _definition(title_zh="重复定义")])

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_vendor_event_definition_crud_round_trip(db_session):
    crud = _contract_module("crud.vendorEventDefinitionCrud")
    created = crud.create_definition(
        db_session,
        storage_type="netapp",
        event_code="nblade.execsOverLimit",
        association_type="performance_anomaly",
        title_zh="并发请求超过限制",
        description_zh="节点收到的并发请求超过允许上限。",
        official_reference_url="https://docs.netapp.example/events/nblade.execsOverLimit",
    )
    db_session.commit()

    fetched = crud.get_definition(db_session, "netapp", "nblade.execsOverLimit")
    assert fetched.id == created.id
    assert crud.list_definitions(db_session, storage_type="netapp") == [fetched]

    updated = crud.update_definition(db_session, created.id, title_zh="并发请求数超过上限")
    db_session.commit()
    assert updated.title_zh == "并发请求数超过上限"

    assert crud.delete_definition(db_session, created.id) is True
    db_session.commit()
    assert crud.get_definition(db_session, "netapp", "nblade.execsOverLimit") is None


def test_unknown_vendor_event_definition_uses_chinese_fallback_without_persisting(db_session):
    service = _contract_module("services.vendorEventDefinitionService")

    resolved = service.resolve_definition(db_session, "netapp", "vendor.unknown.code")

    assert _field(resolved, "association_type") == "unknown"
    assert _field(resolved, "association_type_label") == "未分类厂商事件"
    assert _field(resolved, "title_zh") == "未收录的厂商事件代码"
    assert _field(resolved, "event_code") == "vendor.unknown.code"
    assert db_session.query(_definition_model()).count() == 0


def test_common_vendor_event_seed_is_idempotent_and_covers_both_storage_types(db_session):
    crud = _contract_module("crud.vendorEventDefinitionCrud")
    service = _contract_module("services.vendorEventDefinitionService")

    first_inserted = service.seed_common_definitions(db_session)
    db_session.commit()
    first_rows = crud.list_definitions(db_session)
    second_inserted = service.seed_common_definitions(db_session)
    db_session.commit()
    second_rows = crud.list_definitions(db_session)

    keys = {(row.storage_type, row.event_code) for row in first_rows}
    assert first_inserted >= 2
    assert second_inserted == 0
    assert len(second_rows) == len(first_rows)
    assert {row.storage_type for row in first_rows} == {"netapp", "isilon"}
    assert ("netapp", "wafl.vol.blks_used.done") in keys
    assert ("isilon", "SW_JOBENG_JOB_STATE") in keys
    assert all(row.title_zh and row.description_zh for row in first_rows)


@pytest.fixture
def analytics_client(api_client_factory, auth_headers, db_session):
    db_session.add_all(
        [
            models.User(id=1, rd_username="alice"),
            models.StorageCluster(
                id=1,
                name="cluster-a",
                storage_type="netapp",
                storage_host="storage.local",
                is_active=True,
            ),
        ]
    )
    db_session.commit()
    return api_client_factory([storage_cluster.router], headers=auth_headers)


def test_system_events_endpoint_forwards_exact_fingerprint_filter(analytics_client):
    payload = {"data": [], "total": 0, "page": 1, "page_size": 20}
    fingerprint = "netapp:disk.offline:node:node-a"
    with patch("routers.storage_cluster.get_system_events", return_value=payload) as service:
        response = analytics_client.get(
            "/storage-pulse/api/storage-clusters/1/analytics/system-events",
            params={
                "start_time": START.isoformat(),
                "end_time": END.isoformat(),
                "fingerprint": fingerprint,
            },
        )

    assert response.status_code == 200
    service.assert_called_once_with(
        ANY,
        1,
        START,
        END,
        keyword=None,
        severity=None,
        fingerprint=fingerprint,
        page=1,
        page_size=20,
    )


def test_system_events_return_readable_semantics_for_exact_fingerprint(db_session):
    db_session.add(models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"))
    db_session.add(
        _definition(
            event_code="nblade.execsOverLimit",
            association_type="performance_anomaly",
            title_zh="并发请求超过限制",
            description_zh="客户端并发请求数超过节点允许上限。",
        )
    )
    wanted = "netapp:nblade.execsOverLimit:node:node-a"
    _add_vendor_alert(
        db_session,
        alert_id=101,
        event_code="nblade.execsOverLimit",
        fingerprint=wanted,
        severity="warning",
        description="The number of in-flight requests is greater than the maximum allowed.",
    )
    _add_vendor_alert(
        db_session,
        alert_id=102,
        event_code="nblade.execsOverLimit",
        fingerprint="netapp:nblade.execsOverLimit:node:node-b",
        severity="warning",
        description="another node",
    )
    db_session.commit()

    result = storageHealthAnalyticsService.get_system_events(
        db_session,
        1,
        START,
        END,
        fingerprint=wanted,
    )

    assert result["total"] == 1
    row = result["data"][0]
    assert row["id"] == 101
    assert row["fingerprint"] == wanted
    assert row["event_code"] == "nblade.execsOverLimit"
    assert row["association_type"] == "performance_anomaly"
    assert row["association_type_label"] == "性能异常"
    assert row["title_zh"] == "并发请求超过限制"
    assert row["description_zh"] == "客户端并发请求数超过节点允许上限。"
    assert "raw-payload" not in json.dumps(result, ensure_ascii=False, default=str)
    assert "related_info" not in row


def test_single_system_event_detail_keeps_normalized_log_but_excludes_raw_payload(
    analytics_client, db_session
):
    _add_vendor_alert(
        db_session,
        alert_id=501,
        event_code="vendor.unknown.code",
        fingerprint="netapp:vendor.unknown.code:node:node-a",
        severity="error",
        description="Normalized vendor log message",
    )
    db_session.commit()

    response = analytics_client.get(
        "/storage-pulse/api/storage-clusters/1/analytics/system-events/501"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 501
    assert body["description"] == "Normalized vendor log message"
    assert body["association_type"] == "unknown"
    assert body["association_type_label"] == "未分类厂商事件"
    assert body["title_zh"] == "未收录的厂商事件代码"
    serialized = json.dumps(body, ensure_ascii=False)
    assert "raw-payload-501" not in serialized
    assert "related_info" not in body


def test_repeated_faults_exclude_repeated_informational_system_activity(db_session):
    db_session.add(models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"))
    db_session.add_all(
        [
            _definition(
                event_code="wafl.vol.blks_used.done",
                association_type="system_activity",
                title_zh="卷块使用量计算完成",
                description_zh="卷块使用量后台计算已完成。",
            ),
            _definition(),
        ]
    )
    for alert_id in (1, 2):
        _add_vendor_alert(
            db_session,
            alert_id=alert_id,
            event_code="wafl.vol.blks_used.done",
            fingerprint="netapp:wafl.vol.blks_used.done:node:node-a",
            severity="info",
            description="Volume block usage calculation completed.",
        )
    for alert_id in (3, 4):
        _add_vendor_alert(
            db_session,
            alert_id=alert_id,
            event_code="disk.offline",
            fingerprint="netapp:disk.offline:node:node-a",
            severity="critical",
            description="Disk offline.",
        )
    db_session.commit()

    result = storageHealthAnalyticsService.get_repeated_faults(db_session, 1, START, END)

    assert len(result["data"]) == 1
    fault = result["data"][0]
    assert fault["event_code"] == "disk.offline"
    assert fault["association_type"] == "fault_log"
    assert fault["association_type_label"] == "故障日志"
    assert fault["title_zh"] == "磁盘离线"
    assert fault["count"] == 2
