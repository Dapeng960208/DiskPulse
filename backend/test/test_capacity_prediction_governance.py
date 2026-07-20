# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


UTC_NOW = datetime(2026, 7, 18, 8, 0, tzinfo=timezone.utc)


def _curve(start: datetime, *, offset: float = 0.0) -> list[dict]:
    return [
        {
            "observed_at": (start + timedelta(days=day)).isoformat(),
            "p10": 10.0 + day + offset,
            "p50": 12.0 + day + offset,
            "p90": 14.0 + day + offset,
        }
        for day in range(1, 31)
    ]


def test_ai_curve_requires_exactly_30_ordered_nonnegative_quantiles():
    from services.capacityPredictionGovernanceService import validate_ai_prediction_curve

    validated = validate_ai_prediction_curve(_curve(UTC_NOW), forecast_start=UTC_NOW)

    assert len(validated) == 30
    assert validated[0]["p10"] <= validated[0]["p50"] <= validated[0]["p90"]

    invalid = _curve(UTC_NOW)
    invalid[3]["p10"] = 99.0
    with pytest.raises(ValueError, match="quantile"):
        validate_ai_prediction_curve(invalid, forecast_start=UTC_NOW)

    non_finite = _curve(UTC_NOW)
    non_finite[3]["p10"] = float("inf")
    non_finite[3]["p50"] = float("inf")
    non_finite[3]["p90"] = float("inf")
    with pytest.raises(ValueError, match="finite"):
        validate_ai_prediction_curve(non_finite, forecast_start=UTC_NOW)


def test_ai_candidate_uses_only_aggregate_input_and_falls_back_to_baseline_on_invalid_output():
    from services.capacityPredictionGovernanceService import generate_candidate_curve_with_fallback

    calls = []

    def invalid_completion(_model, messages, *, tools):
        calls.append((messages, tools))
        return SimpleNamespace(text="not-json")

    baseline = _curve(UTC_NOW)
    result = generate_candidate_curve_with_fallback(
        model=SimpleNamespace(),
        asset_type="storage_usage",
        points=[(UTC_NOW - timedelta(days=1), 42.0)],
        hard_limit=100.0,
        approved_plans=[{"effective_at": UTC_NOW.isoformat(), "capacity_delta": 8.0}],
        quality_summary={"sample_count": 42, "coverage_ratio": 0.93, "status": "ready"},
        forecast_start=UTC_NOW,
        baseline_curve=baseline,
        completion=invalid_completion,
    )

    assert result.source == "baseline_fallback"
    assert result.curve == baseline
    assert result.fallback_reason == "invalid_output"
    serialized = str(calls[0][0])
    assert "storage_usage" in serialized
    assert "42.0" in serialized
    assert "sample_count" in serialized
    assert "coverage_ratio" in serialized
    assert "linux_path" not in serialized
    assert calls[0][1] == []


def test_ai_candidate_accepts_a_valid_30_day_prediction_curve():
    from services.capacityPredictionGovernanceService import generate_candidate_curve_with_fallback

    result = generate_candidate_curve_with_fallback(
        model=SimpleNamespace(),
        asset_type="group",
        points=[(UTC_NOW - timedelta(days=1), 42.0)],
        hard_limit=100.0,
        approved_plans=[],
        quality_summary={"sample_count": 45, "coverage_ratio": 1.0, "status": "ready"},
        forecast_start=UTC_NOW,
        baseline_curve=_curve(UTC_NOW),
        completion=lambda *_args, **_kwargs: SimpleNamespace(text='{"curve": ' + str(_curve(UTC_NOW)).replace("'", '"') + '}'),
    )

    assert result.source == "ai_candidate"
    assert result.fallback_reason is None
    assert len(result.curve) == 30


def test_ai_candidate_timeout_uses_baseline_with_timeout_provenance():
    from services.ai_client import AIClientError
    from services.capacityPredictionGovernanceService import generate_candidate_curve_with_fallback

    def timeout_completion(*_args, **_kwargs):
        raise AIClientError("AI 服务请求超时")

    result = generate_candidate_curve_with_fallback(
        model=SimpleNamespace(),
        asset_type="group",
        points=[(UTC_NOW - timedelta(days=1), 42.0)],
        hard_limit=100.0,
        approved_plans=[],
        quality_summary={"sample_count": 1, "coverage_ratio": 0.1, "status": "insufficient"},
        forecast_start=UTC_NOW,
        baseline_curve=_curve(UTC_NOW),
        completion=timeout_completion,
    )

    assert result.source == "baseline_fallback"
    assert result.fallback_reason == "timeout"


def test_candidate_builds_three_rolling_30_day_holdout_evaluations_without_resource_identity():
    from services.capacityPredictionGovernanceService import rolling_candidate_evaluations
    from services.forecastIncidentService import AssetRef

    calls = []

    def completion(_model, messages, *, tools):
        calls.append(messages)
        payload = __import__("json").loads(messages[1]["content"])
        forecast_start = datetime.fromisoformat(payload["forecast_start"]).replace(tzinfo=timezone.utc)
        return SimpleNamespace(text=__import__("json").dumps({"curve": _curve(forecast_start)}))

    points = [(UTC_NOW - timedelta(days=135 - day), 100.0 + day) for day in range(135)]
    evaluations = rolling_candidate_evaluations(
        model=SimpleNamespace(),
        asset_ref=AssetRef(
            asset_type="group",
            asset_id="1",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="group-alpha",
        ),
        points=points,
        hard_limit=10_000.0,
        approved_plans=[],
        quality_summary={"sample_count": 135, "coverage_ratio": 1.0, "status": "ready"},
        completion=completion,
    )

    assert len(evaluations) == 3
    assert all(row["window_end"] - row["window_start"] == timedelta(days=30) for row in evaluations)
    assert all("linux_path" not in str(messages) for messages in calls)


