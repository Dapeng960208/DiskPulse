# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from dependencies import CurrentUserDep, get_db
from schemas import dashboardSchema
from services import dashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])
DBDep = Annotated[Session, Depends(get_db)]


@router.get("/overview", response_model=dashboardSchema.DashboardOverview)
def overview(
    _current_user: CurrentUserDep,
    db: DBDep,
    project_id: Annotated[int | None, Query(gt=0)] = None,
):
    return dashboardService.get_dashboard_overview(db, project_id=project_id)
