# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import get_args

import pytest
from fastapi import HTTPException


UTC_NOW = datetime(2026, 7, 22, 1, 0, tzinfo=timezone.utc)


def _forecast(*, status="ready", p50=None, p90=None):
    return SimpleNamespace(
        training_end=UTC_NOW,
        created_at=UTC_NOW,
        exhaustion_dates={"p10": None, "p50": p50, "p90": p90},
        input_quality={"status": status, "coverage_ratio": 1.0},
    )


@pytest.mark.parametrize(
    ("forecast", "expected_level"),
    [
        (_forecast(status="insufficient"), "insufficient"),
        (_forecast(p90=UTC_NOW + timedelta(days=7)), "critical"),
        (_forecast(p50=UTC_NOW + timedelta(days=30)), "high"),
        (_forecast(p90=UTC_NOW + timedelta(days=30)), "watch"),
        (_forecast(), "none"),
    ],
)
def test_exhaustion_risk_uses_one_server_side_boundary_contract(forecast, expected_level):
    from services.capacityPredictionGovernanceService import build_exhaustion_risk_summary

    result = build_exhaustion_risk_summary(forecast, now=UTC_NOW)

    assert result["level"] == expected_level
    assert result["horizon_days"] == 30
    assert result["reason"]


def test_prediction_schema_exposes_the_four_business_dimensions():
    from schemas.capacityPredictionSchema import PredictionAssetType

    assert set(get_args(PredictionAssetType)) == {
        "storage_cluster",
        "project",
        "group",
        "storage_usage",
    }


def test_capacity_targets_include_project_history_without_faking_a_cluster(db_session):
    import models
    from celery_tasks.tasks.forecast_incidents import _capacity_targets

    db_session.add_all([
        models.Project(id=11, name="project-alpha", limit=800.0),
        models.StorageCluster(
            id=21,
            name="cluster-alpha",
            storage_type="netapp",
            limit=1200.0,
        ),
    ])
    db_session.commit()

    targets = {
        (target.asset_ref.asset_type, target.asset_ref.asset_id): target
        for target in _capacity_targets(db_session)
    }

    project = targets[("project", "11")]
    assert project.table_name == "project_storage_usages"
    assert project.key_column == "project_id"
    assert project.hard_limit == 800.0
    assert project.asset_ref.storage_cluster_id is None
    assert targets[("storage_cluster", "21")].table_name == "storage_cluster_storage_usages"


def test_project_readers_can_read_project_risk_but_not_cluster_risk(db_session, monkeypatch):
    import models
    from services import capacityPredictionGovernanceService as service

    monkeypatch.setattr(service, "is_super_admin", lambda user: user.rd_username == "root")
    db_session.add_all([
        models.User(id=1, rd_username="reader"),
        models.User(id=2, rd_username="root"),
        models.Project(id=11, name="project-alpha", limit=800.0),
        models.ProjectMembership(project_id=11, user_id=1, role="reader"),
        models.StorageCluster(id=21, name="cluster-alpha", storage_type="netapp", limit=1200.0),
        models.CapacityPredictionSettings(id=1, user_visible=True),
        models.CapacityForecast(
            asset_type="project",
            asset_id="11",
            storage_cluster_id=None,
            project_id=11,
            vendor="mixed",
            display_name="project-alpha",
            training_start=UTC_NOW - timedelta(days=44),
            training_end=UTC_NOW,
            hard_limit=800.0,
            curve=[],
            exhaustion_dates={"p90": (UTC_NOW + timedelta(days=20)).isoformat()},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready", "coverage_ratio": 1.0},
        ),
        models.CapacityForecast(
            asset_type="storage_cluster",
            asset_id="21",
            storage_cluster_id=21,
            project_id=None,
            vendor="netapp",
            display_name="cluster-alpha",
            training_start=UTC_NOW - timedelta(days=44),
            training_end=UTC_NOW,
            hard_limit=1200.0,
            curve=[],
            exhaustion_dates={},
            algorithm_version="forecast-incident-v1",
            input_quality={"status": "ready", "coverage_ratio": 1.0},
        ),
    ])
    db_session.commit()

    reader = db_session.get(models.User, 1)
    root = db_session.get(models.User, 2)

    project_risk = service.get_capacity_exhaustion_risk(
        db_session,
        current_user=reader,
        asset_type="project",
        asset_id=11,
        now=UTC_NOW,
    )
    assert project_risk["level"] == "watch"

    with pytest.raises(HTTPException) as denied:
        service.get_capacity_exhaustion_risk(
            db_session,
            current_user=reader,
            asset_type="storage_cluster",
            asset_id=21,
            now=UTC_NOW,
        )
    assert denied.value.status_code == 403

    assert service.get_capacity_exhaustion_risk(
        db_session,
        current_user=root,
        asset_type="storage_cluster",
        asset_id=21,
        now=UTC_NOW,
    )["level"] == "none"


def test_candidate_creation_rejects_a_configured_but_disabled_model(db_session):
    import models
    from services.capacityPredictionGovernanceService import create_capacity_prediction_candidate

    db_session.add(models.AIConfig(
        id=9,
        name="disabled-model",
        provider="openai",
        base_url="https://api.example.com",
        model="forecast-model",
        enabled=False,
        enable_chat=False,
    ))
    db_session.commit()

    with pytest.raises(HTTPException) as rejected:
        create_capacity_prediction_candidate(
            db_session,
            version="capacity-ai-disabled",
            ai_model_id=9,
        )

    assert rejected.value.status_code == 422
    assert "enabled" in rejected.value.detail