def test_candidate_prediction_persists_curve_and_fallback_provenance(db_session):
    import models
    from services.capacityPredictionGovernanceService import (
        CandidateCurveResult,
        persist_candidate_prediction,
    )

    db_session.add(models.AIConfig(
        id=1,
        name="forecast-private-model",
        provider="ollama",
        base_url="http://forecast.internal",
        model="forecast-model",
        enabled=True,
        enable_chat=False,
    ))
    db_session.commit()
    candidate = models.CapacityPredictionCandidate(version="capacity-ai-v1", ai_model_id=1)
    db_session.add(candidate)
    db_session.commit()

    record = persist_candidate_prediction(
        db_session,
        candidate_id=candidate.id,
        asset_type="group",
        asset_id=7,
        project_id=4,
        forecast_start=UTC_NOW,
        baseline_curve=_curve(UTC_NOW),
        result=CandidateCurveResult(
            curve=_curve(UTC_NOW),
            source="baseline_fallback",
            fallback_reason="invalid_output",
        ),
    )

    assert record.candidate_id == candidate.id
    assert record.source == "baseline_fallback"
    assert record.fallback_reason == "invalid_output"
    assert record.asset_id == "7"


def test_candidate_fallback_is_recorded_in_the_unified_audit_log(db_session):
    import models
    from services.capacityPredictionGovernanceService import (
        CandidateCurveResult,
        persist_candidate_prediction,
    )

    db_session.add(models.AIConfig(
        id=1,
        name="forecast-private-model",
        provider="ollama",
        base_url="http://forecast.internal",
        model="forecast-model",
        enabled=True,
        enable_chat=False,
    ))
    db_session.commit()
    candidate = models.CapacityPredictionCandidate(version="capacity-ai-v1", ai_model_id=1)
    db_session.add(candidate)
    db_session.commit()

    persist_candidate_prediction(
        db_session,
        candidate_id=candidate.id,
        asset_type="group",
        asset_id=7,
        project_id=4,
        forecast_start=UTC_NOW,
        baseline_curve=_curve(UTC_NOW),
        result=CandidateCurveResult(
            curve=_curve(UTC_NOW),
            source="baseline_fallback",
            fallback_reason="invalid_output",
        ),
    )

    event = db_session.query(models.AuditEvent).filter_by(
        action="capacity_prediction.fallback",
        project_id=4,
        outcome="success",
    ).one()
    assert event.actor_type == "system"
    assert event.after_summary["fallback_reason"] == "invalid_output"


def test_successful_candidate_prediction_is_recorded_in_the_unified_audit_log(db_session):
    import models
    from services.capacityPredictionGovernanceService import CandidateCurveResult, persist_candidate_prediction

    db_session.add(models.AIConfig(
        id=1,
        name="forecast-private-model",
        provider="ollama",
        base_url="http://forecast.internal",
        model="forecast-model",
        enabled=True,
        enable_chat=False,
    ))
    db_session.commit()
    candidate = models.CapacityPredictionCandidate(version="capacity-ai-v1", ai_model_id=1)
    db_session.add(candidate)
    db_session.commit()

    persist_candidate_prediction(
        db_session,
        candidate_id=candidate.id,
        asset_type="group",
        asset_id=7,
        project_id=4,
        forecast_start=UTC_NOW,
        baseline_curve=_curve(UTC_NOW),
        result=CandidateCurveResult(curve=_curve(UTC_NOW), source="ai_candidate"),
    )

    event = db_session.query(models.AuditEvent).filter_by(
        action="capacity_prediction.generate",
        project_id=4,
        outcome="success",
    ).one()
    assert event.actor_type == "system"
    assert event.after_summary["source"] == "ai_candidate"


def test_governance_view_reports_only_aggregate_fallback_status(db_session):
    import models
    from services.capacityPredictionGovernanceService import candidate_governance_view

    db_session.add(models.AIConfig(
        id=1, name="forecast-private-model", provider="ollama",
        base_url="http://forecast.internal", model="forecast-model",
        enabled=True, enable_chat=False,
    ))
    candidate = models.CapacityPredictionCandidate(version="capacity-ai-v1", ai_model_id=1)
    db_session.add(candidate)
    db_session.flush()
    db_session.add_all([
        models.CapacityPredictionCandidateForecast(
            candidate_id=candidate.id, asset_type="group", asset_id="7", project_id=4,
            forecast_start=UTC_NOW, baseline_curve=_curve(UTC_NOW), curve=_curve(UTC_NOW),
            source="ai_candidate",
        ),
        models.CapacityPredictionCandidateForecast(
            candidate_id=candidate.id, asset_type="storage_usage", asset_id="9", project_id=4,
            forecast_start=UTC_NOW, baseline_curve=_curve(UTC_NOW), curve=_curve(UTC_NOW),
            source="baseline_fallback", fallback_reason="timeout",
        ),
    ])
    db_session.commit()

    result = candidate_governance_view(db_session, candidate)

    assert result["forecast_count"] == 2
    assert result["fallback_count"] == 1
    assert result["fallback_reasons"] == {"timeout": 1}
    assert "asset_id" not in result


