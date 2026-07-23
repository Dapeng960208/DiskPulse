# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session

from crud import forecastIncidentCrud
from dependencies import CurrentUserDep, get_db, require_super_admin
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
    IncidentEvidencePresentationOut,
    IncidentOut,
    IncidentPage,
    IncidentPatch,
    IncidentTimelineOut,
    IncidentTimelinePresentationOut,
    MaintenanceWindowCreate,
)
from services import audit_service, forecastIncidentService
from services import capacityPredictionGovernanceService
from schemas.capacityPredictionSchema import (
    CapacityPredictionAccessOut,
    CapacityExhaustionRiskOut,
    CapacityPredictionCandidateCreate,
    CapacityPredictionCandidateOut,
    CapacityPredictionPlanCreate,
    CapacityPredictionPlanOut,
    CapacityPredictionRelatedIncidentOut,
    CapacityPredictionSettingsPatch,
    CapacityPredictionVisibilityOut,
)


router = APIRouter(prefix="/v1", tags=["forecast-incidents"])
DBDep = Annotated[Session, Depends(get_db)]


@router.get("/capacity-predictions/visibility", response_model=CapacityPredictionVisibilityOut)
def capacity_prediction_visibility(current_user: CurrentUserDep, db: DBDep) -> CapacityPredictionVisibilityOut:
    return CapacityPredictionVisibilityOut(
        visible=capacityPredictionGovernanceService.prediction_visible_to_user(db, current_user=current_user)
    )


