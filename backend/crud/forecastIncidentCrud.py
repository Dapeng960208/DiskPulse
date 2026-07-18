# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import AnomalyObservation, CapacityForecast, Diagnosis, Incident, IncidentEvidence, IncidentTimeline


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
        statement.order_by(Incident.updated_at.desc(), Incident.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()
    return rows, int(total)


def get_incident(db: Session, incident_id: int) -> Incident | None:
    return db.get(Incident, incident_id)


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
        .order_by(IncidentTimeline.occurred_at.asc(), IncidentTimeline.id.asc())
    ).scalars().all()


def latest_diagnosis(db: Session, incident_id: int) -> Diagnosis | None:
    return db.execute(
        select(Diagnosis)
        .where(Diagnosis.incident_id == incident_id)
        .order_by(Diagnosis.created_at.desc(), Diagnosis.id.desc())
        .limit(1)
    ).scalar_one_or_none()


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