def test_active_candidate_version_is_exposed_without_revealing_model_endpoint():
    import models
    from services.capacityPredictionGovernanceService import _prediction_view

    baseline = SimpleNamespace(
        id=1, asset_type="group", asset_id="7", storage_cluster_id=1, project_id=4,
        vendor="netapp", display_name="group-alpha", training_start=UTC_NOW - timedelta(days=45),
        training_end=UTC_NOW, hard_limit=100.0, algorithm_version="forecast-incident-v1",
        backtest_mape=12.0, created_at=UTC_NOW, curve=_curve(UTC_NOW),
        exhaustion_dates={}, input_quality={"status": "ready"},
    )
    candidate = models.CapacityPredictionCandidate(version="capacity-ai-v2", ai_model_id=1)
    candidate_forecast = SimpleNamespace(
        source="ai_candidate", fallback_reason=None, curve=_curve(UTC_NOW),
    )

    result = _prediction_view(baseline, candidate_forecast, candidate)

    assert result.input_quality["candidate_version"] == "capacity-ai-v2"
    assert not hasattr(result, "base_url")


def test_candidate_activation_needs_three_windows_ten_percent_mape_gain_and_risk_coverage():
    from services.capacityPredictionGovernanceService import candidate_meets_activation_gate

    passing = [
        {
            "baseline_mape": 20.0, "candidate_mape": 17.0, "risk_coverage_ok": True,
            "window_start": UTC_NOW, "window_end": UTC_NOW + timedelta(days=30),
        },
        {
            "baseline_mape": 10.0, "candidate_mape": 8.0, "risk_coverage_ok": True,
            "window_start": UTC_NOW + timedelta(days=30), "window_end": UTC_NOW + timedelta(days=60),
        },
        {
            "baseline_mape": 30.0, "candidate_mape": 25.0, "risk_coverage_ok": True,
            "window_start": UTC_NOW + timedelta(days=60), "window_end": UTC_NOW + timedelta(days=90),
        },
    ]
    assert candidate_meets_activation_gate(passing) is True
    assert candidate_meets_activation_gate(passing[:2]) is False
    assert candidate_meets_activation_gate([
        *passing[:2],
        {
            "baseline_mape": 30.0, "candidate_mape": 29.1, "risk_coverage_ok": True,
            "window_start": UTC_NOW + timedelta(days=60), "window_end": UTC_NOW + timedelta(days=90),
        },
    ]) is False
    assert candidate_meets_activation_gate([
        *passing[:2],
        {
            "baseline_mape": 30.0, "candidate_mape": 25.0, "risk_coverage_ok": False,
            "window_start": UTC_NOW + timedelta(days=60), "window_end": UTC_NOW + timedelta(days=90),
        },
    ]) is False
    assert candidate_meets_activation_gate([passing[0], passing[0], passing[0]]) is False


def test_reader_is_denied_resource_prediction_until_super_admin_enables_global_visibility(db_session):
    import models
    from services.capacityPredictionGovernanceService import get_resource_prediction

    db_session.add_all([
        models.User(id=1, rd_username="reader"),
        models.Project(id=1, name="project-alpha"),
        models.ProjectMembership(project_id=1, user_id=1, role="reader"),
        models.StorageCluster(id=1, name="cluster-alpha", storage_type="netapp"),
        models.Group(id=1, project_id=1, storage_cluster_id=1, group_tag_id=1, name="group-alpha", enable_monitoring=False),
        models.GroupTag(id=1, name="research"),
        models.CapacityForecast(
            asset_type="group", asset_id="1", storage_cluster_id=1, project_id=1,
            vendor="netapp", display_name="group-alpha", training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW, hard_limit=100.0, curve=_curve(UTC_NOW),
            exhaustion_dates={}, algorithm_version="forecast-incident-v1", input_quality={},
        ),
    ])
    db_session.commit()
    reader = db_session.get(models.User, 1)

    with pytest.raises(HTTPException, match="globally disabled"):
        get_resource_prediction(db_session, current_user=reader, asset_type="group", asset_id=1)

    db_session.add(models.CapacityPredictionSettings(id=1, user_visible=True))
    db_session.commit()
    result = get_resource_prediction(db_session, current_user=reader, asset_type="group", asset_id=1)

    assert result.asset_type == "group"
    assert result.asset_id == "1"


def test_reader_cannot_list_capacity_plans_until_global_visibility_is_enabled(db_session):
    import models
    from services.capacityPredictionGovernanceService import list_resource_capacity_plans

    db_session.add_all([
        models.User(id=1, rd_username="reader"),
        models.Project(id=1, name="project-alpha"),
        models.ProjectMembership(project_id=1, user_id=1, role="reader"),
        models.StorageCluster(id=1, name="cluster-alpha", storage_type="netapp"),
        models.GroupTag(id=1, name="research"),
        models.Group(id=1, project_id=1, storage_cluster_id=1, group_tag_id=1, name="group-alpha", enable_monitoring=False),
    ])
    db_session.commit()

    with pytest.raises(HTTPException, match="globally disabled"):
        list_resource_capacity_plans(
            db_session,
            current_user=db_session.get(models.User, 1),
            asset_type="group",
            asset_id=1,
        )

    db_session.add(models.CapacityPredictionSettings(id=1, user_visible=True))
    db_session.commit()
    assert list_resource_capacity_plans(
        db_session,
        current_user=db_session.get(models.User, 1),
        asset_type="group",
        asset_id=1,
    ) == []


