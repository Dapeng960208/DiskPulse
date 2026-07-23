# -*- coding: utf-8 -*-
import pytest
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace


UTC_NOW = datetime(2026, 7, 23, 6, 45, tzinfo=timezone.utc)


def _incident_ai_migration():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "migrate" / "versions" / "000000000021_incident_ai_agent.py"
    spec = importlib.util.spec_from_file_location("incident_ai_agent_migration", path)
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)
    return migration


def _incident(*, status="open"):
    import models

    return models.Incident(
        correlation_key="7:volume:9:performance_contention",
        correlation_bucket_at=UTC_NOW,
        asset_type="volume",
        asset_id="9",
        storage_cluster_id=None,
        project_id=None,
        vendor="netapp",
        display_name="volume-9",
        category="performance_contention",
        status=status,
        severity="warning",
        opened_at=UTC_NOW,
        last_evidence_at=UTC_NOW,
    )


def test_performance_incident_snapshot_includes_hourly_24h_metric_context(db_session, monkeypatch):
    from crud import storageHealthAnalyticsCrud
    from services import incidentAiAgentService

    incident = _incident()
    incident.storage_cluster_id = 7
    db_session.add(incident)
    db_session.commit()
    captured = {}

    def hourly_context(_db, *, storage_cluster_id, asset_type, asset_id, start_time, end_time):
        captured.update({
            "storage_cluster_id": storage_cluster_id,
            "asset_type": asset_type,
            "asset_id": asset_id,
            "start_time": start_time,
            "end_time": end_time,
        })
        return [{
            "hour_start": UTC_NOW - timedelta(hours=1),
            "sample_count": 6,
            "latency_read": 1.5,
            "latency_write": 2.5,
            "latency_total": 2.0,
            "iops_total": 240.0,
            "throughput_total": 4096.0,
        }]

    monkeypatch.setattr(
        storageHealthAnalyticsCrud,
        "get_hourly_asset_performance",
        hourly_context,
        raising=False,
    )

    snapshot = incidentAiAgentService._safe_snapshot(db_session, incident)

    context = snapshot["category_context"]
    assert captured == {
        "storage_cluster_id": 7,
        "asset_type": "volume",
        "asset_id": "9",
        "start_time": UTC_NOW - timedelta(hours=24),
        "end_time": UTC_NOW,
    }
    assert context["data_status"] == "data"
    assert context["window"] == {
        "start_at": "2026-07-22T06:45:00Z",
        "end_at": "2026-07-23T06:45:00Z",
        "timezone": "UTC",
    }
    assert context["hourly_metrics"] == [{
        "hour_start": "2026-07-23T05:45:00Z",
        "sample_count": 6,
        "latency_read": 1.5,
        "latency_write": 2.5,
        "latency_total": 2.0,
        "iops_total": 240.0,
        "throughput_total": 4096.0,
    }]
    assert context["metric_summary"]["latency_total"] == {
        "unit": "ms",
        "sample_count": 1,
        "min": 2.0,
        "max": 2.0,
        "average": 2.0,
    }


def test_performance_incident_snapshot_marks_missing_or_unavailable_metrics(db_session, monkeypatch):
    from crud import storageHealthAnalyticsCrud
    from services import incidentAiAgentService

    incident = _incident()
    incident.storage_cluster_id = 7
    db_session.add(incident)
    db_session.commit()
    monkeypatch.setattr(
        storageHealthAnalyticsCrud,
        "get_hourly_asset_performance",
        lambda *_args, **_kwargs: [],
        raising=False,
    )

    no_samples = incidentAiAgentService._safe_snapshot(db_session, incident)["category_context"]

    assert no_samples["data_status"] == "no_samples"
    assert no_samples["data_gaps"] == ["performance_metrics_unavailable"]

    def query_failure(*_args, **_kwargs):
        raise RuntimeError("QuestDB connection details must not reach the model")

    monkeypatch.setattr(
        storageHealthAnalyticsCrud,
        "get_hourly_asset_performance",
        query_failure,
    )
    unavailable = incidentAiAgentService._safe_snapshot(db_session, incident)["category_context"]

    assert unavailable["data_status"] == "unavailable"
    assert unavailable["data_gaps"] == ["performance_metrics_query_failed"]


