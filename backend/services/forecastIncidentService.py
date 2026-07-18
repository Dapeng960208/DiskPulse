# -*- coding: utf-8 -*-
"""Deterministic storage-health analytics primitives and incident correlation."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import numpy as np
from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from crud import forecastIncidentCrud
from models import Incident, IncidentEvidence, IncidentTimeline, MaintenanceWindow
from services import audit_service, project_access_service
from utils.auth_service import is_super_admin


ALGORITHM_VERSION = "forecast-incident-v1"
FORECAST_DAYS = 30
FORECAST_TRAINING_DAYS = 45
MIN_VALID_DAYS = 30
MIN_COVERAGE = 0.80
ROBUST_Z_THRESHOLD = 3.5
ZERO_MAD_SCORE = 100.0
INCIDENT_STATES = ("open", "acknowledged", "investigating", "mitigated", "resolved")
INCIDENT_CATEGORIES = (
    "capacity_pressure",
    "device_fault",
    "performance_contention",
    "telemetry_blindspot",
)
_NEXT_STATE = dict(zip(INCIDENT_STATES, INCIDENT_STATES[1:]))
_PRIORITY = {category: index for index, category in enumerate(INCIDENT_CATEGORIES)}
_WEIGHTS = {
    "capacity_pressure": {
        "forecast_exhaustion": 0.45,
        "hard_limit_alert": 0.35,
        "soft_limit_alert": 0.35,
        "high_usage": 0.20,
    },
    "device_fault": {
        "severe_vendor_event": 0.50,
        "repeated_fingerprint": 0.25,
        "collection_error": 0.15,
    },
    "performance_contention": {
        "continuous_performance_anomaly": 0.45,
        "throughput_iops_deviation": 0.30,
        "workload_overlap": 0.25,
    },
    "telemetry_blindspot": {
        "telemetry_stale": 0.60,
        "collection_failure": 0.25,
        "coverage_insufficient": 0.15,
    },
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("analytics timestamps must include a timezone")
    return value.astimezone(timezone.utc)


class AssetRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_type: Literal["storage_cluster", "volume", "qtree", "group", "storage_usage"]
    asset_id: str
    storage_cluster_id: int
    project_id: int | None = None
    vendor: str
    display_name: str


class TelemetryEnvelope(BaseModel):
    asset_ref: AssetRef
    source: str = Field(min_length=1, max_length=64)
    source_ref: str = Field(min_length=1, max_length=255)
    observed_at: datetime
    collected_at: datetime
    metric_or_event: str = Field(min_length=1, max_length=64)
    value: Any
    quality: str = Field(min_length=1, max_length=32)


class ForecastPoint(BaseModel):
    observed_at: datetime
    p10: float
    p50: float
    p90: float


class ExhaustionDates(BaseModel):
    p10: datetime | None = None
    p50: datetime | None = None
    p90: datetime | None = None


class ForecastResult(BaseModel):
    asset_ref: AssetRef
    status: Literal["ready", "insufficient"]
    curve: list[ForecastPoint] = Field(default_factory=list)
    exhaustion_dates: ExhaustionDates = Field(default_factory=ExhaustionDates)
    data_gaps: list[str] = Field(default_factory=list)
    coverage_ratio: float
    algorithm_version: str = ALGORITHM_VERSION


class TelemetryQualityResult(BaseModel):
    status: Literal["ready", "insufficient", "stale", "unknown"]
    coverage_ratio: float
    latest_point_at: datetime | None
    authoritative_last_success_at: None = None
    data_gaps: list[str] = Field(default_factory=list)


class DiagnosisEvidence(BaseModel):
    evidence_type: str
    evidence_ref: str
    observed_at: datetime
    data_gaps: list[str] = Field(default_factory=list)
    conflicting: bool = False


class DiagnosisCandidate(BaseModel):
    category: str
    score: float
    evidence_refs: list[str]
    independent_evidence_types: int
    data_gaps: list[str] = Field(default_factory=list)


class DiagnosisResult(BaseModel):
    incident_id: int
    algorithm_version: str = ALGORITHM_VERSION
    candidates: list[DiagnosisCandidate]
    confidence: Literal["high", "medium", "low", "insufficient"]
    evidence_ids: list[str]
    data_gaps: list[str]


@dataclass(frozen=True)
class CorrelationResult:
    incident: Incident
    created: bool
    reopened: bool


def build_capacity_forecast(
    asset_ref: AssetRef,
    *,
    points: list[tuple[datetime, float]],
    hard_limit: float,
    now: datetime,
) -> ForecastResult:
    """Build a 30-day Theil-Sen forecast from UTC daily maxima."""
    now = _utc(now)
    daily: dict[datetime.date, tuple[datetime, float]] = {}
    cutoff = now.date() - timedelta(days=FORECAST_TRAINING_DAYS - 1)
    for observed_at, value in points:
        observed_at = _utc(observed_at)
        if observed_at.date() < cutoff:
            continue
        prior = daily.get(observed_at.date())
        if prior is None or value > prior[1]:
            daily[observed_at.date()] = (observed_at, float(value))

    ordered = [daily[key] for key in sorted(daily)]
    coverage_ratio = len(ordered) / FORECAST_TRAINING_DAYS
    if len(ordered) < MIN_VALID_DAYS or coverage_ratio < MIN_COVERAGE:
        return ForecastResult(
            asset_ref=asset_ref,
            status="insufficient",
            coverage_ratio=coverage_ratio,
            data_gaps=["capacity_history_insufficient"],
        )

    x = np.array([(item[0].date() - ordered[0][0].date()).days for item in ordered], dtype=float)
    y = np.array([item[1] for item in ordered], dtype=float)
    deltas = y[np.newaxis, :] - y[:, np.newaxis]
    distances = x[np.newaxis, :] - x[:, np.newaxis]
    slopes = deltas[np.triu_indices_from(deltas, k=1)] / distances[np.triu_indices_from(distances, k=1)]
    slope = float(np.median(slopes))
    intercept = float(np.median(y - slope * x))
    residuals = y - (intercept + slope * x)
    residual_quantiles = np.quantile(residuals, [0.1, 0.5, 0.9])
    last_day = ordered[-1][0].date()
    curves: list[ForecastPoint] = []
    for day in range(1, FORECAST_DAYS + 1):
        future_day = last_day + timedelta(days=day)
        future_x = (future_day - ordered[0][0].date()).days
        center = intercept + slope * future_x
        p10, p50, p90 = sorted(float(center + offset) for offset in residual_quantiles)
        curves.append(
            ForecastPoint(
                observed_at=datetime.combine(future_day, datetime.min.time(), tzinfo=timezone.utc),
                p10=max(0.0, p10),
                p50=max(0.0, p50),
                p90=max(0.0, p90),
            )
        )

    def first_exhaustion(key: str) -> datetime | None:
        return next((point.observed_at for point in curves if getattr(point, key) >= hard_limit), None)

    return ForecastResult(
        asset_ref=asset_ref,
        status="ready",
        curve=curves,
        exhaustion_dates=ExhaustionDates(
            p10=first_exhaustion("p10"),
            p50=first_exhaustion("p50"),
            p90=first_exhaustion("p90"),
        ),
        coverage_ratio=coverage_ratio,
    )


def evaluate_telemetry_quality(
    *,
    component: Literal["capacity", "vendor_events", "performance"],
    latest_success_at: datetime | None,
    latest_point_at: datetime | None,
    observed_points: int,
    expected_points: int,
    now: datetime,
) -> TelemetryQualityResult:
    """Summarise quality without duplicating the collection-run success authority."""
    now = _utc(now)
    latest_point_at = _utc(latest_point_at) if latest_point_at is not None else None
    coverage_ratio = 0.0 if expected_points <= 0 else round(observed_points / expected_points, 4)
    if latest_success_at is None:
        return TelemetryQualityResult(
            status="unknown",
            coverage_ratio=coverage_ratio,
            latest_point_at=latest_point_at,
            data_gaps=["telemetry_success_unknown"],
        )
    latest_success_at = _utc(latest_success_at)
    threshold = {"capacity": 150, "vendor_events": 150, "performance": 630}[component]
    gaps: list[str] = []
    if (now - latest_success_at).total_seconds() > threshold:
        gaps.append("telemetry_stale")
        quality_status: Literal["ready", "insufficient", "stale", "unknown"] = "stale"
    elif coverage_ratio < MIN_COVERAGE:
        gaps.append("coverage_insufficient")
        quality_status = "insufficient"
    else:
        quality_status = "ready"
    if latest_point_at is None:
        gaps.append("latest_point_missing")
        quality_status = "insufficient" if quality_status == "ready" else quality_status
    return TelemetryQualityResult(
        status=quality_status,
        coverage_ratio=coverage_ratio,
        latest_point_at=latest_point_at,
        data_gaps=gaps,
    )


def robust_z_score(*, value: float, median: float, mad: float) -> float:
    if mad == 0:
        return 0.0 if value == median else (ZERO_MAD_SCORE if value > median else -ZERO_MAD_SCORE)
    return max(-ZERO_MAD_SCORE, min(ZERO_MAD_SCORE, 0.67448975 * (value - median) / mad))


def qualifies_performance_anomaly(scores: list[float]) -> bool:
    return len(scores) >= 3 and all(abs(score) >= ROBUST_Z_THRESHOLD for score in scores[-3:])


def build_diagnosis(
    *,
    incident_id: int,
    evidences: list[DiagnosisEvidence],
    high_confidence_enabled: bool,
) -> DiagnosisResult:
    candidates: list[DiagnosisCandidate] = []
    all_gaps = sorted({gap for evidence in evidences for gap in evidence.data_gaps})
    for category, weights in _WEIGHTS.items():
        selected: dict[str, tuple[DiagnosisEvidence, float]] = {}
        conflict = False
        for evidence in evidences:
            weight = weights.get(evidence.evidence_type)
            if weight is None:
                continue
            current = selected.get(evidence.evidence_type)
            if current is None or weight > current[1]:
                selected[evidence.evidence_type] = (evidence, weight)
            conflict = conflict or evidence.conflicting
        if not selected:
            continue
        score = min(1.0, sum(weight for _, weight in selected.values()))
        gaps = list(all_gaps)
        if conflict:
            score = max(0.0, score - 0.20)
            gaps.append("conflicting_evidence")
        references = [item[0].evidence_ref for item in selected.values()]
        newest = max(item[0].observed_at for item in selected.values())
        candidates.append(
            DiagnosisCandidate(
                category=category,
                score=round(score, 2),
                evidence_refs=references,
                independent_evidence_types=len(selected),
                data_gaps=sorted(set(gaps)),
            )
        )
        # Store sort metadata without exposing it in the public schema.
        candidates[-1].__dict__["_newest"] = newest

    candidates.sort(
        key=lambda item: (
            -item.score,
            -item.independent_evidence_types,
            -item.__dict__.get("_newest", datetime.min.replace(tzinfo=timezone.utc)).timestamp(),
            _PRIORITY[item.category],
        )
    )
    candidates = candidates[:3]
    for candidate in candidates:
        candidate.__dict__.pop("_newest", None)
    lead = candidates[0] if candidates else None
    confidence: Literal["high", "medium", "low", "insufficient"]
    if lead is None:
        confidence = "insufficient"
    elif high_confidence_enabled and lead.score >= 0.8 and lead.independent_evidence_types >= 2:
        confidence = "high"
    elif lead.score >= 0.5:
        confidence = "medium"
    else:
        confidence = "low"
    return DiagnosisResult(
        incident_id=incident_id,
        candidates=candidates,
        confidence=confidence,
        evidence_ids=[evidence.evidence_ref for evidence in evidences],
        data_gaps=all_gaps,
    )


def can_transition_incident(current: str, target: str, *, system_reopen: bool = False) -> bool:
    if system_reopen and current == "resolved" and target == "open":
        return True
    return _NEXT_STATE.get(current) == target


def require_incident_transition(current: str, target: str, *, system_reopen: bool = False) -> None:
    if not can_transition_incident(current, target, system_reopen=system_reopen):
        raise ValueError("invalid incident status transition")


def _bucket_start(observed_at: datetime) -> datetime:
    observed_at = _utc(observed_at)
    return observed_at.replace(minute=observed_at.minute - observed_at.minute % 30, second=0, microsecond=0)


def _correlation_key(asset_ref: AssetRef, category: str) -> str:
    return ":".join((str(asset_ref.storage_cluster_id), asset_ref.asset_type, asset_ref.asset_id, category))


def _severity(envelope: TelemetryEnvelope) -> str:
    if isinstance(envelope.value, dict):
        raw = str(envelope.value.get("severity") or "warning").lower()
        return "critical" if raw in {"critical", "emergency", "alert"} else raw
    return "warning"


def _append_evidence(db, incident: Incident, envelope: TelemetryEnvelope) -> None:
    evidence = IncidentEvidence(
        incident_id=incident.id,
        source=envelope.source,
        source_ref=envelope.source_ref,
        evidence_type=envelope.metric_or_event,
        observed_at=_utc(envelope.observed_at),
        data_gaps=[] if envelope.quality == "good" else [f"quality_{envelope.quality}"],
        evidence_hash=hashlib.sha256(f"{envelope.source}:{envelope.source_ref}".encode("utf-8")).hexdigest(),
    )
    db.add(evidence)
    db.add(IncidentTimeline(incident_id=incident.id, event_type="evidence_added"))


def correlate_incident(db, envelope: TelemetryEnvelope, *, category: str) -> CorrelationResult:
    if category not in INCIDENT_CATEGORIES:
        raise ValueError("unsupported incident category")
    existing_evidence = db.query(IncidentEvidence).filter(
        IncidentEvidence.source == envelope.source,
        IncidentEvidence.source_ref == envelope.source_ref,
    ).one_or_none()
    if existing_evidence is not None:
        incident = db.get(Incident, existing_evidence.incident_id)
        return CorrelationResult(incident=incident, created=False, reopened=False)

    asset = envelope.asset_ref
    observed_at = _utc(envelope.observed_at)
    correlation_key = _correlation_key(asset, category)
    incident = db.query(Incident).filter(
        Incident.correlation_key == correlation_key,
        Incident.correlation_bucket_at == _bucket_start(observed_at),
    ).one_or_none()
    created = False
    reopened = False
    if incident is None:
        incident = db.query(Incident).filter(
            Incident.correlation_key == correlation_key,
            Incident.status == "resolved",
            Incident.resolved_at >= observed_at - timedelta(hours=24),
        ).order_by(Incident.resolved_at.desc()).first()
        if incident is not None:
            require_incident_transition("resolved", "open", system_reopen=True)
            incident.status = "open"
            incident.resolved_at = None
            incident.last_evidence_at = observed_at
            db.add(IncidentTimeline(incident_id=incident.id, event_type="reopened", from_status="resolved", to_status="open"))
            reopened = True
        else:
            incident = Incident(
                correlation_key=correlation_key,
                correlation_bucket_at=_bucket_start(observed_at),
                asset_type=asset.asset_type,
                asset_id=asset.asset_id,
                storage_cluster_id=asset.storage_cluster_id,
                project_id=asset.project_id,
                vendor=asset.vendor,
                display_name=asset.display_name,
                category=category,
                severity=_severity(envelope),
                opened_at=observed_at,
                last_evidence_at=observed_at,
            )
            db.add(incident)
            db.flush()
            db.add(IncidentTimeline(incident_id=incident.id, event_type="created", to_status="open"))
            created = True
    else:
        incident.last_evidence_at = observed_at
        if _severity(envelope) == "critical":
            incident.severity = "critical"
    _append_evidence(db, incident, envelope)
    db.flush()
    return CorrelationResult(incident=incident, created=created, reopened=reopened)


def visible_project_ids(db, current_user) -> set[int] | None:
    return project_access_service.accessible_project_ids(db, current_user)


def require_visible_incident(db, current_user, incident_id: int, minimum_role: str = "reader") -> Incident:
    incident = forecastIncidentCrud.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident was not found")
    if incident.project_id is None:
        if not is_super_admin(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="project permission required")
        return incident
    project_access_service.require_project_permission(db, current_user, incident.project_id, minimum_role)
    return incident


def list_visible_incidents(
    db,
    *,
    current_user,
    page: int,
    size: int,
    storage_cluster_id: int | None = None,
    incident_status: str | None = None,
    category: str | None = None,
) -> tuple[list[Incident], int]:
    return forecastIncidentCrud.list_incidents(
        db,
        visible_project_ids=visible_project_ids(db, current_user),
        page=page,
        size=size,
        storage_cluster_id=storage_cluster_id,
        status=incident_status,
        category=category,
    )


def incident_detail(db, *, current_user, incident_id: int) -> tuple[Incident, list[IncidentEvidence], list[IncidentTimeline], Any]:
    incident = require_visible_incident(db, current_user, incident_id)
    return (
        incident,
        forecastIncidentCrud.list_incident_evidence(db, incident.id),
        forecastIncidentCrud.list_incident_timeline(db, incident.id),
        forecastIncidentCrud.latest_diagnosis(db, incident.id),
    )


def _append_mutation_audit(db, *, audit_context, current_user, incident: Incident, action: str, before: dict, after: dict) -> None:
    if audit_context is None:
        return
    audit_service.append_audit_event(
        db,
        context=audit_context,
        phase="result",
        action=action,
        resource_type="incident",
        resource_id=incident.id,
        project_id=incident.project_id,
        outcome="success",
        before_summary=before,
        after_summary=after,
    )


def update_incident(
    db,
    *,
    current_user,
    incident_id: int,
    target_status: str | None = None,
    claim: bool | None = None,
    silenced_until: datetime | None = None,
    silence_reason: str | None = None,
    audit_context=None,
) -> Incident:
    incident = require_visible_incident(db, current_user, incident_id, "editor")
    before = {"status": incident.status, "assigned_user_id": incident.assigned_user_id, "silenced_until": incident.silenced_until}
    changed = False
    if target_status is not None:
        require_incident_transition(incident.status, target_status)
        old_status = incident.status
        incident.status = target_status
        incident.resolved_at = _utc(datetime.now(timezone.utc)) if target_status == "resolved" else None
        db.add(IncidentTimeline(
            incident_id=incident.id,
            event_type="status_changed",
            actor_user_id=current_user.id,
            from_status=old_status,
            to_status=target_status,
        ))
        changed = True
    if claim is True:
        incident.assigned_user_id = current_user.id
        db.add(IncidentTimeline(incident_id=incident.id, event_type="claimed", actor_user_id=current_user.id))
        changed = True
    elif claim is False:
        if incident.assigned_user_id not in (None, current_user.id) and not is_super_admin(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only the assignee can release this incident")
        incident.assigned_user_id = None
        db.add(IncidentTimeline(incident_id=incident.id, event_type="released", actor_user_id=current_user.id))
        changed = True
    if silenced_until is not None:
        incident.silenced_until = _utc(silenced_until)
        incident.silence_reason = silence_reason
        db.add(IncidentTimeline(incident_id=incident.id, event_type="silenced", actor_user_id=current_user.id))
        changed = True
    elif silence_reason is not None:
        incident.silenced_until = None
        incident.silence_reason = None
        db.add(IncidentTimeline(incident_id=incident.id, event_type="unsilenced", actor_user_id=current_user.id))
        changed = True
    if not changed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="no incident update supplied")
    _append_mutation_audit(
        db,
        audit_context=audit_context,
        current_user=current_user,
        incident=incident,
        action="incident.update",
        before=before,
        after={"status": incident.status, "assigned_user_id": incident.assigned_user_id, "silenced_until": incident.silenced_until},
    )
    db.commit()
    db.refresh(incident)
    return incident


def add_comment(db, *, current_user, incident_id: int, content: str, audit_context=None) -> IncidentTimeline:
    incident = require_visible_incident(db, current_user, incident_id, "editor")
    timeline = IncidentTimeline(
        incident_id=incident.id,
        event_type="commented",
        actor_user_id=current_user.id,
        comment=content,
    )
    db.add(timeline)
    _append_mutation_audit(
        db,
        audit_context=audit_context,
        current_user=current_user,
        incident=incident,
        action="incident.comment",
        before={},
        after={"comment_length": len(content)},
    )
    db.commit()
    db.refresh(timeline)
    return timeline


def create_maintenance_window(
    db,
    *,
    current_user,
    project_id: int | None,
    storage_cluster_id: int | None,
    asset_type: str | None,
    asset_id: str | None,
    starts_at: datetime,
    ends_at: datetime,
    reason: str,
    audit_context=None,
) -> MaintenanceWindow:
    starts_at, ends_at = _utc(starts_at), _utc(ends_at)
    if starts_at >= ends_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="maintenance window end must follow start")
    if project_id is None and not is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super admin permission required")
    if project_id is not None:
        project_access_service.require_project_permission(db, current_user, project_id, "project_admin")
    window = MaintenanceWindow(
        project_id=project_id,
        storage_cluster_id=storage_cluster_id,
        asset_type=asset_type,
        asset_id=asset_id,
        starts_at=starts_at,
        ends_at=ends_at,
        reason=reason,
        created_by=current_user.id,
    )
    db.add(window)
    db.flush()
    if audit_context is not None:
        audit_service.append_audit_event(
            db,
            context=audit_context,
            phase="result",
            action="maintenance_window.create",
            resource_type="maintenance_window",
            resource_id=window.id,
            project_id=project_id,
            outcome="success",
            after_summary={"starts_at": starts_at, "ends_at": ends_at, "storage_cluster_id": storage_cluster_id},
        )
    db.commit()
    db.refresh(window)
    return window