def test_related_incidents_use_resource_rbac_when_prediction_publication_is_disabled(db_session):
    import models
    from services.capacityPredictionGovernanceService import list_resource_related_incidents

    db_session.add_all([
        models.User(id=1, rd_username="reader"),
        models.Project(id=1, name="project-alpha"),
        models.Project(id=2, name="project-beta"),
        models.ProjectMembership(project_id=1, user_id=1, role="reader"),
        models.StorageCluster(id=1, name="cluster-alpha", storage_type="netapp"),
        models.GroupTag(id=1, name="research"),
        models.Group(
            id=11,
            project_id=1,
            storage_cluster_id=1,
            group_tag_id=1,
            name="group-alpha",
            enable_monitoring=False,
        ),
        models.Group(
            id=12,
            project_id=2,
            storage_cluster_id=1,
            group_tag_id=1,
            name="group-beta",
            enable_monitoring=False,
        ),
        models.CapacityPredictionSettings(id=1, user_visible=False),
        models.Incident(
            id=1,
            correlation_key="cluster-1:group:11:capacity_pressure",
            correlation_bucket_at=UTC_NOW,
            asset_type="group",
            asset_id="11",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="group-alpha",
            category="capacity_pressure",
            opened_at=UTC_NOW,
            last_evidence_at=UTC_NOW,
        ),
    ])
    db_session.commit()
    reader = db_session.get(models.User, 1)

    with pytest.raises(HTTPException) as denied:
        list_resource_related_incidents(
            db_session,
            current_user=reader,
            asset_type="group",
            asset_id=12,
        )
    assert denied.value.status_code == 403
    assert denied.value.detail == "project permission required"

    result = list_resource_related_incidents(
        db_session,
        current_user=reader,
        asset_type="group",
        asset_id=11,
    )

    assert [
        (
            item["id"],
            item["category"],
            item["severity"],
            item["status"],
            item["rca_confidence"],
        )
        for item in result
    ] == [(1, "capacity_pressure", "warning", "open", None)]


def test_project_admin_can_only_create_capacity_plan_for_its_own_resource(db_session):
    import models
    from services.capacityPredictionGovernanceService import create_capacity_plan

    db_session.add_all([
        models.User(id=1, rd_username="admin"),
        models.Project(id=1, name="project-alpha"),
        models.Project(id=2, name="project-beta"),
        models.ProjectMembership(project_id=1, user_id=1, role="project_admin"),
        models.CapacityPredictionSettings(id=1, user_visible=True),
        models.StorageCluster(id=1, name="cluster-alpha", storage_type="netapp"),
        models.GroupTag(id=1, name="research"),
        models.Group(id=1, project_id=1, storage_cluster_id=1, group_tag_id=1, name="group-alpha", enable_monitoring=False),
        models.Group(id=2, project_id=2, storage_cluster_id=1, group_tag_id=1, name="group-beta", enable_monitoring=False),
    ])
    db_session.commit()
    user = db_session.get(models.User, 1)

    plan = create_capacity_plan(
        db_session, current_user=user, asset_type="group", asset_id=1,
        effective_at=UTC_NOW, capacity_delta=10.0, reason="approved expansion",
    )
    assert plan.project_id == 1

    with pytest.raises(HTTPException, match="project permission"):
        create_capacity_plan(
            db_session, current_user=user, asset_type="group", asset_id=2,
            effective_at=UTC_NOW, capacity_delta=10.0, reason="cross project",
        )


def test_only_candidate_with_passing_evaluations_can_be_enabled(db_session):
    import models
    from services.capacityPredictionGovernanceService import (
        activate_capacity_prediction_candidate,
        create_capacity_prediction_candidate,
        record_capacity_prediction_evaluation,
    )

    db_session.add(models.AIConfig(
        id=1,
        name="forecast-private-model",
        provider="ollama",
        base_url="http://forecast.internal",
        model="forecast-model",
        enabled=True,
        enable_chat=False,
    ))
    db_session.commit()
    candidate = create_capacity_prediction_candidate(
        db_session,
        version="capacity-ai-v1",
        ai_model_id=1,
    )
    for index in range(3):
        record_capacity_prediction_evaluation(
            db_session,
            candidate_id=candidate.id,
            baseline_mape=20.0,
            candidate_mape=17.0,
            risk_coverage_ok=True,
            window_start=UTC_NOW + timedelta(days=index * 30),
            window_end=UTC_NOW + timedelta(days=(index + 1) * 30),
        )
    activate_capacity_prediction_candidate(db_session, candidate_id=candidate.id)

    assert db_session.get(models.CapacityPredictionCandidate, candidate.id).enabled is True

    rejected = create_capacity_prediction_candidate(
        db_session,
        version="capacity-ai-v2",
        ai_model_id=1,
    )
    with pytest.raises(HTTPException, match="activation gate"):
        activate_capacity_prediction_candidate(db_session, candidate_id=rejected.id)


def test_candidate_can_be_activated_after_its_ai_model_is_disabled(db_session):
    import models
    from services.capacityPredictionGovernanceService import (
        activate_capacity_prediction_candidate,
        record_capacity_prediction_evaluation,
    )

    model = models.AIConfig(
        id=1, name="forecast-private-model", provider="ollama",
        base_url="http://forecast.internal", model="forecast-model",
        enabled=True, enable_chat=False,
    )
    candidate = models.CapacityPredictionCandidate(version="capacity-ai-v1", ai_model_id=1)
    db_session.add_all([model, candidate])
    db_session.flush()
    for index in range(3):
        record_capacity_prediction_evaluation(
            db_session,
            candidate_id=candidate.id,
            baseline_mape=20.0,
            candidate_mape=17.0,
            risk_coverage_ok=True,
            window_start=UTC_NOW + timedelta(days=index * 30),
            window_end=UTC_NOW + timedelta(days=(index + 1) * 30),
        )
    model.enabled = False
    db_session.flush()

    activate_capacity_prediction_candidate(db_session, candidate_id=candidate.id)

    assert db_session.get(models.CapacityPredictionCandidate, candidate.id).enabled is True


