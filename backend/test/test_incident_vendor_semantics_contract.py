# -*- coding: utf-8 -*-
import importlib
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import event

import models
from routers import forecast_incidents
from utils.security import issue_token


NOW = datetime(2026, 7, 21, 1, 30, tzinfo=timezone.utc)


def _contract_module(name: str):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        pytest.fail(f"缺少约定模块 {name}: {error}")


def _field(value, name: str):
    return value.get(name) if isinstance(value, dict) else getattr(value, name)


def _definition_model():
    model = getattr(models, "VendorEventDefinition", None)
    assert model is not None, "models.VendorEventDefinition 尚未实现"
    return model


def _incident(*, incident_id: int, correlation_key: str):
    return models.Incident(
        id=incident_id,
        correlation_key=correlation_key,
        correlation_bucket_at=NOW,
        asset_type="storage_node",
        asset_id=f"node-{incident_id}",
        storage_cluster_id=7,
        project_id=1,
        vendor="netapp",
        display_name=f"node-{incident_id}",
        category="device_fault",
        severity="warning",
        status="open",
        opened_at=NOW,
        last_evidence_at=NOW,
    )


def _alert(
    *,
    alert_id: int,
    external_event_id: str,
    severity: str,
    event_code: str,
    source: str = "netapp",
):
    return models.StorageAlerts(
        id=alert_id,
        storage_cluster_id=7,
        source=source,
        external_event_id=external_event_id,
        fingerprint=f"{source}:{event_code}:node:node-{alert_id}",
        severity=severity,
        alert_level=severity,
        alert_type="vendor_event",
        description=f"normalized log {external_event_id}",
        related_type="node",
        related_info={
            "event_code": event_code,
            "object_id": f"node-{alert_id}",
            "raw": {"secret": f"raw-secret-{alert_id}"},
        },
        updated_at=NOW,
    )


def _evidence(
    *,
    incident_id: int,
    external_event_id: str,
    evidence_hash: str,
    source_ref: str | None = None,
):
    return models.IncidentEvidence(
        incident_id=incident_id,
        source="storage_alert",
        source_ref=source_ref or f"netapp:{external_event_id}",
        evidence_type="severe_vendor_event",
        observed_at=NOW,
        data_gaps=["asset_mapping_missing"],
        evidence_hash=evidence_hash,
    )


def test_incident_and_ai_diagnosis_expose_chinese_gap_and_safe_vendor_evidence_summaries(
    db_session, api_client_factory
):
    db_session.add_all(
        [
            models.User(id=2, rd_username="reader"),
            models.Project(id=1, name="project-alpha"),
            models.ProjectMembership(project_id=1, user_id=2, role="reader"),
            models.StorageCluster(id=7, name="cluster-7", storage_type="netapp"),
            _definition_model()(
                storage_type="netapp",
                event_code="disk.offline",
                association_type="fault_log",
                title_zh="磁盘离线",
                description_zh="存储节点报告磁盘已离线。",
                official_reference_url="https://docs.netapp.com/test/events/disk.offline",
                version_scope="ONTAP test fixture",
                review_status="reviewed",
            ),
            _incident(incident_id=1, correlation_key="legacy:netapp:disk.offline"),
            _alert(
                alert_id=900,
                external_event_id="event-900",
                severity="critical",
                event_code="disk.offline",
            ),
            _evidence(incident_id=1, external_event_id="event-900", evidence_hash="a" * 64),
            models.Diagnosis(
                incident_id=1,
                algorithm_version="forecast-incident-v1",
                candidates=[
                    {
                        "category": "device_fault",
                        "score": 0.8,
                        "evidence_refs": ["netapp:event-900"],
                        "data_gaps": ["asset_mapping_missing"],
                    }
                ],
                confidence="medium",
                evidence_ids=["netapp:event-900"],
                data_gaps=["asset_mapping_missing"],
                evidence_digest="b" * 64,
            ),
        ]
    )
    db_session.commit()
    client = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(2)}"},
    )

    detail_response = client.get("/storage-pulse/api/v1/incidents/1")
    tool_response = client.get("/storage-pulse/api/v1/incidents/1/diagnosis")

    assert detail_response.status_code == 200
    assert tool_response.status_code == 200
    detail = detail_response.json()
    tool = tool_response.json()
    gap = detail["evidence"][0]["data_gap_details"][0]
    assert gap["code"] == "asset_mapping_missing"
    assert gap["label"] == "资产映射不完整"
    assert gap["description"] == (
        "事件至少已归属存储集群，但节点、卷、Qtree 或项目的稳定映射链路不完整；"
        "已识别稳定节点身份的厂商事件不会产生此缺口。"
    )
    assert gap["impact"] == "不影响查看已规范化的厂商事件日志正文。"
    evidence_summary = detail["evidence"][0]["evidence_summary"]
    assert evidence_summary == {
        "source_ref": "netapp:event-900",
        "event_code": "disk.offline",
        "association_type": "fault_log",
        "association_type_label": "故障日志",
        "title_zh": "磁盘离线",
        "severity": "critical",
    }
    assert detail["diagnosis"]["data_gap_details"] == [gap]
    assert detail["diagnosis"]["evidence_summaries"] == [evidence_summary]
    presentation = detail["evidence"][0]["presentation"]
    assert presentation["group_label"] == "厂商系统事件"
    assert presentation["association_type_label"] == "故障日志"
    assert presentation["log_excerpt"] == "normalized log event-900"
    assert tool["data_gap_details"] == [gap]
    assert tool["evidence_summaries"] == [evidence_summary]
    serialized = json.dumps({"detail": detail, "tool": tool}, ensure_ascii=False)
    assert "raw-secret-900" not in serialized
    assert "related_info" not in serialized