@router.get("/capacity-predictions", response_model=ForecastPage)
def list_capacity_predictions(
    current_user: CurrentUserDep,
    db: DBDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ForecastPage:
    rows, total = capacityPredictionGovernanceService.list_final_predictions(
        db,
        current_user=current_user,
        page=page,
        size=size,
    )
    return ForecastPage(content=[ForecastOut.model_validate(row) for row in rows], total=total)


@router.get("/capacity-predictions/{asset_type}/{asset_id}", response_model=ForecastOut)
def resource_capacity_prediction(
    asset_type: Annotated[str, Path(pattern="^(group|storage_usage)$")],
    asset_id: Annotated[int, Path(ge=1)],
    current_user: CurrentUserDep,
    db: DBDep,
) -> ForecastOut:
    forecast = capacityPredictionGovernanceService.get_resource_prediction(
        db, current_user=current_user, asset_type=asset_type, asset_id=asset_id
    )
    return ForecastOut.model_validate(forecast)


@router.get(
    "/capacity-predictions/{asset_type}/{asset_id}/risk",
    response_model=CapacityExhaustionRiskOut,
)
def resource_capacity_exhaustion_risk(
    asset_type: Annotated[str, Path(pattern="^(storage_cluster|project|group|storage_usage)$")],
    asset_id: Annotated[int, Path(ge=1)],
    current_user: CurrentUserDep,
    db: DBDep,
) -> CapacityExhaustionRiskOut:
    return CapacityExhaustionRiskOut(**capacityPredictionGovernanceService.get_capacity_exhaustion_risk(
        db,
        current_user=current_user,
        asset_type=asset_type,
        asset_id=asset_id,
    ))


@router.get("/capacity-predictions/{asset_type}/{asset_id}/access", response_model=CapacityPredictionAccessOut)
def resource_capacity_prediction_access(
    asset_type: Annotated[str, Path(pattern="^(group|storage_usage)$")],
    asset_id: Annotated[int, Path(ge=1)],
    current_user: CurrentUserDep,
    db: DBDep,
) -> CapacityPredictionAccessOut:
    return CapacityPredictionAccessOut(**capacityPredictionGovernanceService.resource_prediction_access(
        db, current_user=current_user, asset_type=asset_type, asset_id=asset_id
    ))


@router.get("/capacity-predictions/{asset_type}/{asset_id}/plans", response_model=list[CapacityPredictionPlanOut])
def resource_capacity_prediction_plans(
    asset_type: Annotated[str, Path(pattern="^(group|storage_usage)$")],
    asset_id: Annotated[int, Path(ge=1)],
    current_user: CurrentUserDep,
    db: DBDep,
) -> list[CapacityPredictionPlanOut]:
    plans = capacityPredictionGovernanceService.list_resource_capacity_plans(
        db, current_user=current_user, asset_type=asset_type, asset_id=asset_id
    )
    return [CapacityPredictionPlanOut.model_validate(item) for item in plans]


@router.get(
    "/capacity-predictions/{asset_type}/{asset_id}/related-incidents",
    response_model=list[CapacityPredictionRelatedIncidentOut],
)
def resource_capacity_prediction_related_incidents(
    asset_type: Annotated[str, Path(pattern="^(group|storage_usage)$")],
    asset_id: Annotated[int, Path(ge=1)],
    current_user: CurrentUserDep,
    db: DBDep,
) -> list[CapacityPredictionRelatedIncidentOut]:
    return [
        CapacityPredictionRelatedIncidentOut(**item)
        for item in capacityPredictionGovernanceService.list_resource_related_incidents(
            db,
            current_user=current_user,
            asset_type=asset_type,
            asset_id=asset_id,
        )
    ]


@router.post("/capacity-predictions/{asset_type}/{asset_id}/plans", response_model=CapacityPredictionPlanOut, status_code=status.HTTP_201_CREATED)
def create_resource_capacity_prediction_plan(
    asset_type: Annotated[str, Path(pattern="^(group|storage_usage)$")],
    asset_id: Annotated[int, Path(ge=1)],
    payload: CapacityPredictionPlanCreate,
    request: Request,
    current_user: CurrentUserDep,
    db: DBDep,
) -> CapacityPredictionPlanOut:
    plan = capacityPredictionGovernanceService.create_capacity_plan(
        db, current_user=current_user, asset_type=asset_type, asset_id=asset_id,
        effective_at=payload.effective_at, capacity_delta=payload.capacity_delta, reason=payload.reason,
    )
    audit_service.append_audit_event(
        db, context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
        phase="result", action="capacity_prediction_plan.create", resource_type="capacity_prediction_plan",
        resource_id=plan.id, project_id=plan.project_id, outcome="success",
        after_summary={"asset_type": asset_type, "asset_id": asset_id, "capacity_delta": payload.capacity_delta},
    )
    db.commit()
    db.refresh(plan)
    return CapacityPredictionPlanOut.model_validate(plan)


@router.get("/admin/capacity-prediction-settings", response_model=CapacityPredictionVisibilityOut, dependencies=[Depends(require_super_admin)])
def capacity_prediction_settings(_current_user: CurrentUserDep, db: DBDep) -> CapacityPredictionVisibilityOut:
    return CapacityPredictionVisibilityOut(visible=capacityPredictionGovernanceService.get_prediction_settings(db))


@router.patch("/admin/capacity-prediction-settings", response_model=CapacityPredictionVisibilityOut, dependencies=[Depends(require_super_admin)])
def update_capacity_prediction_settings(
    payload: CapacityPredictionSettingsPatch, request: Request, current_user: CurrentUserDep, db: DBDep
) -> CapacityPredictionVisibilityOut:
    settings = capacityPredictionGovernanceService.update_prediction_settings(
        db,
        user_id=current_user.id,
        user_visible=payload.user_visible,
    )
    audit_service.append_audit_event(
        db, context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
        phase="result", action="capacity_prediction_visibility.update", resource_type="capacity_prediction_settings",
        resource_id=1, outcome="success", after_summary={"user_visible": payload.user_visible},
    )
    db.commit()
    return CapacityPredictionVisibilityOut(visible=settings.user_visible)


@router.get(
    "/admin/capacity-prediction-candidates",
    response_model=list[CapacityPredictionCandidateOut],
    dependencies=[Depends(require_super_admin)],
)
def list_capacity_prediction_candidates(_current_user: CurrentUserDep, db: DBDep) -> list[CapacityPredictionCandidateOut]:
    return [
        CapacityPredictionCandidateOut(**item)
        for item in capacityPredictionGovernanceService.list_candidate_governance(db)
    ]


@router.post(
    "/admin/capacity-prediction-candidates",
    response_model=CapacityPredictionCandidateOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_super_admin)],
)
def create_capacity_prediction_candidate(
    payload: CapacityPredictionCandidateCreate,
    request: Request,
    current_user: CurrentUserDep,
    db: DBDep,
) -> CapacityPredictionCandidateOut:
    candidate = capacityPredictionGovernanceService.create_capacity_prediction_candidate(
        db,
        version=payload.version,
        ai_model_id=payload.ai_model_id,
    )
    audit_service.append_audit_event(
        db,
        context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
        phase="result",
        action="capacity_prediction_candidate.create",
        resource_type="capacity_prediction_candidate",
        resource_id=candidate.id,
        outcome="success",
        after_summary={"version": candidate.version, "ai_model_id": candidate.ai_model_id},
    )
    db.commit()
    db.refresh(candidate)
    return CapacityPredictionCandidateOut.model_validate(candidate)