def test_agent_prompt_requires_category_context_facts_and_disallows_unprovided_signals():
    from services.incidentAiAgentService import _messages

    prompt = _messages({"category_context": {}})[0]["content"]

    assert "category_context" in prompt
    assert "CPU" in prompt
    assert "进程" in prompt


def test_incident_output_exposes_the_latest_ai_review_state(db_session, monkeypatch):
    import models
    from routers import forecast_incidents
    from services import forecastIncidentService

    incident = _incident()
    db_session.add(incident)
    db_session.flush()
    db_session.add_all([
        models.IncidentAiRun(
            incident_id=incident.id,
            trigger="scheduled",
            idempotency_key="scheduled:1:1",
            status="succeeded",
            started_at=datetime(2026, 7, 23, 6, 30, tzinfo=timezone.utc),
            completed_at=datetime(2026, 7, 23, 6, 31, tzinfo=timezone.utc),
            input_snapshot={},
            attempt_summary=[],
        ),
        models.IncidentAiRun(
            incident_id=incident.id,
            trigger="lifecycle",
            idempotency_key="lifecycle:1:open:2026-07-23T06:45:00+00:00",
            status="running",
            started_at=datetime(2026, 7, 23, 6, 45, tzinfo=timezone.utc),
            input_snapshot={},
            attempt_summary=[],
        ),
    ])
    db_session.commit()
    monkeypatch.setattr(forecastIncidentService, "incident_capabilities", lambda *_args, **_kwargs: {})

    result = forecast_incidents._incident_out(db_session, SimpleNamespace(), incident)

    assert result.ai_review.status == "running"
    assert result.ai_review.trigger == "lifecycle"
    assert result.ai_review.started_at == datetime(2026, 7, 23, 6, 45, tzinfo=timezone.utc)


def test_incident_output_supports_legacy_ai_assessment_without_confidence(db_session, monkeypatch):
    from routers import forecast_incidents
    from services import forecastIncidentService

    incident = _incident()
    incident.ai_assessment = {
        "classification": "insufficient_evidence",
        "urgency": "low",
        "summary": "历史研判未记录置信度。",
        "analyzed_at": "2026-07-23T06:38:13.272112+00:00",
    }
    db_session.add(incident)
    db_session.commit()
    monkeypatch.setattr(forecastIncidentService, "incident_capabilities", lambda *_args, **_kwargs: {})

    result = forecast_incidents._incident_out(db_session, SimpleNamespace(), incident)

    assert result.ai_assessment.confidence == "low"
    assert result.ai_assessment.urgency_downgraded is False


def test_lifecycle_review_candidates_only_include_critical_incidents(db_session):
    from crud import incidentAiAgentCrud

    critical = _incident()
    critical.correlation_key = "critical-lifecycle"
    critical.severity = "critical"
    warning = _incident()
    warning.correlation_key = "warning-lifecycle"
    db_session.add_all([critical, warning])
    db_session.commit()

    candidates = incidentAiAgentCrud.list_lifecycle_review_candidates(
        db_session,
        incident_ids=[warning.id, critical.id],
        freshest_after=UTC_NOW - timedelta(minutes=60),
    )

    assert [item.id for item in candidates] == [critical.id]


def test_scheduled_review_candidates_prioritize_fresh_critical_items_and_cap_the_batch(db_session):
    from crud import incidentAiAgentCrud

    def add_incident(*, suffix, severity, evidence_at, analyzed_at=None):
        item = _incident()
        item.correlation_key = f"priority-{suffix}"
        item.severity = severity
        item.last_evidence_at = evidence_at
        item.ai_analyzed_at = analyzed_at
        db_session.add(item)
        return item

    critical_new = add_incident(suffix="critical-new", severity="critical", evidence_at=UTC_NOW)
    critical_updated = add_incident(
        suffix="critical-updated",
        severity="critical",
        evidence_at=UTC_NOW - timedelta(minutes=1),
        analyzed_at=UTC_NOW - timedelta(minutes=31),
    )
    warning_new = add_incident(suffix="warning-new", severity="warning", evidence_at=UTC_NOW - timedelta(minutes=2))
    stale = add_incident(suffix="stale", severity="critical", evidence_at=UTC_NOW - timedelta(minutes=61))
    fillers = [
        add_incident(suffix=f"critical-{index}", severity="critical", evidence_at=UTC_NOW - timedelta(minutes=index + 2))
        for index in range(4)
    ]
    db_session.commit()

    candidates = incidentAiAgentCrud.list_due_incidents(
        db_session,
        before=UTC_NOW - timedelta(minutes=30),
        freshest_after=UTC_NOW - timedelta(minutes=60),
        limit=5,
    )

    assert [item.id for item in candidates] == [
        critical_new.id,
        critical_updated.id,
        *[item.id for item in fillers[:3]],
    ]
    assert warning_new.id not in [item.id for item in candidates]
    assert stale.id not in [item.id for item in candidates]