def test_incident_detail_batches_vendor_alerts_and_reviewed_semantics_without_leaking_raw(
    db_session, db_engine, api_client_factory
):
    db_session.add_all(
        [
            models.User(id=2, rd_username="reader"),
            models.Project(id=1, name="project-alpha"),
            models.ProjectMembership(project_id=1, user_id=2, role="reader"),
            models.StorageCluster(id=7, name="cluster-7", storage_type="netapp"),
            _definition_model()(
                storage_type="netapp",
                event_code="disk.offline",
                association_type="fault_log",
                title_zh="磁盘离线",
                description_zh="存储节点报告磁盘已离线。",
                official_reference_url="https://docs.netapp.com/test/events/disk.offline",
                version_scope="ONTAP test fixture",
                review_status="reviewed",
            ),
            _definition_model()(
                storage_type="netapp",
                event_code="nblade.pending",
                association_type="performance_anomaly",
                title_zh="待审核性能候选",
                description_zh="该候选语义不能进入用户可见详情。",
                review_status="pending",
            ),
            _definition_model()(
                storage_type="isilon",
                event_code="100000001",
                association_type="fault_log",
                title_zh="已停用故障候选",
                description_zh="该停用语义不能进入用户可见详情。",
                official_reference_url="https://infohub.delltechnologies.com/test/events/100000001",
                version_scope="OneFS test fixture",
                review_status="reviewed",
                is_active=False,
            ),
            _incident(incident_id=3, correlation_key="batch:vendor:evidence"),
            _alert(
                alert_id=910,
                external_event_id="event-910",
                severity="critical",
                event_code="disk.offline",
            ),
            _alert(
                alert_id=911,
                external_event_id="legacy-911",
                severity="warning",
                event_code="nblade.pending",
            ),
            _alert(
                alert_id=912,
                external_event_id="event-912",
                severity="critical",
                event_code="100000001",
                source="isilon",
            ),
            _evidence(
                incident_id=3,
                external_event_id="event-910",
                evidence_hash="c" * 64,
                source_ref="storage_alert:910",
            ),
            _evidence(
                incident_id=3,
                external_event_id="legacy-911",
                evidence_hash="d" * 64,
            ),
            _evidence(
                incident_id=3,
                external_event_id="event-912",
                evidence_hash="e" * 64,
                source_ref="storage_alert:912",
            ),
            models.Diagnosis(
                incident_id=3,
                algorithm_version="forecast-incident-v1",
                candidates=[],
                confidence="medium",
                evidence_ids=[
                    "storage_alert:910",
                    "netapp:legacy-911",
                    "storage_alert:912",
                ],
                data_gaps=[],
                evidence_digest="f" * 64,
            ),
        ]
    )
    db_session.commit()
    client = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(2)}"},
    )
    vendor_queries = {"storage_alerts": 0, "vendor_event_definitions": 0}

    def count_vendor_queries(_conn, _cursor, statement, _parameters, _context, _many):
        normalized = statement.lower()
        for table_name in vendor_queries:
            if table_name in normalized:
                vendor_queries[table_name] += 1

    event.listen(db_engine, "before_cursor_execute", count_vendor_queries)
    try:
        response = client.get("/storage-pulse/api/v1/incidents/3")
    finally:
        event.remove(db_engine, "before_cursor_execute", count_vendor_queries)

    assert response.status_code == 200
    body = response.json()
    evidence_by_ref = {item["source_ref"]: item for item in body["evidence"]}
    reviewed = evidence_by_ref["storage_alert:910"]
    pending = evidence_by_ref["netapp:legacy-911"]
    disabled = evidence_by_ref["storage_alert:912"]
    assert reviewed["evidence_summary"]["title_zh"] == "磁盘离线"
    assert reviewed["evidence_summary"]["association_type"] == "fault_log"
    assert pending["evidence_summary"]["title_zh"] == "未收录的厂商事件代码"
    assert pending["evidence_summary"]["association_type"] == "unknown"
    assert disabled["evidence_summary"]["title_zh"] == "未收录的厂商事件代码"
    assert disabled["evidence_summary"]["association_type"] == "unknown"
    assert pending["presentation"]["log_excerpt"] == "normalized log legacy-911"
    assert disabled["presentation"]["log_excerpt"] == "normalized log event-912"
    assert {
        item["source_ref"]: item for item in body["diagnosis"]["evidence_summaries"]
    } == {
        source_ref: item["evidence_summary"]
        for source_ref, item in evidence_by_ref.items()
    }
    serialized = json.dumps(body, ensure_ascii=False)
    assert "raw-secret-910" not in serialized
    assert "raw-secret-911" not in serialized
    assert "raw-secret-912" not in serialized
    assert "related_info" not in serialized
    assert vendor_queries == {"storage_alerts": 1, "vendor_event_definitions": 1}


