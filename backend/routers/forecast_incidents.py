# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session

from crud import forecastIncidentCrud
from dependencies import CurrentUserDep, get_db
from schemas.forecastIncidentSchema import (
    AnomalyOut,
    AnomalyPage,
    DiagnosisOut,
    DiagnosisToolOut,
    ForecastOut,
    ForecastPage,
    IncidentCommentCreate,
    IncidentDetailOut,
    IncidentEvidenceOut,
    IncidentOut,
    IncidentPage,
    IncidentPatch,
    IncidentTimelineOut,
    MaintenanceWindowCreate,
)
from services import audit_service, forecastIncidentService


router = APIRouter(prefix="/v1", tags=["forecast-incidents"])
DBDep = Annotated[Session, Depends(get_db)]


def _utc_or_422(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{name} must include a UTC offset")
    return value.astimezone(timezone.utc)


def _incident_detail(db: Session, current_user, incident_id: int) -> IncidentDetailOut:
    incident, evidence, timeline, diagnosis = forecastIncidentService.incident_detail(
        db, current_user=current_user, incident_id=incident_id
    )
    return IncidentDetailOut(
        **_incident_out(db, current_user, incident).model_dump(),
        evidence=[IncidentEvidenceOut.model_validate(item) for item in evidence],
        timeline=[IncidentTimelineOut.model_validate(item) for item in timeline],
        diagnosis=DiagnosisOut.model_validate(diagnosis) if diagnosis is not None else None,
    )


def _incident_out(db: Session, current_user, incident) -> IncidentOut:
    return IncidentOut(
        **IncidentOut.model_validate(incident).model_dump(exclude={"capabilities"}),
        capabilities=forecastIncidentService.incident_capabilities(
            db, current_user=current_user, incident=incident
        ),
    )


@router.get("/forecasts", response_model=ForecastPage)
def list_forecasts(
    current_user: CurrentUserDep,
    db: DBDep,
    storage_cluster_id: Annotated[int | None, Query(ge=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ForecastPage:
    rows, total = forecastIncidentCrud.list_forecasts(
        db,
        visible_project_ids=forecastIncidentService.visible_project_ids(db, current_user),
        storage_cluster_id=storage_cluster_id,
        page=page,
        size=size,
    )
    return ForecastPage(content=[ForecastOut.model_validate(row) for row in rows], total=total)


@router.get("/anomalies", response_model=AnomalyPage)
def list_anomalies(
    current_user: CurrentUserDep,
    db: DBDep,
    storage_cluster_id: Annotated[int | None, Query(ge=1)] = None,
    metric: Annotated[str | None, Query(max_length=32)] = None,
    observed_from: Annotated[datetime | None, Query()] = None,
    observed_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AnomalyPage:
    observed_from = _utc_or_422(observed_from, "observed_from")
    observed_to = _utc_or_422(observed_to, "observed_to")
    if observed_from is not None and observed_to is not None and observed_from > observed_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="observed_from must not exceed observed_to")
    rows, total = forecastIncidentCrud.list_anomalies(
        db,
        visible_project_ids=forecastIncidentService.visible_project_ids(db, current_user),
        storage_cluster_id=storage_cluster_id,
        metric=metric,
        observed_from=observed_from,
        observed_to=observed_to,
        page=page,
        size=size,
    )
    return AnomalyPage(content=[AnomalyOut.model_validate(row) for row in rows], total=total)


@router.get("/incidents", response_model=IncidentPage)
def list_incidents(
    current_user: CurrentUserDep,
    db: DBDep,
    storage_cluster_id: Annotated[int | None, Query(ge=1)] = None,
    incident_status: Annotated[str | None, Query(alias="status", max_length=16)] = None,
    category: Annotated[str | None, Query(max_length=32)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> IncidentPage:
    rows, total = forecastIncidentService.list_visible_incidents(
        db,
        current_user=current_user,
        storage_cluster_id=storage_cluster_id,
        incident_status=incident_status,
        category=category,
        page=page,
        size=size,
    )
    return IncidentPage(content=[_incident_out(db, current_user, row) for row in rows], total=total)


@router.get("/incidents/{incident_id}", response_model=IncidentDetailOut)
def get_incident(incident_id: Annotated[int, Path(ge=1)], current_user: CurrentUserDep, db: DBDep) -> IncidentDetailOut:
    return _incident_detail(db, current_user, incident_id)


@router.get(
    "/incidents/{incident_id}/diagnosis",
    response_model=DiagnosisToolOut,
    openapi_extra={
        "ai_exposed": True,
        "ai_name": "get_incident_diagnosis",
        "ai_description": "读取当前用户有权查看的确定性 Incident 诊断与证据摘要",
    },
)
def get_incident_diagnosis(incident_id: int, current_user: CurrentUserDep, db: DBDep) -> DiagnosisToolOut:
    incident = forecastIncidentService.require_visible_incident(db, current_user, incident_id)
    diagnosis = forecastIncidentCrud.latest_diagnosis(db, incident.id)
    if diagnosis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident diagnosis was not found")
    return DiagnosisToolOut(
        incident_id=incident.id,
        algorithm_version=diagnosis.algorithm_version,
        candidates=diagnosis.candidates,
        confidence=diagnosis.confidence,
        evidence_ids=diagnosis.evidence_ids,
        data_gaps=diagnosis.data_gaps,
    )


@router.patch("/incidents/{incident_id}", response_model=IncidentOut)
def patch_incident(
    incident_id: int,
    payload: IncidentPatch,
    request: Request,
    current_user: CurrentUserDep,
    db: DBDep,
) -> IncidentOut:
    try:
        incident = forecastIncidentService.update_incident(
            db,
            current_user=current_user,
            incident_id=incident_id,
            target_status=payload.status,
            claim=payload.claim,
            silenced_until=_utc_or_422(payload.silenced_until, "silenced_until"),
            silence_reason=payload.silence_reason,
            silence_requested="silenced_until" in payload.model_fields_set,
            audit_context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return _incident_out(db, current_user, incident)


@router.post("/incidents/{incident_id}/comments", response_model=IncidentTimelineOut, status_code=status.HTTP_201_CREATED)
def create_incident_comment(
    incident_id: int,
    payload: IncidentCommentCreate,
    request: Request,
    current_user: CurrentUserDep,
    db: DBDep,
) -> IncidentTimelineOut:
    timeline = forecastIncidentService.add_comment(
        db,
        current_user=current_user,
        incident_id=incident_id,
        content=payload.content,
        audit_context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
    )
    return IncidentTimelineOut.model_validate(timeline)


@router.post("/maintenance-windows", status_code=status.HTTP_201_CREATED)
def create_maintenance_window(
    payload: MaintenanceWindowCreate,
    request: Request,
    current_user: CurrentUserDep,
    db: DBDep,
):
    return forecastIncidentService.create_maintenance_window(
        db,
        current_user=current_user,
        project_id=payload.project_id,
        storage_cluster_id=payload.storage_cluster_id,
        asset_type=payload.asset_type,
        asset_id=payload.asset_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        reason=payload.reason,
        audit_context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
    )