def test_agent_assessment_rejects_status_skips_and_accepts_a_single_next_step():
    from services.incidentAiAgentService import IncidentAiAssessment, validate_agent_assessment

    accepted = validate_agent_assessment(
        IncidentAiAssessment(
            classification="normal_fluctuation",
            urgency="low",
            confidence="high",
            summary="低负载 IOPS 短时波动，暂无服务影响证据。",
            evidence_basis=["绝对 IOPS 低于动态噪声门槛"],
            investigation_steps=["继续观察下一采集周期"],
            resolution_steps=["无需设备写操作"],
            proposed_next_status="acknowledged",
            transition_reason="已完成初步研判。",
        ),
        current_status="open",
    )

    assert accepted.proposed_next_status == "acknowledged"
    with pytest.raises(ValueError, match="相邻"):
        validate_agent_assessment(
            accepted.model_copy(update={"proposed_next_status": "resolved"}),
            current_status="open",
        )


def test_low_confidence_downgrades_ai_urgency_without_changing_the_incident_severity():
    from services.incidentAiAgentService import (
        IncidentAiAssessment,
        calibrated_ai_urgency,
    )

    assessment = IncidentAiAssessment(
        classification="actionable",
        urgency="critical",
        confidence="low",
        summary="证据只覆盖单个短窗口。",
        evidence_basis=["缺少独立交叉证据"],
        investigation_steps=["继续核查"],
        resolution_steps=["确认后再处置"],
    )

    assert calibrated_ai_urgency(assessment) == ("high", True)
    assert assessment.urgency == "critical"


def test_legacy_ai_assessment_defaults_to_low_confidence_for_safe_api_compatibility():
    from schemas.forecastIncidentSchema import IncidentAiAssessmentOut

    assessment = IncidentAiAssessmentOut(
        classification="insufficient_evidence",
        urgency="high",
        summary="历史审查未记录置信度。",
    )

    assert assessment.confidence == "low"


def test_incident_ai_settings_accept_enabled_models_in_explicit_priority_order(db_session):
    import models
    from services.incidentAiAgentService import update_settings

    db_session.add_all([
        models.AIConfig(id=1, name="disabled", provider="openai", model="disabled", enabled=False, enable_chat=False),
        models.AIConfig(id=2, name="fallback", provider="openai", model="fallback", enabled=True, enable_chat=False),
        models.AIConfig(id=3, name="primary", provider="openai", model="primary", enabled=True, enable_chat=True),
    ])
    db_session.commit()

    settings = update_settings(
        db_session,
        actor_id=None,
        enabled=True,
        model_ids=[3, 2],
        iops_absolute_floor=10.0,
        iops_baseline_ratio=0.05,
    )

    assert settings.enabled is True
    assert [binding.ai_model_id for binding in settings.model_bindings] == [3, 2]
    with pytest.raises(HTTPException, match="已启用"):
        update_settings(
            db_session,
            actor_id=None,
            enabled=True,
            model_ids=[1],
            iops_absolute_floor=10.0,
            iops_baseline_ratio=0.05,
        )


def test_model_bound_to_incident_ai_settings_cannot_be_deleted(db_session):
    import models
    from services import ai_config_service
    from services.incidentAiAgentService import update_settings

    model = models.AIConfig(id=8, name="incident-agent", provider="openai", model="agent", enabled=True)
    db_session.add(model)
    db_session.commit()
    update_settings(
        db_session,
        actor_id=None,
        enabled=True,
        model_ids=[model.id],
        iops_absolute_floor=10.0,
        iops_baseline_ratio=0.05,
    )

    with pytest.raises(HTTPException, match="事件 AI") as error:
        ai_config_service.delete_model(db_session, model.id)

    assert error.value.status_code == 409
    assert db_session.get(models.AIConfig, model.id) is not None