def test_duplicate_candidate_version_returns_a_stable_conflict(db_session):
    import models
    from services.capacityPredictionGovernanceService import create_capacity_prediction_candidate

    db_session.add(models.AIConfig(
        id=1, name="forecast-private-model", provider="ollama",
        base_url="http://forecast.internal", model="forecast-model",
        enabled=True, enable_chat=False,
    ))
    db_session.commit()
    create_capacity_prediction_candidate(db_session, version="capacity-ai-v1", ai_model_id=1)

    with pytest.raises(HTTPException) as error:
        create_capacity_prediction_candidate(db_session, version="capacity-ai-v1", ai_model_id=1)

    assert error.value.status_code == 409
    assert "version" in error.value.detail


def test_candidate_evaluations_require_a_30_day_holdout_window(db_session):
    import models
    from services.capacityPredictionGovernanceService import record_capacity_prediction_evaluation

    db_session.add(models.AIConfig(
        id=1,
        name="forecast-private-model",
        provider="ollama",
        base_url="http://forecast.internal",
        model="forecast-model",
        enabled=True,
        enable_chat=False,
    ))
    candidate = models.CapacityPredictionCandidate(version="capacity-ai-v1", ai_model_id=1)
    db_session.add(candidate)
    db_session.commit()

    with pytest.raises(HTTPException, match="30-day"):
        record_capacity_prediction_evaluation(
            db_session,
            candidate_id=candidate.id,
            baseline_mape=20.0,
            candidate_mape=17.0,
            risk_coverage_ok=True,
            window_start=UTC_NOW,
            window_end=UTC_NOW + timedelta(days=29),
        )
    with pytest.raises(HTTPException, match="finite"):
        record_capacity_prediction_evaluation(
            db_session,
            candidate_id=candidate.id,
            baseline_mape=float("nan"),
            candidate_mape=17.0,
            risk_coverage_ok=True,
            window_start=UTC_NOW,
            window_end=UTC_NOW + timedelta(days=30),
        )


def test_candidate_evaluation_windows_cannot_be_recorded_twice(db_session):
    import models
    from services.capacityPredictionGovernanceService import record_capacity_prediction_evaluation

    db_session.add(models.AIConfig(
        id=1, name="forecast-private-model", provider="ollama",
        base_url="http://forecast.internal", model="forecast-model",
        enabled=True, enable_chat=False,
    ))
    candidate = models.CapacityPredictionCandidate(version="capacity-ai-v1", ai_model_id=1)
    db_session.add(candidate)
    db_session.commit()
    values = dict(
        candidate_id=candidate.id,
        baseline_mape=20.0,
        candidate_mape=17.0,
        risk_coverage_ok=True,
        window_start=UTC_NOW,
        window_end=UTC_NOW + timedelta(days=30),
    )
    record_capacity_prediction_evaluation(db_session, **values)

    with pytest.raises(HTTPException) as error:
        record_capacity_prediction_evaluation(db_session, **values)

    assert error.value.status_code == 409
    assert "window" in error.value.detail


def test_latest_forecast_is_selected_by_training_date_not_insert_order(db_session):
    import models
    from crud.capacityPredictionCrud import latest_forecast

    newer = models.CapacityForecast(
        asset_type="group", asset_id="1", storage_cluster_id=1, project_id=1,
        vendor="netapp", display_name="group-alpha", training_start=UTC_NOW - timedelta(days=45),
        training_end=UTC_NOW, hard_limit=100.0, curve=_curve(UTC_NOW), exhaustion_dates={},
        algorithm_version="forecast-incident-v1", input_quality={}, created_at=UTC_NOW,
    )
    backfilled = models.CapacityForecast(
        asset_type="group", asset_id="1", storage_cluster_id=1, project_id=1,
        vendor="netapp", display_name="group-alpha", training_start=UTC_NOW - timedelta(days=46),
        training_end=UTC_NOW - timedelta(days=1), hard_limit=100.0,
        curve=_curve(UTC_NOW - timedelta(days=1)), exhaustion_dates={},
        algorithm_version="forecast-incident-v1", input_quality={}, created_at=UTC_NOW + timedelta(hours=1),
    )
    db_session.add_all([newer, backfilled])
    db_session.commit()

    assert latest_forecast(db_session, asset_type="group", asset_id="1").id == newer.id


def test_stale_candidate_curve_does_not_override_the_current_baseline(db_session):
    import models
    from services.capacityPredictionGovernanceService import get_resource_prediction

    db_session.add_all([
        models.User(id=1, rd_username="reader"),
        models.Project(id=1, name="project-alpha"),
        models.ProjectMembership(project_id=1, user_id=1, role="reader"),
        models.StorageCluster(id=1, name="cluster-alpha", storage_type="netapp"),
        models.GroupTag(id=1, name="research"),
        models.Group(id=1, project_id=1, storage_cluster_id=1, group_tag_id=1, name="group-alpha", enable_monitoring=False),
        models.CapacityPredictionSettings(id=1, user_visible=True),
        models.AIConfig(id=1, name="forecast-private-model", provider="ollama", base_url="http://forecast.internal", model="forecast-model", enabled=True, enable_chat=False),
    ])
    db_session.flush()
    candidate = models.CapacityPredictionCandidate(version="capacity-ai-v1", ai_model_id=1, enabled=True)
    baseline_curve = _curve(UTC_NOW)
    stale_curve = _curve(UTC_NOW - timedelta(days=1), offset=500)
    db_session.add_all([
        candidate,
        models.CapacityForecast(
            asset_type="group", asset_id="1", storage_cluster_id=1, project_id=1,
            vendor="netapp", display_name="group-alpha", training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW, hard_limit=1000.0, curve=baseline_curve, exhaustion_dates={},
            algorithm_version="forecast-incident-v1", input_quality={},
        ),
    ])
    db_session.flush()
    db_session.add(models.CapacityPredictionCandidateForecast(
        candidate_id=candidate.id, asset_type="group", asset_id="1", project_id=1,
        forecast_start=UTC_NOW - timedelta(days=1), baseline_curve=stale_curve,
        curve=stale_curve, source="ai_candidate",
    ))
    db_session.commit()

    result = get_resource_prediction(
        db_session,
        current_user=db_session.get(models.User, 1),
        asset_type="group",
        asset_id=1,
    )

    assert result.curve == baseline_curve
    assert "candidate_version" not in result.input_quality


