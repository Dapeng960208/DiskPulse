# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from dependencies import CurrentUserDep, UseRatioMaximum, UseRatioMinimum, get_db, validate_use_ratio_range
from schemas import dashboardSchema
from services import dashboardService
from services import project_access_service
from utils.auth_service import is_super_admin


router = APIRouter(prefix="/dashboard", tags=["dashboard"])
DBDep = Annotated[Session, Depends(get_db)]
OptionalProjectId = Annotated[int | None, Query(gt=0)]
ProjectId = Annotated[int, Query(gt=0)]


def _require_dashboard_scope(db: Session, current_user, project_id: int | None) -> None:
    if project_id is None:
        if not is_super_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="project scope is required",
            )
        return
    project_access_service.require_project_permission(db, current_user, project_id, "reader")


@router.get("/summary", response_model=dashboardSchema.DashboardSummaryResponse)
def summary(
    current_user: CurrentUserDep,
    db: DBDep,
    project_id: OptionalProjectId = None,
):
    _require_dashboard_scope(db, current_user, project_id)
    return dashboardService.get_summary(db, project_id=project_id)


@router.get("/capacity-trend", response_model=list[dashboardSchema.CapacityTrendPoint])
def capacity_trend(
    current_user: CurrentUserDep,
    db: DBDep,
    project_id: OptionalProjectId = None,
):
    _require_dashboard_scope(db, current_user, project_id)
    return dashboardService.get_capacity_trend(db, project_id=project_id)


@router.get("/capacity-items", response_model=list[dashboardSchema.CapacityItem])
def capacity_items(
    current_user: CurrentUserDep,
    db: DBDep,
    project_id: OptionalProjectId = None,
    use_ratio_min: UseRatioMinimum = None,
    use_ratio_max: UseRatioMaximum = None,
):
    _require_dashboard_scope(db, current_user, project_id)
    use_ratio_min, use_ratio_max = validate_use_ratio_range(use_ratio_min, use_ratio_max)
    return dashboardService.get_capacity_items(
        db,
        project_id=project_id,
        use_ratio_min=use_ratio_min,
        use_ratio_max=use_ratio_max,
    )


@router.get("/alert-levels", response_model=list[dashboardSchema.AlertLevelItem])
def alert_levels(
    current_user: CurrentUserDep,
    db: DBDep,
    project_id: OptionalProjectId = None,
):
    _require_dashboard_scope(db, current_user, project_id)
    return dashboardService.get_alert_levels(db, project_id=project_id)


@router.get("/top-users", response_model=list[dashboardSchema.TopUser])
def top_users(
    current_user: CurrentUserDep,
    db: DBDep,
    project_id: ProjectId,
):
    _require_dashboard_scope(db, current_user, project_id)
    return dashboardService.get_top_users(db, project_id=project_id)