def test_incident_ai_review_uses_ordered_fallback_and_persists_only_safe_context(db_session):
    import models
    from services import incidentAiAgentService

    primary = models.AIConfig(id=11, name="primary", provider="openai", model="primary", enabled=True)
    fallback = models.AIConfig(id=12, name="fallback", provider="openai", model="fallback", enabled=True)
    incident = _incident()
    db_session.add_all([primary, fallback, incident])
    db_session.commit()
    db_session.add(models.IncidentEvidence(
        incident_id=incident.id,
        source="anomaly_observation",
        source_ref="/private/path/vendor-log-with-secret",
        evidence_type="continuous_performance_anomaly",
        observed_at=UTC_NOW,
        evidence_hash="a" * 64,
    ))
    db_session.add(models.Diagnosis(
        incident_id=incident.id,
        algorithm_version="test",
        candidates=[{
            "category": "performance_contention",
            "score": 0.9,
            "evidence_refs": ["/private/path/vendor-log-with-secret"],
            "data_gaps": [],
        }],
        confidence="medium",
        evidence_ids=["/private/path/vendor-log-with-secret"],
        data_gaps=[],
        evidence_digest="b" * 64,
    ))
    db_session.add_all([
        models.IncidentEvidence(
            incident_id=incident.id,
            source="anomaly_observation",
            source_ref="anomaly:55",
            evidence_type="continuous_performance_anomaly",
            observed_at=UTC_NOW,
            evidence_hash="c" * 64,
        ),
        models.AnomalyObservation(
            id=55,
            asset_type="volume",
            asset_id="9",
            storage_cluster_id=None,
            project_id=None,
            vendor="netapp",
            display_name="volume-9",
            metric="iops",
            observed_at=UTC_NOW,
            observed_value=2.0,
            seasonal_baseline=0.0,
            mad=0.0,
            robust_z_score=4.0,
            severity="warning",
            evidence_window_start=UTC_NOW,
            evidence_window_end=UTC_NOW,
            source="questdb_performance",
            source_ref="performance:7:volume:9:iops:test",
            input_quality={"ai_performance_context": {
                "metric": "iops",
                "trigger_three_bucket_p95": [2.0, 2.0, 2.0],
                "trend_2h_p95": [{"minutes_before_trigger": 0, "p95": 2.0}],
                "history_28d": {"sample_count": 100, "coverage_ratio": 0.5, "median": 0.0, "p95": 2.0, "mad": 0.0},
                "associated_metrics": [],
            }},
            algorithm_version="test",
        ),
    ])
    db_session.commit()
    incidentAiAgentService.update_settings(
        db_session,
        actor_id=None,
        enabled=True,
        model_ids=[primary.id, fallback.id],
        iops_absolute_floor=10.0,
        iops_baseline_ratio=0.05,
    )
    calls = []

    def completion(model, messages, **_kwargs):
        calls.append(model.id)
        assert "/private/path" not in messages[-1]["content"]
        assert "secret" not in messages[-1]["content"]
        assert '"trigger_three_bucket_p95":[2.0,2.0,2.0]' in messages[-1]["content"]
        if model.id == primary.id:
            raise incidentAiAgentService.AIClientError("provider unavailable")
        return SimpleNamespace(text='''{
            "classification":"actionable", "urgency":"critical", "confidence":"low", "summary":"连续性能偏离，需要核查。",
            "investigation_steps":["核查关联指标"], "resolution_steps":["验证恢复趋势"],
            "proposed_next_status":"acknowledged", "transition_reason":"已完成初步研判"
        }''')

    run = incidentAiAgentService.review_incident(
        db_session,
        incident_id=incident.id,
        trigger="lifecycle",
        idempotency_key="review:1",
        completion=completion,
    )
    duplicate = incidentAiAgentService.review_incident(
        db_session,
        incident_id=incident.id,
        trigger="lifecycle",
        idempotency_key="review:1",
        completion=completion,
    )
    db_session.refresh(incident)

    assert calls == [primary.id, fallback.id]
    assert duplicate.id == run.id
    assert run.status == "succeeded"
    assert run.model_snapshot == {"name": "fallback", "provider": "openai", "model": "fallback"}
    assert "/private/path" not in str(run.input_snapshot)
    assert incident.severity == "warning"
    assert incident.ai_urgency == "high"
    assert run.assessment["confidence"] == "low"
    assert run.assessment["model_urgency"] == "critical"
    assert run.assessment["urgency_downgraded"] is True
    assert incident.status == "acknowledged"
    assert [item.event_type for item in db_session.query(models.IncidentTimeline).order_by(models.IncidentTimeline.id)] == [
        "ai_analysis", "ai_status_changed"
    ]