def test_capacity_prediction_list_uses_final_curve_filters_projects_and_paginates(
    db_session,
    api_client_factory,
):
    import models
    from routers import forecast_incidents
    from utils.security import issue_token

    db_session.add_all([
        models.User(id=1, rd_username="reader"),
        models.Project(id=1, name="project-alpha"),
        models.Project(id=2, name="project-beta"),
        models.ProjectMembership(project_id=1, user_id=1, role="reader"),
        models.StorageCluster(id=1, name="cluster-alpha", storage_type="netapp"),
        models.GroupTag(id=1, name="research"),
        models.Group(
            id=11,
            project_id=1,
            storage_cluster_id=1,
            group_tag_id=1,
            name="visible-group",
            enable_monitoring=False,
        ),
        models.Group(
            id=12,
            project_id=2,
            storage_cluster_id=1,
            group_tag_id=1,
            name="hidden-group",
            enable_monitoring=False,
        ),
        models.StorageUsage(id=101, storage_cluster_id=1, group_id=11, linux_path="/visible/alice"),
        models.CapacityPredictionSettings(id=1, user_visible=True),
        models.AIConfig(
            id=1,
            name="forecast-model",
            provider="ollama",
            base_url="http://forecast.internal",
            model="forecast-model",
            enabled=True,
            enable_chat=False,
        ),
    ])
    db_session.flush()
    candidate = models.CapacityPredictionCandidate(
        version="capacity-ai-v2",
        ai_model_id=1,
        enabled=True,
    )
    db_session.add(candidate)
    db_session.flush()

    baseline_curve = _curve(UTC_NOW)
    final_curve = _curve(UTC_NOW, offset=100)
    db_session.add_all([
        models.CapacityForecast(
            id=1,
            asset_type="group",
            asset_id="11",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="visible-group",
            training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW,
            hard_limit=1000.0,
            curve=baseline_curve,
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
            created_at=UTC_NOW + timedelta(hours=3),
        ),
        models.CapacityForecast(
            id=2,
            asset_type="storage_usage",
            asset_id="101",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="/visible/alice",
            training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW,
            hard_limit=500.0,
            curve=baseline_curve,
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
            created_at=UTC_NOW + timedelta(hours=2),
        ),
        models.CapacityForecast(
            id=3,
            asset_type="group",
            asset_id="12",
            storage_cluster_id=1,
            project_id=2,
            vendor="netapp",
            display_name="hidden-group",
            training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW,
            hard_limit=1000.0,
            curve=baseline_curve,
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
            created_at=UTC_NOW + timedelta(hours=5),
        ),
        models.CapacityForecast(
            id=4,
            asset_type="storage_cluster",
            asset_id="1",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="cluster-alpha",
            training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW,
            hard_limit=2000.0,
            curve=baseline_curve,
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
            created_at=UTC_NOW + timedelta(hours=4),
        ),
        models.CapacityForecast(
            id=5,
            asset_type="group",
            asset_id="11",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="visible-group-old",
            training_start=UTC_NOW - timedelta(days=46),
            training_end=UTC_NOW - timedelta(days=1),
            hard_limit=1000.0,
            curve=_curve(UTC_NOW - timedelta(days=1)),
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
            created_at=UTC_NOW + timedelta(hours=6),
        ),
        models.CapacityPredictionCandidateForecast(
            candidate_id=candidate.id,
            asset_type="group",
            asset_id="11",
            project_id=1,
            forecast_start=UTC_NOW,
            baseline_curve=baseline_curve,
            curve=final_curve,
            source="ai_candidate",
        ),
    ])
    db_session.commit()

    client = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )
    first_page = client.get(
        "/storage-pulse/api/v1/capacity-predictions",
        params={"page": 1, "size": 1},
    )

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 2
    assert len(first_page.json()["content"]) == 1
    first = first_page.json()["content"][0]
    assert first["asset_type"] == "group"
    assert first["asset_id"] == "11"
    assert len(first["curve"]) == len(final_curve)
    for serialized_point, expected_point in zip(first["curve"], final_curve, strict=True):
        assert serialized_point["observed_at"] == expected_point["observed_at"].replace("+00:00", "Z")
        assert {
            key: serialized_point[key]
            for key in ("p10", "p50", "p90")
        } == {
            key: expected_point[key]
            for key in ("p10", "p50", "p90")
        }
        assert serialized_point["capacity"] == {
            key: {"value": int(expected_point[key]), "unit": "GB"}
            for key in ("p10", "p50", "p90")
        }
    assert first["data_unit"] == "GB"
    assert first["input_quality"]["prediction_source"] == "ai_candidate"
    assert first["input_quality"]["candidate_version"] == "capacity-ai-v2"

    second_page = client.get(
        "/storage-pulse/api/v1/capacity-predictions",
        params={"page": 2, "size": 1},
    )
    assert second_page.status_code == 200
    assert second_page.json()["total"] == 2
    assert second_page.json()["content"][0]["asset_type"] == "storage_usage"


