# -*- coding: utf-8 -*-
import importlib
import json
from datetime import datetime, timezone
import inspect
from unittest.mock import ANY, patch

import pytest
from pydantic import ValidationError
from sqlalchemy import event as sqlalchemy_event
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
        "official_reference_url": "https://docs.netapp.com/test/events/disk.offline",
        "version_scope": "ONTAP test fixture",
        "review_status": "reviewed",
        "recommended_solution_zh": "核对厂商事件详情并按官方处置步骤处理。",
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


def test_reviewed_vendor_event_definition_requires_complete_official_evidence():
    schema = _contract_module("schemas.vendorEventDefinitionSchema")
    base = {
        "storage_type": "netapp",
        "event_code": "disk.offline",
        "title_zh": "磁盘离线",
        "description_zh": "存储节点报告磁盘已离线。",
        "review_status": "reviewed",
    }

    with pytest.raises(ValidationError):
        schema.VendorEventDefinitionCreate(
            **base,
            association_type="unknown",
            official_reference_url="https://docs.netapp.com/test/events/disk.offline",
            version_scope="ONTAP 9",
        )
    with pytest.raises(ValidationError):
        schema.VendorEventDefinitionCreate(
            **base,
            association_type="fault_log",
            official_reference_url=None,
            version_scope="ONTAP 9",
        )
    with pytest.raises(ValidationError):
        schema.VendorEventDefinitionCreate(
            **base,
            association_type="fault_log",
            official_reference_url="https://docs.netapp.com/test/events/disk.offline",
            version_scope=None,
        )
    with pytest.raises(ValidationError):
        schema.VendorEventDefinitionCreate(
            **base,
            association_type="fault_log",
            official_reference_url="https://docs.netapp.com/test/events/disk.offline",
            version_scope="ONTAP 9",
            recommended_solution_zh="   ",
        )

    validated = schema.VendorEventDefinitionCreate(
        **base,
        association_type="fault_log",
        official_reference_url="https://docs.netapp.com/test/events/disk.offline",
        version_scope="ONTAP 9",
        recommended_solution_zh="核对磁盘状态并按官方处置步骤处理。",
    )
    assert validated.review_status == "reviewed"
    host_only = schema.VendorEventDefinitionCreate(
        **base,
        association_type="fault_log",
        official_reference_url="https://docs.netapp.com",
        version_scope="ONTAP 9",
        recommended_solution_zh="核对磁盘状态并按官方处置步骤处理。",
    )
    assert host_only.official_reference_url == "https://docs.netapp.com/"

    for invalid_reference in (
        "https://",
        "https://exa mple.com/event",
        "https://example.com/event",
        "https://docs.netapp.com@evil.example/event",
        "https://docs.netapp.com:443/event",
        "https://docs.netapp.com./event",
        "https://docs.netapp.com/event@v1",
        "https://www.dell.com/support/manuals/en-us/powerscale-onefs/events",
    ):
        with pytest.raises(ValidationError):
            schema.VendorEventDefinitionCreate(
                **base,
                association_type="fault_log",
                official_reference_url=invalid_reference,
                version_scope="ONTAP 9",
            )

    with pytest.raises(ValidationError):
        schema.VendorEventDefinitionCreate(
            storage_type="isilon",
            event_code="cross.vendor.reference",
            association_type="fault_log",
            title_zh="错误厂商依据",
            description_zh="PowerScale 定义不能使用 NetApp 文档背书。",
            official_reference_url="https://docs.netapp.com/us-en/ontap-ems/",
            version_scope="OneFS 9",
            review_status="reviewed",
        )