def test_invalid_agent_output_creates_no_comment_or_status_change(db_session):
    import models
    from services import incidentAiAgentService

    model = models.AIConfig(id=21, name="strict", provider="openai", model="strict", enabled=True)
    incident = _incident()
    db_session.add_all([model, incident])
    db_session.commit()
    incidentAiAgentService.update_settings(
        db_session,
        actor_id=None,
        enabled=True,
        model_ids=[model.id],
        iops_absolute_floor=10.0,
        iops_baseline_ratio=0.05,
    )

    run = incidentAiAgentService.review_incident(
        db_session,
        incident_id=incident.id,
        trigger="lifecycle",
        idempotency_key="invalid:1",
        completion=lambda *_args, **_kwargs: SimpleNamespace(text='{"classification":"actionable","unknown":true}'),
    )
    db_session.refresh(incident)

    assert run.status == "failed"
    assert run.error_code == "all_models_failed"
    assert incident.status == "open"
    assert incident.ai_assessment is None
    assert db_session.query(models.IncidentTimeline).count() == 0


def test_unexpected_model_failure_is_recorded_without_leaving_a_running_agent_run(db_session):
    import models
    from services import incidentAiAgentService

    model = models.AIConfig(id=22, name="broken", provider="openai", model="broken", enabled=True)
    incident = _incident()
    db_session.add_all([model, incident])
    db_session.commit()
    incidentAiAgentService.update_settings(
        db_session,
        actor_id=None,
        enabled=True,
        model_ids=[model.id],
        iops_absolute_floor=10.0,
        iops_baseline_ratio=0.05,
    )

    def broken_completion(*_args, **_kwargs):
        raise RuntimeError("provider internal detail must not be persisted")

    run = incidentAiAgentService.review_incident(
        db_session,
        incident_id=incident.id,
        trigger="lifecycle",
        idempotency_key="failure:1",
        completion=broken_completion,
    )

    assert run.status == "failed"
    assert run.error_code == "all_models_failed"
    assert run.attempt_summary == [{"model_id": model.id, "outcome": "failed"}]


def test_expired_evidence_snapshot_does_not_write_an_ai_comment_or_change_status(db_session):
    import models
    from services import incidentAiAgentService

    model = models.AIConfig(id=23, name="snapshot", provider="openai", model="snapshot", enabled=True)
    incident = _incident()
    db_session.add_all([model, incident])
    db_session.commit()
    incidentAiAgentService.update_settings(
        db_session,
        actor_id=None,
        enabled=True,
        model_ids=[model.id],
        iops_absolute_floor=10.0,
        iops_baseline_ratio=0.05,
    )

    def evidence_changes_during_completion(*_args, **_kwargs):
        db_session.get(models.Incident, incident.id).last_evidence_at = UTC_NOW.replace(minute=46)
        db_session.commit()
        return SimpleNamespace(text='''{
            "classification":"actionable", "urgency":"high", "confidence":"high", "summary":"旧快照中的异常。",
            "evidence_basis":["触发窗口"], "investigation_steps":["核查"], "resolution_steps":["验证"],
            "proposed_next_status":"acknowledged"
        }''')

    run = incidentAiAgentService.review_incident(
        db_session,
        incident_id=incident.id,
        trigger="lifecycle",
        idempotency_key="stale:1",
        completion=evidence_changes_during_completion,
    )
    db_session.refresh(incident)

    assert run.status == "superseded"
    assert incident.status == "open"
    assert incident.ai_assessment is None
    assert db_session.query(models.IncidentTimeline).count() == 0