def test_capacity_prediction_list_uses_current_resource_project_after_group_move(
    db_session,
    api_client_factory,
):
    import models
    from routers import forecast_incidents
    from utils.security import issue_token

    db_session.add_all([
        models.User(id=1, rd_username="reader"),
        models.User(id=2, rd_username="alice"),
        models.User(id=3, rd_username="current-reader"),
        models.Project(id=1, name="old-project"),
        models.Project(id=2, name="current-project"),
        models.ProjectMembership(project_id=1, user_id=1, role="reader"),
        models.ProjectMembership(project_id=2, user_id=3, role="reader"),
        models.StorageCluster(id=1, name="cluster-alpha", storage_type="netapp"),
        models.GroupTag(id=1, name="research"),
        models.Group(
            id=11,
            project_id=2,
            storage_cluster_id=1,
            group_tag_id=1,
            name="moved-group",
            enable_monitoring=False,
        ),
        models.StorageUsage(
            id=101,
            storage_cluster_id=1,
            group_id=11,
            linux_path="/moved/alice",
        ),
        models.CapacityPredictionSettings(id=1, user_visible=True),
        models.CapacityForecast(
            id=1,
            asset_type="group",
            asset_id="11",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="moved-group",
            training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW,
            hard_limit=1000.0,
            curve=_curve(UTC_NOW),
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
        ),
        models.CapacityForecast(
            id=2,
            asset_type="storage_usage",
            asset_id="101",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="/moved/alice",
            training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW,
            hard_limit=500.0,
            curve=_curve(UTC_NOW),
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
        ),
    ])
    db_session.commit()

    reader = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )
    reader_response = reader.get("/storage-pulse/api/v1/capacity-predictions")
    assert reader_response.status_code == 200
    assert reader_response.json() == {"content": [], "total": 0}

    current_reader = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(3)}"},
    )
    current_reader_response = current_reader.get(
        "/storage-pulse/api/v1/capacity-predictions"
    )
    assert current_reader_response.status_code == 200
    assert current_reader_response.json()["total"] == 2
    assert {
        item["asset_type"] for item in current_reader_response.json()["content"]
    } == {"group", "storage_usage"}

    superadmin = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(2)}"},
    )
    superadmin_response = superadmin.get("/storage-pulse/api/v1/capacity-predictions")
    assert superadmin_response.status_code == 200
    assert superadmin_response.json()["total"] == 2
    assert {
        item["asset_type"] for item in superadmin_response.json()["content"]
    } == {"group", "storage_usage"}


def test_capacity_prediction_list_excludes_deleted_group_and_storage_usage(
    db_session,
    api_client_factory,
):
    import models
    from routers import forecast_incidents
    from utils.security import issue_token

    db_session.add_all([
        models.User(id=1, rd_username="reader"),
        models.User(id=2, rd_username="alice"),
        models.Project(id=1, name="project-alpha"),
        models.ProjectMembership(project_id=1, user_id=1, role="reader"),
        models.StorageCluster(id=1, name="cluster-alpha", storage_type="netapp"),
        models.GroupTag(id=1, name="research"),
        models.Group(
            id=11,
            project_id=1,
            storage_cluster_id=1,
            group_tag_id=1,
            name="deleted-group",
            enable_monitoring=False,
        ),
        models.StorageUsage(
            id=101,
            storage_cluster_id=1,
            group_id=11,
            linux_path="/deleted/alice",
        ),
        models.CapacityPredictionSettings(id=1, user_visible=True),
        models.CapacityForecast(
            id=1,
            asset_type="group",
            asset_id="11",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="deleted-group",
            training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW,
            hard_limit=1000.0,
            curve=_curve(UTC_NOW),
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
        ),
        models.CapacityForecast(
            id=2,
            asset_type="storage_usage",
            asset_id="101",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="/deleted/alice",
            training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW,
            hard_limit=500.0,
            curve=_curve(UTC_NOW),
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
        ),
    ])
    db_session.commit()

    db_session.delete(db_session.get(models.StorageUsage, 101))
    db_session.delete(db_session.get(models.Group, 11))
    db_session.commit()

    for user_id in (1, 2):
        client = api_client_factory(
            [forecast_incidents.router],
            headers={"Authorization": f"Bearer {issue_token(user_id)}"},
        )
        response = client.get("/storage-pulse/api/v1/capacity-predictions")
        assert response.status_code == 200
        assert response.json() == {"content": [], "total": 0}


def test_capacity_prediction_list_skips_malformed_asset_ids_and_compiles_safe_postgres_cast(
    db_session,
):
    import models
    from crud.capacityPredictionCrud import _safe_integer_asset_id, list_latest_forecasts
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql

    db_session.add_all([
        models.Project(id=1, name="project-alpha"),
        models.StorageCluster(id=1, name="cluster-alpha", storage_type="netapp"),
        models.GroupTag(id=1, name="research"),
        models.Group(
            id=11,
            project_id=1,
            storage_cluster_id=1,
            group_tag_id=1,
            name="group-alpha",
            enable_monitoring=False,
        ),
        models.StorageUsage(
            id=101,
            storage_cluster_id=1,
            group_id=11,
            linux_path="/visible/alice",
        ),
        models.CapacityForecast(
            id=1,
            asset_type="group",
            asset_id="abc",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="malformed-group",
            training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW,
            hard_limit=1000.0,
            curve=_curve(UTC_NOW),
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
        ),
        models.CapacityForecast(
            id=2,
            asset_type="storage_usage",
            asset_id="99999999999",
            storage_cluster_id=1,
            project_id=1,
            vendor="netapp",
            display_name="malformed-usage",
            training_start=UTC_NOW - timedelta(days=45),
            training_end=UTC_NOW,
            hard_limit=500.0,
            curve=_curve(UTC_NOW),
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready"},
        ),
    ])
    db_session.commit()

    rows, total = list_latest_forecasts(
        db_session,
        visible_project_ids={1},
        page=1,
        size=20,
    )
    assert rows == []
    assert total == 0

    compiled = str(
        select(_safe_integer_asset_id(models.CapacityForecast.asset_id)).compile(
            dialect=postgresql.dialect()
        )
    )
    case_position = compiled.index("CASE WHEN")
    cast_position = compiled.index(
        "THEN CAST(capacity_forecasts.asset_id AS INTEGER)"
    )
    end_position = compiled.index(" END", cast_position)
    assert case_position < cast_position < end_position