def test_database_rejects_reviewed_definition_without_complete_official_evidence(
    db_session,
):
    db_session.add(
        _definition_model()(
            storage_type="netapp",
            event_code="invalid.reviewed",
            association_type="unknown",
            title_zh="无效已审核定义",
            description_zh="绕过 API 写入的不完整定义。",
            review_status="reviewed",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(
        _definition(
            event_code="invalid.reviewed.solution",
            recommended_solution_zh="   ",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    for index, invalid_reference in enumerate(
        (
            "https://",
            "https://example.com/event",
            "https://docs.netapp.com@evil.example/event",
        )
    ):
        db_session.add(
            _definition(
                event_code=f"invalid.official.domain.{index}",
                official_reference_url=invalid_reference,
            )
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    for index, values in enumerate(
        (
            {
                "storage_type": "netapp",
                "official_reference_url": (
                    "https://www.dell.com/support/manuals/en-us/powerscale-onefs/events"
                ),
            },
            {
                "storage_type": "isilon",
                "official_reference_url": (
                    "https://docs.netapp.com/us-en/ontap-ems/secd-authsys-events.html"
                ),
            },
        )
    ):
        db_session.add(
            _definition(
                event_code=f"invalid.cross.vendor.{index}",
                **values,
            )
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    db_session.add(
        _definition(
            event_code="invalid.http.reference",
            official_reference_url="http://docs.example.test/event",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_vendor_event_definition_crud_round_trip(db_session):
    crud = _contract_module("crud.vendorEventDefinitionCrud")
    created = crud.create_definition(
        db_session,
        storage_type="netapp",
        event_code="nblade.execsOverLimit",
        association_type="performance_anomaly",
        title_zh="并发请求超过限制",
        description_zh="节点收到的并发请求超过允许上限。",
        official_reference_url="https://docs.netapp.com/test/events/nblade.execsOverLimit",
        recommended_solution_zh="检查并降低节点并发请求负载。",
    )
    db_session.commit()

    fetched = crud.get_definition(db_session, "netapp", "nblade.execsOverLimit")
    assert fetched.id == created.id
    assert fetched.recommended_solution_zh == "检查并降低节点并发请求负载。"
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


def test_pending_definition_is_not_used_as_reviewed_business_semantics(db_session):
    service = _contract_module("services.vendorEventDefinitionService")
    pending = _definition(
        event_code="candidate.fault",
        association_type="fault_log",
        title_zh="候选故障解释",
        description_zh="该解释仍待目标阵列运行时目录确认。",
        official_reference_url=None,
        version_scope=None,
        review_status="pending",
        recommended_solution_zh=None,
    )
    db_session.add(pending)
    db_session.commit()

    resolved = service.resolve_definition(db_session, "netapp", "candidate.fault")

    assert _field(resolved, "association_type") == "unknown"
    assert _field(resolved, "title_zh") == "未收录的厂商事件代码"
    assert db_session.get(_definition_model(), pending.id).title_zh == "候选故障解释"


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
    sis = crud.get_definition(db_session, "netapp", "sis.auto.session.change")
    assert sis.association_type == "system_activity"
    assert sis.default_severity == "warning"
    asup = crud.get_definition(db_session, "netapp", "asup.aods.response.timeOut")
    assert asup.version_scope == "ONTAP 9.11.1–9.18.1"
    powerscale_scopes = {
        code: crud.get_definition(db_session, "isilon", code).version_scope
        for code in ("400050004", "400100006", "500010001", "500010002")
    }
    assert all(scope is None for scope in powerscale_scopes.values())
    assert all(
        crud.get_definition(db_session, "isilon", code).review_status == "pending"
        and crud.get_definition(db_session, "isilon", code).association_type == "unknown"
        and crud.get_definition(db_session, "isilon", code).recommended_solution_zh is None
        for code in powerscale_scopes
    )
    assert all(
        row.recommended_solution_zh
        for row in first_rows
        if row.review_status == "reviewed"
    )


def test_runtime_seed_does_not_restore_pre_017_powerscale_semantics():
    migration = _contract_module(
        "migrate.versions.000000000016_vendor_event_definitions"
    )
    service = _contract_module("services.vendorEventDefinitionService")

    assert not hasattr(migration, "_COMMON_SEEDS")
    assert all(
        seed["association_type"] == "unknown"
        and seed["review_status"] == "pending"
        and seed["official_reference_url"] is None
        and seed["version_scope"] is None
        for seed in service.COMMON_DEFINITIONS
        if seed["storage_type"] == "isilon"
    )


def test_vendor_event_migration_leaves_history_discovery_to_the_admin_action():
    migration = _contract_module(
        "migrate.versions.000000000016_vendor_event_definitions"
    )

    assert not hasattr(migration, "_discovered_placeholder_rows")
    assert "_discovered_placeholder_rows" not in inspect.getsource(migration.upgrade)


def test_discover_preloads_catalog_in_constant_queries(db_session):
    service = _contract_module("services.vendorEventDefinitionService")
    db_session.add(models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"))
    for index in range(3):
        _add_vendor_alert(
            db_session,
            alert_id=801 + index,
            event_code=f"observed.batch.{index}",
            fingerprint=f"netapp:observed.batch.{index}:node:node-a",
            severity="warning",
            description=f"Observed event {index}",
        )
    db_session.commit()

    statements = []

    def capture_statement(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lower())

    sqlalchemy_event.listen(
        db_session.get_bind(),
        "before_cursor_execute",
        capture_statement,
    )
    try:
        result = service.discover(db_session)
    finally:
        sqlalchemy_event.remove(
            db_session.get_bind(),
            "before_cursor_execute",
            capture_statement,
        )

    catalog_selects = [
        statement
        for statement in statements
        if statement.lstrip().startswith("select")
        and "vendor_event_definitions" in statement
    ]
    observed_event_selects = [
        statement
        for statement in statements
        if statement.lstrip().startswith("select")
        and "storage_alerts" in statement
    ]
    assert len(catalog_selects) <= 2
    assert len(observed_event_selects) == 1
    assert "distinct" in observed_event_selects[0]
    assert result["created"] >= 3
    assert {
        definition.event_code
        for definition in db_session.query(_definition_model()).all()
    }.issuperset({f"observed.batch.{index}" for index in range(3)})


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
            recommended_solution_zh="检查节点负载并降低并发请求。",
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
    assert row["recommended_solution_zh"] == "检查节点负载并降低并发请求。"
    assert "raw-payload" not in json.dumps(result, ensure_ascii=False, default=str)
    assert "related_info" not in row


def test_system_event_page_loads_catalog_semantics_in_one_query(db_session):
    db_session.add(models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"))
    db_session.add_all(
        [
            _definition(
                event_code=f"disk.batch.{index}",
                title_zh=f"批量事件 {index}",
            )
            for index in range(3)
        ]
    )
    for index in range(3):
        _add_vendor_alert(
            db_session,
            alert_id=701 + index,
            event_code=f"disk.batch.{index}",
            fingerprint=f"netapp:disk.batch.{index}:node:node-a",
            severity="critical",
            description=f"Batch event {index}",
        )
    db_session.commit()

    statements = []

    def capture_statement(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lower())

    sqlalchemy_event.listen(
        db_session.get_bind(),
        "before_cursor_execute",
        capture_statement,
    )
    try:
        result = storageHealthAnalyticsService.get_system_events(
            db_session,
            1,
            START,
            END,
        )
    finally:
        sqlalchemy_event.remove(
            db_session.get_bind(),
            "before_cursor_execute",
            capture_statement,
        )

    catalog_selects = [
        statement
        for statement in statements
        if statement.lstrip().startswith("select")
        and "vendor_event_definitions" in statement
    ]
    assert len(catalog_selects) == 1
    assert {row["title_zh"] for row in result["data"]} == {
        "批量事件 0",
        "批量事件 1",
        "批量事件 2",
    }


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


def test_single_system_event_detail_returns_friendly_not_found_error(analytics_client):
    response = analytics_client.get(
        "/storage-pulse/api/storage-clusters/1/analytics/system-events/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "厂商系统事件不存在"


def test_single_system_event_detail_hides_events_from_other_clusters(
    analytics_client, db_session
):
    db_session.add(
        models.StorageCluster(
            id=2,
            name="cluster-b",
            storage_type="netapp",
            storage_host="storage-b.local",
            is_active=True,
        )
    )
    _add_vendor_alert(
        db_session,
        alert_id=502,
        event_code="vendor.other.cluster",
        fingerprint="netapp:vendor.other.cluster:node:node-z",
        severity="error",
        description="Belongs to cluster 1",
    )
    db_session.commit()

    response = analytics_client.get(
        "/storage-pulse/api/storage-clusters/2/analytics/system-events/502"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "厂商系统事件不存在"


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
            _definition(
                event_code="candidate.fault",
                association_type="fault_log",
                title_zh="候选故障解释",
                description_zh="该解释仍待目标阵列运行时目录确认。",
                official_reference_url=None,
                version_scope=None,
                review_status="pending",
            ),
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
    for alert_id in (5, 6):
        _add_vendor_alert(
            db_session,
            alert_id=alert_id,
            event_code="candidate.fault",
            fingerprint="netapp:candidate.fault:node:node-a",
            severity="critical",
            description="Unreviewed candidate event.",
        )
    db_session.commit()

    statements = []

    def capture_statement(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lower())

    sqlalchemy_event.listen(
        db_session.get_bind(),
        "before_cursor_execute",
        capture_statement,
    )
    try:
        result = storageHealthAnalyticsService.get_repeated_faults(
            db_session,
            1,
            START,
            END,
        )
    finally:
        sqlalchemy_event.remove(
            db_session.get_bind(),
            "before_cursor_execute",
            capture_statement,
        )

    assert len(result["data"]) == 1
    fault = result["data"][0]
    assert fault["event_code"] == "disk.offline"
    assert fault["association_type"] == "fault_log"
    assert fault["association_type_label"] == "故障日志"
    assert fault["title_zh"] == "磁盘离线"
    assert fault["count"] == 2
    catalog_selects = [
        statement
        for statement in statements
        if statement.lstrip().startswith("select")
        and "vendor_event_definitions" in statement
    ]
    vendor_event_selects = [
        statement
        for statement in statements
        if statement.lstrip().startswith("select")
        and "storage_alerts" in statement
    ]
    assert len(catalog_selects) == 1
    assert len(vendor_event_selects) == 2