def test_disabling_settings_during_completion_drops_the_generated_assessment(db_session):
    import models
    from services import incidentAiAgentService

    model = models.AIConfig(id=24, name="disable", provider="openai", model="disable", enabled=True)
    incident = _incident()
    db_session.add_all([model, incident])
    db_session.commit()
    incidentAiAgentService.update_settings(
        db_session,
        actor_id=None,
        enabled=True,
        model_ids=[model.id],
        iops_absolute_floor=10.0,
        iops_baseline_ratio=0.05,
    )

    def disable_during_completion(*_args, **_kwargs):
        settings = incidentAiAgentService.get_settings(db_session)
        settings.enabled = False
        db_session.commit()
        return SimpleNamespace(text='''{
            "classification":"actionable", "urgency":"high", "confidence":"high", "summary":"不应被写入。",
            "evidence_basis":["触发窗口"], "investigation_steps":["核查"], "resolution_steps":["验证"],
            "proposed_next_status":"acknowledged"
        }''')

    run = incidentAiAgentService.review_incident(
        db_session,
        incident_id=incident.id,
        trigger="lifecycle",
        idempotency_key="disabled:1",
        completion=disable_during_completion,
    )
    db_session.refresh(incident)

    assert run.status == "skipped"
    assert run.error_code == "disabled"
    assert incident.status == "open"
    assert incident.ai_assessment is None


def test_normal_fluctuation_advances_only_one_adjacent_status_per_review_until_resolved(db_session):
    import models
    from services import incidentAiAgentService

    model = models.AIConfig(id=31, name="normal", provider="openai", model="normal", enabled=True)
    incident = _incident()
    db_session.add_all([model, incident])
    db_session.commit()
    incidentAiAgentService.update_settings(
        db_session,
        actor_id=None,
        enabled=True,
        model_ids=[model.id],
        iops_absolute_floor=10.0,
        iops_baseline_ratio=0.05,
    )
    next_status = {"open": "acknowledged", "acknowledged": "investigating", "investigating": "mitigated", "mitigated": "resolved"}

    def completion(_model, messages, **_kwargs):
        current_status = __import__("json").loads(messages[-1]["content"])["status"]
        return SimpleNamespace(text=__import__("json").dumps({
            "classification": "normal_fluctuation",
            "urgency": "low",
            "confidence": "high",
            "summary": "低绝对负载的短时波动，无持续影响证据。",
            "evidence_basis": ["绝对负载低且仅连续三个短时窗口波动"],
            "investigation_steps": ["下一周期复核"],
            "resolution_steps": ["无需写操作"],
            "proposed_next_status": next_status[current_status],
            "transition_reason": "继续按相邻状态机自动推进",
        }))

    for index, expected_status in enumerate(next_status.values(), start=1):
        run = incidentAiAgentService.review_incident(
            db_session,
            incident_id=incident.id,
            trigger="scheduled",
            idempotency_key=f"scheduled:{index}",
            completion=completion,
        )
        db_session.refresh(incident)
        assert run.status == "succeeded"
        assert incident.status == expected_status

    assert incident.resolved_at is not None


def test_incident_ai_settings_api_is_super_admin_only_and_returns_selected_models(db_session, api_client_factory):
    import models
    from appConfig import base_config
    from routers import forecast_incidents
    from utils.security import issue_token

    base_config.set("super_admin_usernames", ["incident-admin"])
    db_session.add_all([
        models.User(id=41, rd_username="incident-reader"),
        models.User(id=42, rd_username="incident-admin"),
        models.AIConfig(id=43, name="available", provider="openai", model="available", enabled=True),
    ])
    db_session.commit()
    reader = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(41)}"},
    )
    admin = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(42)}"},
    )

    assert reader.get("/storage-pulse/api/v1/admin/incident-ai-settings").status_code == 403
    assert admin.get("/storage-pulse/api/v1/admin/incident-ai-settings").json()["enabled"] is False
    response = admin.patch(
        "/storage-pulse/api/v1/admin/incident-ai-settings",
        json={
            "enabled": True,
            "model_ids": [43],
            "iops_absolute_floor": 10,
            "iops_baseline_ratio": 0.05,
        },
    )

    assert response.status_code == 200
    assert response.json()["model_ids"] == [43]
    assert response.json()["available_models"] == [{
        "id": 43, "name": "available", "provider": "openai", "model": "available"
    }]


def test_incident_ai_migration_compiles_for_supported_dialects():
    import io
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    for dialect_name in ("sqlite", "postgresql", "mysql"):
        migration = _incident_ai_migration()
        output = io.StringIO()
        migration.op = Operations(
            MigrationContext.configure(
                dialect_name=dialect_name,
                opts={"as_sql": True, "output_buffer": output},
            )
        )
        migration.upgrade()
        sql = output.getvalue().lower()
        assert all(table in sql for table in ("incident_ai_settings", "incident_ai_model_bindings", "incident_ai_runs"))