def test_capacity_prediction_list_requires_publication_and_validates_pagination(
    db_session,
    api_client_factory,
):
    import models
    from routers import forecast_incidents
    from utils.security import issue_token

    db_session.add_all([
        models.User(id=1, rd_username="reader"),
        models.Project(id=1, name="project-alpha"),
        models.ProjectMembership(project_id=1, user_id=1, role="reader"),
        models.CapacityPredictionSettings(id=1, user_visible=False),
    ])
    db_session.commit()
    client = api_client_factory(
        [forecast_incidents.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )

    denied = client.get("/storage-pulse/api/v1/capacity-predictions")
    assert denied.status_code == 403
    assert client.get(
        "/storage-pulse/api/v1/capacity-predictions",
        params={"page": 0},
    ).status_code == 422
    assert client.get(
        "/storage-pulse/api/v1/capacity-predictions",
        params={"size": 101},
    ).status_code == 422


def test_final_prediction_list_batches_candidate_lookup_after_database_pagination(monkeypatch):
    from unittest.mock import Mock

    from services import capacityPredictionGovernanceService as governance

    db = object()
    current_user = object()
    baselines = [
        SimpleNamespace(asset_type="group", asset_id="11", training_end=UTC_NOW),
        SimpleNamespace(asset_type="storage_usage", asset_id="101", training_end=UTC_NOW),
    ]
    list_latest = Mock(return_value=(baselines, 7))
    active_candidate = SimpleNamespace(id=9, version="capacity-ai-v2")
    list_candidate_batch = Mock(return_value=[])
    per_resource_lookup = Mock(side_effect=AssertionError("candidate lookup must be batched"))

    monkeypatch.setattr(governance, "_require_prediction_visibility", Mock())
    monkeypatch.setattr(governance.forecastIncidentService, "visible_project_ids", Mock(return_value={1}))
    monkeypatch.setattr(governance.capacityPredictionCrud, "list_latest_forecasts", list_latest)
    monkeypatch.setattr(governance.capacityPredictionCrud, "active_candidate", Mock(return_value=active_candidate))
    monkeypatch.setattr(
        governance.capacityPredictionCrud,
        "list_candidate_forecasts_for_baselines",
        list_candidate_batch,
    )
    monkeypatch.setattr(
        governance.capacityPredictionCrud,
        "latest_active_candidate_forecast",
        per_resource_lookup,
    )

    rows, total = governance.list_final_predictions(
        db,
        current_user=current_user,
        page=2,
        size=2,
    )

    assert rows == baselines
    assert total == 7
    list_latest.assert_called_once_with(
        db,
        visible_project_ids={1},
        page=2,
        size=2,
    )
    list_candidate_batch.assert_called_once_with(
        db,
        candidate_id=9,
        baseline_keys=[
            ("group", "11", UTC_NOW),
            ("storage_usage", "101", UTC_NOW),
        ],
    )
    per_resource_lookup.assert_not_called()


def test_candidate_accepts_any_configured_ai_center_model(db_session):
    import models
    from services.capacityPredictionGovernanceService import create_capacity_prediction_candidate

    db_session.add(models.AIConfig(
        id=1,
        name="public-model",
        provider="openai",
        base_url="https://api.example.com",
        model="public-model",
        enabled=True,
        enable_chat=False,
    ))
    db_session.commit()

    candidate = create_capacity_prediction_candidate(
        db_session,
        version="capacity-ai-public-v1",
        ai_model_id=1,
    )

    assert candidate.ai_model_id == 1


def test_governance_router_exposes_safe_candidate_lifecycle_only_to_super_admins():
    import inspect
    import routers.forecast_incidents as forecast_incidents_router
    from routers.forecast_incidents import router
    from schemas.capacityPredictionSchema import CapacityPredictionCandidateOut

    list_route = next(
        route
        for route in router.routes
        if route.path == "/v1/admin/capacity-prediction-candidates" and "GET" in route.methods
    )
    activate_route = next(
        route
        for route in router.routes
        if route.path == "/v1/admin/capacity-prediction-candidates/{candidate_id}/activate"
    )

    assert list_route.response_model == list[CapacityPredictionCandidateOut]
    assert list_route.dependencies
    assert activate_route.dependencies
    assert "evaluations" in CapacityPredictionCandidateOut.model_fields
    assert "activation_ready" in CapacityPredictionCandidateOut.model_fields
    assert "forecast_count" in CapacityPredictionCandidateOut.model_fields
    assert "fallback_count" in CapacityPredictionCandidateOut.model_fields
    assert "capacityPredictionCrud" not in inspect.getsource(forecast_incidents_router)


def test_capacity_plan_rejects_no_op_or_blank_approval():
    from pydantic import ValidationError
    from schemas.capacityPredictionSchema import CapacityPredictionPlanCreate

    with pytest.raises(ValidationError):
        CapacityPredictionPlanCreate(
            effective_at=UTC_NOW,
            capacity_delta=0,
            reason="approved",
        )
    with pytest.raises(ValidationError):
        CapacityPredictionPlanCreate(
            effective_at=UTC_NOW,
            capacity_delta=10,
            reason="   ",
        )