@router.post(
    "/admin/capacity-prediction-candidates/{candidate_id}/activate",
    response_model=CapacityPredictionCandidateOut,
    dependencies=[Depends(require_super_admin)],
)
def activate_capacity_prediction_candidate(
    candidate_id: Annotated[int, Path(ge=1)],
    request: Request,
    current_user: CurrentUserDep,
    db: DBDep,
) -> CapacityPredictionCandidateOut:
    candidate = capacityPredictionGovernanceService.activate_capacity_prediction_candidate(
        db,
        candidate_id=candidate_id,
    )
    audit_service.append_audit_event(
        db,
        context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
        phase="result",
        action="capacity_prediction_candidate.activate",
        resource_type="capacity_prediction_candidate",
        resource_id=candidate.id,
        outcome="success",
        after_summary={"version": candidate.version, "ai_model_id": candidate.ai_model_id},
    )
    db.commit()
    db.refresh(candidate)
    return CapacityPredictionCandidateOut.model_validate(candidate)


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
    vendor_context = forecastIncidentService.build_vendor_evidence_context(
        db,
        evidence,
        storage_cluster_id=incident.storage_cluster_id,
    )
    anomaly_context = forecastIncidentService.build_anomaly_evidence_context(
        db,
        evidence,
    )
    return IncidentDetailOut(
        **_incident_out(db, current_user, incident).model_dump(),
        evidence=[
            _incident_evidence_out(
                db,
                item,
                vendor_context=vendor_context,
                anomaly_context=anomaly_context,
            )
            for item in evidence
        ],
        timeline=[_incident_timeline_out(db, item) for item in timeline],
        diagnosis=(
            DiagnosisOut(
                **DiagnosisOut.model_validate(diagnosis).model_dump(
                    exclude={"data_gap_details", "evidence_summaries"}
                ),
                data_gap_details=forecastIncidentService.diagnosis_data_gap_details(
                    diagnosis
                ),
                evidence_summaries=forecastIncidentService.diagnosis_evidence_summaries(
                    db,
                    incident.id,
                    diagnosis.evidence_ids,
                    evidence_items=evidence,
                    vendor_context=vendor_context,
                ),
            )
            if diagnosis is not None
            else None
        ),
    )


def _incident_evidence_out(
    db: Session,
    evidence,
    *,
    vendor_context: forecastIncidentService.VendorEvidenceContextMap | None = None,
    anomaly_context: forecastIncidentService.AnomalyEvidenceContextMap | None = None,
) -> IncidentEvidenceOut:
    return IncidentEvidenceOut(
        id=evidence.id,
        source=evidence.source,
        source_ref=evidence.source_ref,
        evidence_type=evidence.evidence_type,
        observed_at=evidence.observed_at,
        data_gaps=list(evidence.data_gaps or []),
        data_gap_details=forecastIncidentService.data_gap_details(evidence.data_gaps),
        evidence_summary=forecastIncidentService.vendor_evidence_summary(
            db,
            evidence,
            vendor_context=vendor_context,
        ),
        presentation=IncidentEvidencePresentationOut(
            **forecastIncidentService.build_evidence_presentation(
                evidence,
                db=db,
                vendor_context=vendor_context,
                anomaly_context=anomaly_context,
            )
        ),
    )


def _incident_timeline_out(db: Session, timeline) -> IncidentTimelineOut:
    return IncidentTimelineOut(
        id=timeline.id,
        event_type=timeline.event_type,
        actor_user_id=timeline.actor_user_id,
        from_status=timeline.from_status,
        to_status=timeline.to_status,
        comment=timeline.comment,
        occurred_at=timeline.occurred_at,
        presentation=IncidentTimelinePresentationOut(
            **forecastIncidentService.build_timeline_presentation(
                timeline,
                actor_label=forecastIncidentService.timeline_actor_label(db, timeline),
            )
        ),
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


@router.get(
    "/anomalies",
    response_model=AnomalyPage,
    openapi_extra={
        "ai_exposed": True,
        "ai_name": "list_performance_anomalies",
        "ai_description": "分页查询当前用户可见的存储集群性能异常",
    },
)
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


@router.get(
    "/incidents",
    response_model=IncidentPage,
    openapi_extra={
        "ai_exposed": True,
        "ai_name": "list_incidents",
        "ai_description": "分页查询当前用户可见的故障分析事件",
    },
)
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
        data_gap_details=forecastIncidentService.diagnosis_data_gap_details(diagnosis),
        evidence_summaries=forecastIncidentService.diagnosis_evidence_summaries(
            db, incident.id, diagnosis.evidence_ids
        ),
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
            target_severity=payload.severity,
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
