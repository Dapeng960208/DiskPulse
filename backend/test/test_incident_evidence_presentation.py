# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest


UTC_NOW = datetime(2026, 7, 20, 6, 15, tzinfo=timezone.utc)


def test_telemetry_quality_evidence_has_a_readable_presentation_without_exposing_its_internal_key():
    from services import forecastIncidentService as analytics

    evidence = SimpleNamespace(
        source="telemetry_quality",
        source_ref="quality:7:performance:2026-07-20T06:15:00+00:00:telemetry_stale",
        evidence_type="telemetry_stale",
        observed_at=UTC_NOW,
        data_gaps=[],
    )

    presentation = analytics.build_evidence_presentation(evidence)

    assert presentation["group_key"] == "telemetry_quality"
    assert presentation["group_label"] == "监控可用性异常"
    assert presentation["title"] == "性能采集已过期"
    assert presentation["scope_label"] == "性能采集"
    assert presentation["summary"] == "性能采集自 2026-07-20 06:15 起未产生新的成功采集记录。"
    assert presentation["technical_ref"] == evidence.source_ref


def test_performance_anomaly_evidence_has_an_explicit_theme_and_actual_association_content():
    from services import forecastIncidentService as analytics

    evidence = SimpleNamespace(
        source="anomaly_observation",
        source_ref="anomaly:1204",
        evidence_type="continuous_performance_anomaly",
        observed_at=UTC_NOW,
        data_gaps=[],
    )

    presentation = analytics.build_evidence_presentation(evidence)

    assert presentation["group_key"] == "anomaly_observation"
    assert presentation["group_label"] == "性能异常"
    assert presentation["title"] == "持续性能异常"
    assert presentation["scope_label"] == "性能指标"
    assert presentation["summary"] == "性能指标持续偏离历史基线，请核查延迟、IOPS、吞吐量及同期负载。"
    assert presentation["technical_ref"] == evidence.source_ref


def test_incident_detail_api_resolves_performance_anomaly_measurements_and_lookup_guidance(
    db_session, api_client_factory
):
    import models
    from routers import forecast_incidents
    from utils.security import issue_token

    window_start = datetime(2026, 7, 23, 9, 35, tzinfo=timezone.utc)
    window_end = datetime(2026, 7, 23, 9, 45, tzinfo=timezone.utc)
    db_session.add_all(
        [
            models.User(id=2, rd_username="reader"),
            models.Project(id=1, name="project-alpha"),
            models.ProjectMembership(project_id=1, user_id=2, role="reader"),
            models.StorageCluster(id=7, name="cluster-7", storage_type="netapp"),
            models.AnomalyObservation(
                id=1204,
                asset_type="volume",
                asset_id="volume-a",
                storage_cluster_id=7,
                project_id=1,
                vendor="netapp",
                display_name="volume-a",
                metric="latency",
                observed_at=window_end,
                observed_value=24.5,
                seasonal_baseline=10.0,
                mad=2.0,
                robust_z_score=4.89,
                severity="critical",
                evidence_window_start=window_start,
                evidence_window_end=window_end,
                source="questdb_performance",
                source_ref="performance:7:volume:volume-a:latency:2026-07-23T09:45:00+00:00",
                input_quality={},
                algorithm_version="forecast-incident-v1",
            ),
            models.Incident(
                id=9,
                correlation_key="cluster-7:volume:volume-a:performance_contention",
                correlation_bucket_at=window_start,
                asset_type="volume",
                asset_id="volume-a",
                storage_cluster_id=7,
                project_id=1,
                vendor="netapp",
                display_name="volume-a",
                category="performance_contention",
                opened_at=window_start,
                last_evidence_at=window_end,
            ),
            models.IncidentEvidence(
                incident_id=9,
                source="anomaly_observation",
                source_ref="anomaly:1204",
                evidence_type="continuous_performance_anomaly",
                observed_at=window_end,
                data_gaps=[],
                evidence_hash="b" * 64,
            ),
        ]
    )
    db_session.commit()

    client = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(2)}"},
    )
    response = client.get("/storage-pulse/api/v1/incidents/9")

    assert response.status_code == 200
    presentation = response.json()["evidence"][0]["presentation"]
    assert presentation["metric_key"] == "latency"
    assert presentation["metric_label"] == "P95 总延迟"
    assert presentation["metric_unit"] == "ms"
    assert presentation["window_start"] == "2026-07-23T09:35:00Z"
    assert presentation["window_end"] == "2026-07-23T09:45:00Z"
    assert presentation["observed_value"] == 24.5
    assert presentation["baseline_value"] == 10.0
    assert presentation["reference_lower"] == pytest.approx(0.0)
    assert presentation["reference_upper"] == pytest.approx(
        10.0 + 3.5 * 2.0 / 0.67448975
    )
    assert presentation["robust_z_score"] == 4.89
    assert presentation["summary"] == (
        "P95 总延迟连续三个相邻 5 分钟窗口超出基于过去 28 天"
        "同星期同小时历史样本计算的正常参考范围。"
    )
    assert presentation["reference_purpose"] == (
        "该标识用于把事件证据与原始异常观测精确关联，支持去重、审计和回放；它本身不是异常结论。"
    )
    assert "异常观测 ID 1204" in presentation["lookup_hint"]
    assert "metric=latency" in presentation["lookup_hint"]