def test_legacy_noncritical_vendor_fault_reconciliation_is_dry_run_safe_and_idempotent(
    db_session,
):
    service = _contract_module("services.incidentReconciliationService")
    db_session.add_all(
        [
            models.StorageCluster(id=7, name="cluster-7", storage_type="netapp"),
            _incident(incident_id=1, correlation_key="legacy:noncritical"),
            _incident(incident_id=2, correlation_key="legacy:critical"),
            _alert(
                alert_id=101,
                external_event_id="info-101",
                severity="info",
                event_code="wafl.vol.blks_used.done",
            ),
            _alert(
                alert_id=102,
                external_event_id="warning-102",
                severity="warning",
                event_code="nblade.execsOverLimit",
            ),
            _alert(
                alert_id=201,
                external_event_id="critical-201",
                severity="critical",
                event_code="disk.offline",
            ),
            _evidence(incident_id=1, external_event_id="info-101", evidence_hash="1" * 64),
            _evidence(incident_id=1, external_event_id="warning-102", evidence_hash="2" * 64),
            _evidence(incident_id=2, external_event_id="critical-201", evidence_hash="3" * 64),
            models.Diagnosis(
                incident_id=1,
                algorithm_version="legacy-v1",
                candidates=[],
                confidence="insufficient",
                evidence_ids=["netapp:info-101", "netapp:warning-102"],
                data_gaps=["asset_mapping_missing"],
                evidence_digest="4" * 64,
            ),
        ]
    )
    db_session.commit()
    original_counts = {
        "alerts": db_session.query(models.StorageAlerts).count(),
        "evidence": db_session.query(models.IncidentEvidence).count(),
        "diagnoses": db_session.query(models.Diagnosis).count(),
    }

    statements = []

    def capture_statement(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lower())

    event.listen(db_session.get_bind(), "before_cursor_execute", capture_statement)
    try:
        preview = service.reconcile_legacy_vendor_incidents(
            db_session,
            dry_run=True,
            now=NOW,
        )
    finally:
        event.remove(db_session.get_bind(), "before_cursor_execute", capture_statement)

    assert _field(preview, "scanned") == 2
    assert _field(preview, "would_close") == 1
    assert _field(preview, "closed") == 0
    assert db_session.get(models.Incident, 1).status == "open"
    assert db_session.query(models.IncidentTimeline).count() == 0
    reconciliation_selects = {
        table: sum(
            1
            for statement in statements
            if statement.lstrip().startswith("select") and table in statement
        )
        for table in ("incident_evidence", "storage_alerts")
    }
    assert reconciliation_selects == {
        "incident_evidence": 1,
        "storage_alerts": 1,
    }

    applied = service.reconcile_legacy_vendor_incidents(db_session, dry_run=False, now=NOW)
    db_session.flush()

    assert _field(applied, "closed") == 1
    assert db_session.get(models.Incident, 1).status == "resolved"
    assert db_session.get(models.Incident, 1).resolved_at == NOW
    assert db_session.get(models.Incident, 2).status == "open"
    assert db_session.query(models.IncidentTimeline).filter_by(
        incident_id=1, event_type="reconciled"
    ).count() == 1
    assert {
        "alerts": db_session.query(models.StorageAlerts).count(),
        "evidence": db_session.query(models.IncidentEvidence).count(),
        "diagnoses": db_session.query(models.Diagnosis).count(),
    } == original_counts

    repeated = service.reconcile_legacy_vendor_incidents(db_session, dry_run=False, now=NOW)
    db_session.flush()

    assert _field(repeated, "closed") == 0
    assert db_session.query(models.IncidentTimeline).filter_by(
        incident_id=1, event_type="reconciled"
    ).count() == 1
