# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

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


def test_candidate_activation_needs_three_windows_ten_percent_mape_gain_and_risk_coverage():
    from services.capacityPredictionGovernanceService import candidate_meets_activation_gate

    passing = [
        {"baseline_mape": 20.0, "candidate_mape": 17.0, "risk_coverage_ok": True},
        {"baseline_mape": 10.0, "candidate_mape": 8.0, "risk_coverage_ok": True},
        {"baseline_mape": 30.0, "candidate_mape": 25.0, "risk_coverage_ok": True},
    ]
    assert candidate_meets_activation_gate(passing) is True
    assert candidate_meets_activation_gate(passing[:2]) is False
    assert candidate_meets_activation_gate([
        *passing[:2],
        {"baseline_mape": 30.0, "candidate_mape": 29.1, "risk_coverage_ok": True},
    ]) is False
    assert candidate_meets_activation_gate([
        *passing[:2],
        {"baseline_mape": 30.0, "candidate_mape": 25.0, "risk_coverage_ok": False},
    ]) is False


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


def test_candidate_requires_private_ollama_model(db_session):
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

    with pytest.raises(HTTPException, match="private AI model"):
        create_capacity_prediction_candidate(
            db_session,
            version="capacity-ai-public-v1",
            ai_model_id=1,
        )


def test_governance_router_exposes_safe_candidate_lifecycle_only_to_super_admins():
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
