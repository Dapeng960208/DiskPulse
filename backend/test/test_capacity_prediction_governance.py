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
        {"baseline_mape": 30.0, "candidate_mape": 28.0, "risk_coverage_ok": True},
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
        models.Group(id=1, project_id=1, storage_cluster_id=1, group_tag_id=1, name="group-alpha"),
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


def test_project_admin_can_only_create_capacity_plan_for_its_own_resource(db_session):
    import models
    from services.capacityPredictionGovernanceService import create_capacity_plan

    db_session.add_all([
        models.User(id=1, rd_username="admin"),
        models.Project(id=1, name="project-alpha"),
        models.Project(id=2, name="project-beta"),
        models.ProjectMembership(project_id=1, user_id=1, role="project_admin"),
        models.StorageCluster(id=1, name="cluster-alpha", storage_type="netapp"),
        models.GroupTag(id=1, name="research"),
        models.Group(id=1, project_id=1, storage_cluster_id=1, group_tag_id=1, name="group-alpha"),
        models.Group(id=2, project_id=2, storage_cluster_id=1, group_tag_id=1, name="group-beta"),
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