def test_timeline_presentation_uses_chinese_actions_and_a_system_actor_for_automatic_records():
    from services import forecastIncidentService as analytics

    created = analytics.build_timeline_presentation(
        SimpleNamespace(event_type="created", comment=None),
        actor_label=None,
    )
    evidence_added = analytics.build_timeline_presentation(
        SimpleNamespace(event_type="evidence_added", comment="关联性能采集已过期：性能采集自 2026-07-20 06:15 起未产生新的成功采集记录。"),
        actor_label=None,
    )

    assert created == {
        "action_label": "系统创建事件",
        "summary": "系统根据关联证据创建了该事件。",
        "actor_label": "系统",
    }
    assert evidence_added["action_label"] == "关联新证据"
    assert evidence_added["summary"] == "关联性能采集已过期：性能采集自 2026-07-20 06:15 起未产生新的成功采集记录。"
    assert evidence_added["actor_label"] == "系统"


def test_incident_detail_api_returns_readable_evidence_and_timeline_presentations(
    db_session, api_client_factory
):
    import models
    from routers import forecast_incidents
    from utils.security import issue_token

    db_session.add_all(
        [
            models.User(id=2, rd_username="reader"),
            models.Project(id=1, name="project-alpha"),
            models.ProjectMembership(project_id=1, user_id=2, role="reader"),
            models.StorageCluster(id=7, name="cluster-7", storage_type="netapp"),
            models.Incident(
                id=1,
                correlation_key="cluster-7:cluster:7:telemetry_blindspot",
                correlation_bucket_at=UTC_NOW,
                asset_type="cluster",
                asset_id="7",
                storage_cluster_id=7,
                project_id=1,
                vendor="netapp",
                display_name="cluster-7",
                category="telemetry_blindspot",
                opened_at=UTC_NOW,
                last_evidence_at=UTC_NOW,
            ),
            models.IncidentEvidence(
                incident_id=1,
                source="telemetry_quality",
                source_ref="quality:7:performance:2026-07-20T06:15:00+00:00:telemetry_stale",
                evidence_type="telemetry_stale",
                observed_at=UTC_NOW,
                data_gaps=[],
                evidence_hash="a" * 64,
            ),
            models.IncidentTimeline(
                id=2,
                incident_id=1,
                event_type="evidence_added",
                occurred_at=UTC_NOW.replace(minute=30),
                comment="关联性能采集已过期。",
            ),
            models.IncidentTimeline(
                id=1,
                incident_id=1,
                event_type="created",
                occurred_at=UTC_NOW,
            ),
        ]
    )
    db_session.commit()

    client = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(2)}"},
    )
    response = client.get("/storage-pulse/api/v1/incidents/1")

    assert response.status_code == 200
    body = response.json()
    assert body["evidence"][0]["presentation"]["title"] == "性能采集已过期"
    assert body["evidence"][0]["presentation"]["summary"] == "性能采集自 2026-07-20 06:15 起未产生新的成功采集记录。"
    assert [item["id"] for item in body["timeline"]] == [2, 1]
    assert body["timeline"][1]["presentation"]["action_label"] == "系统创建事件"
