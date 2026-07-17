# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from dependencies import CurrentUserDep, get_db
from schemas import dashboardSchema
from services import dashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])
DBDep = Annotated[Session, Depends(get_db)]
OptionalProjectId = Annotated[int | None, Query(gt=0)]
ProjectId = Annotated[int, Query(gt=0)]


@router.get("/summary", response_model=dashboardSchema.DashboardSummaryResponse)
def summary(
    _current_user: CurrentUserDep,
    db: DBDep,
    project_id: OptionalProjectId = None,
):
    return dashboardService.get_summary(db, project_id=project_id)


@router.get("/capacity-trend", response_model=list[dashboardSchema.CapacityTrendPoint])
def capacity_trend(
    _current_user: CurrentUserDep,
    db: DBDep,
    project_id: OptionalProjectId = None,
):
    return dashboardService.get_capacity_trend(db, project_id=project_id)


@router.get("/capacity-items", response_model=list[dashboardSchema.CapacityItem])
def capacity_items(
    _current_user: CurrentUserDep,
    db: DBDep,
    project_id: OptionalProjectId = None,
):
    return dashboardService.get_capacity_items(db, project_id=project_id)


@router.get("/alert-trend", response_model=list[dashboardSchema.AlertTrendPoint])
def alert_trend(
    _current_user: CurrentUserDep,
    db: DBDep,
    project_id: OptionalProjectId = None,
):
    return dashboardService.get_alert_trend(db, project_id=project_id)


@router.get("/top-users", response_model=list[dashboardSchema.TopUser])
def top_users(
    _current_user: CurrentUserDep,
    db: DBDep,
    project_id: ProjectId,
):
    return dashboardService.get_top_users(db, project_id=project_id)
