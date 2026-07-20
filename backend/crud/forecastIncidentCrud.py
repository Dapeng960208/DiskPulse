# -*- coding: utf-8 -*-
from datetime import datetime

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models import (
    AnomalyObservation,
    CapacityForecast,
    Diagnosis,
    Incident,
    IncidentEvidence,
    IncidentTimeline,
    MaintenanceWindow,
    TelemetryQualitySnapshot,
)


def list_incidents(
    db: Session,
    *,
    visible_project_ids: set[int] | None,
    page: int,
    size: int,
    storage_cluster_id: int | None = None,
    status: str | None = None,
    category: str | None = None,
) -> tuple[list[Incident], int]:
    statement = select(Incident)
    if visible_project_ids is not None:
        statement = statement.where(Incident.project_id.in_(visible_project_ids))
    if storage_cluster_id is not None:
        statement = statement.where(Incident.storage_cluster_id == storage_cluster_id)
    if status is not None:
        statement = statement.where(Incident.status == status)
    if category is not None:
        statement = statement.where(Incident.category == category)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.execute(
        statement.order_by(
            Incident.last_evidence_at.desc(),
            Incident.opened_at.desc(),
            Incident.id.desc(),
        )
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()
    return rows, int(total)


def list_resource_incidents(db: Session, *, asset_type: str, asset_id: str, limit: int = 5) -> list[Incident]:
    return db.execute(
        select(Incident)
        .where(Incident.asset_type == asset_type, Incident.asset_id == asset_id)
        .order_by(Incident.updated_at.desc(), Incident.id.desc())
        .limit(limit)
    ).scalars().all()


def get_incident(db: Session, incident_id: int) -> Incident | None:
    return db.get(Incident, incident_id)


def get_incident_evidence_by_source_ref(
    db: Session, *, source: str, source_ref: str
) -> IncidentEvidence | None:
    return db.execute(
        select(IncidentEvidence).where(
            IncidentEvidence.source == source,
            IncidentEvidence.source_ref == source_ref,
        )
    ).scalar_one_or_none()


def get_incident_by_correlation_bucket(
    db: Session, *, correlation_key: str, correlation_bucket_at: datetime
) -> Incident | None:
    return db.execute(
        select(Incident).where(
            Incident.correlation_key == correlation_key,
            Incident.correlation_bucket_at == correlation_bucket_at,
        )
    ).scalar_one_or_none()


def get_recent_resolved_incident(
    db: Session, *, correlation_key: str, resolved_since: datetime
) -> Incident | None:
    return db.execute(
        select(Incident)
        .where(
            Incident.correlation_key == correlation_key,
            Incident.status == "resolved",
            Incident.resolved_at >= resolved_since,
        )
        .order_by(Incident.resolved_at.desc(), Incident.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def add_incident(db: Session, incident: Incident) -> Incident:
    db.add(incident)
    db.flush()
    return incident


def add_incident_evidence(db: Session, evidence: IncidentEvidence) -> IncidentEvidence:
    db.add(evidence)
    db.flush()
    return evidence


def add_incident_timeline(db: Session, timeline: IncidentTimeline) -> IncidentTimeline:
    db.add(timeline)
    db.flush()
    return timeline


def matching_maintenance_window(
    db: Session,
    *,
    project_id: int | None,
    storage_cluster_id: int,
    asset_type: str,
    asset_id: str,
    observed_at: datetime,
) -> MaintenanceWindow | None:
    """Return the narrowest active window that applies to the derived Incident."""
    project_condition = (
        MaintenanceWindow.project_id.is_(None)
        if project_id is None
        else MaintenanceWindow.project_id.in_((None, project_id))
    )
    return db.execute(
        select(MaintenanceWindow)
        .where(
            project_condition,
            MaintenanceWindow.starts_at <= observed_at,
            MaintenanceWindow.ends_at >= observed_at,
            or_(
                MaintenanceWindow.storage_cluster_id.is_(None),
                MaintenanceWindow.storage_cluster_id == storage_cluster_id,
            ),
            or_(MaintenanceWindow.asset_type.is_(None), MaintenanceWindow.asset_type == asset_type),
            or_(MaintenanceWindow.asset_id.is_(None), MaintenanceWindow.asset_id == asset_id),
        )
        .order_by(
            MaintenanceWindow.asset_id.is_not(None).desc(),
            MaintenanceWindow.storage_cluster_id.is_not(None).desc(),
            MaintenanceWindow.id.desc(),
        )
        .limit(1)
    ).scalar_one_or_none()


def list_incident_evidence(db: Session, incident_id: int) -> list[IncidentEvidence]:
    return db.execute(
        select(IncidentEvidence)
        .where(IncidentEvidence.incident_id == incident_id)
        .order_by(IncidentEvidence.observed_at.desc(), IncidentEvidence.id.desc())
    ).scalars().all()


def list_incident_timeline(db: Session, incident_id: int) -> list[IncidentTimeline]:
    return db.execute(
        select(IncidentTimeline)
        .where(IncidentTimeline.incident_id == incident_id)
        .order_by(IncidentTimeline.occurred_at.desc(), IncidentTimeline.id.desc())
    ).scalars().all()


def latest_diagnosis(db: Session, incident_id: int) -> Diagnosis | None:
    return db.execute(
        select(Diagnosis)
        .where(Diagnosis.incident_id == incident_id)
        .order_by(Diagnosis.created_at.desc(), Diagnosis.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_diagnosis_by_digest(
    db: Session, *, incident_id: int, algorithm_version: str, evidence_digest: str
) -> Diagnosis | None:
    return db.execute(
        select(Diagnosis).where(
            Diagnosis.incident_id == incident_id,
            Diagnosis.algorithm_version == algorithm_version,
            Diagnosis.evidence_digest == evidence_digest,
        )
    ).scalar_one_or_none()


def add_diagnosis(db: Session, diagnosis: Diagnosis) -> Diagnosis:
    db.add(diagnosis)
    db.flush()
    return diagnosis


def add_telemetry_quality_snapshot(db: Session, snapshot) -> None:
    db.add(snapshot)


def get_telemetry_quality_snapshot(
    db: Session,
    *,
    asset_type: str,
    asset_id: str,
    period: str,
    algorithm_version: str,
    calculated_at: datetime,
) -> TelemetryQualitySnapshot | None:
    return db.execute(
        select(TelemetryQualitySnapshot).where(
            TelemetryQualitySnapshot.asset_type == asset_type,
            TelemetryQualitySnapshot.asset_id == asset_id,
            TelemetryQualitySnapshot.period == period,
            TelemetryQualitySnapshot.algorithm_version == algorithm_version,
            TelemetryQualitySnapshot.calculated_at == calculated_at,
        )
    ).scalar_one_or_none()


def get_capacity_forecast(
    db: Session,
    *,
    asset_type: str,
    asset_id: str,
    training_end: datetime,
    algorithm_version: str,
) -> CapacityForecast | None:
    return db.execute(
        select(CapacityForecast).where(
            CapacityForecast.asset_type == asset_type,
            CapacityForecast.asset_id == asset_id,
            CapacityForecast.training_end == training_end,
            CapacityForecast.algorithm_version == algorithm_version,
        )
    ).scalar_one_or_none()


def add_capacity_forecast(db: Session, forecast: CapacityForecast) -> CapacityForecast:
    db.add(forecast)
    db.flush()
    return forecast


def get_anomaly_observation(
    db: Session,
    *,
    source: str,
    source_ref: str,
    metric: str,
    algorithm_version: str,
) -> AnomalyObservation | None:
    return db.execute(
        select(AnomalyObservation).where(
            AnomalyObservation.source == source,
            AnomalyObservation.source_ref == source_ref,
            AnomalyObservation.metric == metric,
            AnomalyObservation.algorithm_version == algorithm_version,
        )
    ).scalar_one_or_none()


def add_anomaly_observation(db: Session, observation: AnomalyObservation) -> AnomalyObservation:
    db.add(observation)
    db.flush()
    return observation


def list_forecasts(
    db: Session,
    *,
    visible_project_ids: set[int] | None,
    page: int,
    size: int,
    storage_cluster_id: int | None = None,
) -> tuple[list[CapacityForecast], int]:
    statement = select(CapacityForecast)
    if visible_project_ids is not None:
        statement = statement.where(CapacityForecast.project_id.in_(visible_project_ids))
    if storage_cluster_id is not None:
        statement = statement.where(CapacityForecast.storage_cluster_id == storage_cluster_id)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.execute(
        statement.order_by(CapacityForecast.created_at.desc(), CapacityForecast.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()
    return rows, int(total)


def list_anomalies(
    db: Session,
    *,
    visible_project_ids: set[int] | None,
    page: int,
    size: int,
    storage_cluster_id: int | None = None,
    metric: str | None = None,
    observed_from: datetime | None = None,
    observed_to: datetime | None = None,
) -> tuple[list[AnomalyObservation], int]:
    statement = select(AnomalyObservation)
    if visible_project_ids is not None:
        statement = statement.where(AnomalyObservation.project_id.in_(visible_project_ids))
    if storage_cluster_id is not None:
        statement = statement.where(AnomalyObservation.storage_cluster_id == storage_cluster_id)
    if metric is not None:
        statement = statement.where(AnomalyObservation.metric == metric)
    if observed_from is not None:
        statement = statement.where(AnomalyObservation.observed_at >= observed_from)
    if observed_to is not None:
        statement = statement.where(AnomalyObservation.observed_at <= observed_to)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.execute(
        statement.order_by(AnomalyObservation.observed_at.desc(), AnomalyObservation.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()
    return rows, int(total)
