# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from types import SimpleNamespace


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
    assert body["timeline"][0]["presentation"]["action_label"] == "系统创建事件"
