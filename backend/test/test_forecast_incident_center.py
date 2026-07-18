# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

import pytest


UTC_NOW = datetime(2026, 7, 18, 8, 0, tzinfo=timezone.utc)


def _asset(project_id: int | None = 1):
    from services.forecastIncidentService import AssetRef

    return AssetRef(
        asset_type="group",
        asset_id="101",
        storage_cluster_id=7,
        project_id=project_id,
        vendor="netapp",
        display_name="project-alpha",
    )


def test_capacity_forecast_requires_30_valid_daily_points_and_80_percent_coverage():
    from services import forecastIncidentService as analytics

    points = [(UTC_NOW - timedelta(days=day), float(day)) for day in range(29)]
    result = analytics.build_capacity_forecast(
        _asset(),
        points=points,
        hard_limit=100.0,
        now=UTC_NOW,
    )

    assert result.status == "insufficient"
    assert "capacity_history_insufficient" in result.data_gaps
    assert result.curve == []


def test_theil_sen_capacity_forecast_returns_30_ordered_quantile_points_and_three_dates():
    from services import forecastIncidentService as analytics

    points = [
        (UTC_NOW - timedelta(days=44 - day), 10.0 + day)
        for day in range(45)
    ]
    result = analytics.build_capacity_forecast(
        _asset(),
        points=points,
        hard_limit=60.0,
        now=UTC_NOW,
    )

    assert result.status == "ready"
    assert len(result.curve) == 30
    assert all(point.p10 <= point.p50 <= point.p90 for point in result.curve)
    assert result.exhaustion_dates.p10 is not None
    assert result.exhaustion_dates.p50 is not None
    assert result.exhaustion_dates.p90 is not None


def test_performance_requires_three_consecutive_robust_z_scores_and_ignores_isolated_spike():
    from services import forecastIncidentService as analytics

    assert analytics.qualifies_performance_anomaly([3.6]) is False
    assert analytics.qualifies_performance_anomaly([3.6, 3.7]) is False
    assert analytics.qualifies_performance_anomaly([3.6, 3.7, 3.8]) is True
    assert analytics.robust_z_score(value=9.0, median=1.0, mad=0.0) == 100.0


def test_diagnosis_uses_fixed_weights_independent_evidence_and_high_confidence_gate():
    from services import forecastIncidentService as analytics

    diagnosis = analytics.build_diagnosis(
        incident_id=1,
        evidences=[
            analytics.DiagnosisEvidence("forecast_exhaustion", "forecast-1", UTC_NOW),
            analytics.DiagnosisEvidence("hard_limit_alert", "alert-1", UTC_NOW),
            analytics.DiagnosisEvidence("high_usage", "usage-1", UTC_NOW),
        ],
        high_confidence_enabled=True,
    )

    candidate = diagnosis.candidates[0]
    assert candidate.category == "capacity_pressure"
    assert candidate.score == 1.0
    assert diagnosis.confidence == "high"


def test_incident_state_machine_rejects_skips_and_allows_system_reopen():
    from services import forecastIncidentService as analytics

    assert analytics.can_transition_incident("open", "acknowledged") is True
    assert analytics.can_transition_incident("open", "investigating") is False
    assert analytics.can_transition_incident("resolved", "open", system_reopen=True) is True


def test_incident_evidence_deduplicates_and_resolved_incident_reopens_within_24_hours(db_session):
    import models
    from services import forecastIncidentService as analytics

    cluster = models.StorageCluster(id=7, name="cluster-7", storage_type="netapp")
    project = models.Project(id=1, name="project-alpha")
    db_session.add_all([cluster, project])
    db_session.commit()

    envelope = analytics.TelemetryEnvelope(
        asset_ref=_asset(),
        source="storage_alert",
        source_ref="netapp:123",
        observed_at=UTC_NOW,
        collected_at=UTC_NOW,
        metric_or_event="vendor_event",
        value={"severity": "critical"},
        quality="good",
    )
    created = analytics.correlate_incident(db_session, envelope, category="device_fault")
    db_session.commit()
    assert created.created is True

    duplicate = analytics.correlate_incident(db_session, envelope, category="device_fault")
    db_session.commit()
    assert duplicate.created is False
    assert duplicate.incident.id == created.incident.id

    created.incident.status = "resolved"
    created.incident.resolved_at = UTC_NOW
    db_session.commit()
    reopened = analytics.correlate_incident(
        db_session,
        envelope.model_copy(update={"source_ref": "netapp:124", "observed_at": UTC_NOW + timedelta(hours=1)}),
        category="device_fault",
    )
    assert reopened.reopened is True
    assert reopened.incident.status == "open"


@pytest.mark.parametrize("next_status", ["investigating", "resolved"])
def test_invalid_state_transition_is_a_conflict(next_status):
    from services import forecastIncidentService as analytics

    with pytest.raises(ValueError, match="invalid incident status transition"):
        analytics.require_incident_transition("open", next_status)
