# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from dependencies import get_db, require_super_admin
from schemas.telemetryObservabilitySchema import TelemetryCollectionRunPage, TelemetryCollectionRunRead
from services import telemetryObservabilityService


router = APIRouter(prefix="/v1", tags=["telemetry"])
DBDep = Annotated[Session, Depends(get_db)]
AdminDep = Annotated[None, Depends(require_super_admin)]


def _utc_or_422(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise HTTPException(status_code=422, detail=f"{name} must include a UTC offset")
    return value.astimezone(timezone.utc)


@router.get("/telemetry-runs", response_model=TelemetryCollectionRunPage)
def list_telemetry_runs(
    _admin: AdminDep,
    db: DBDep,
    cluster_id: Annotated[int | None, Query(ge=1)] = None,
    component: Annotated[Literal["capacity", "vendor_events", "performance"] | None, Query()] = None,
    started_at_from: Annotated[datetime | None, Query()] = None,
    started_at_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TelemetryCollectionRunPage:
    started_at_from = _utc_or_422(started_at_from, "started_at_from")
    started_at_to = _utc_or_422(started_at_to, "started_at_to")
    if started_at_from and started_at_to and started_at_from > started_at_to:
        raise HTTPException(status_code=422, detail="started_at_from must not exceed started_at_to")
    runs, total = telemetryObservabilityService.list_collection_runs(
        db,
        cluster_id=cluster_id,
        component=component,
        started_at_from=started_at_from,
        started_at_to=started_at_to,
        page=page,
        size=size,
    )
    return TelemetryCollectionRunPage(
        content=[
            TelemetryCollectionRunRead(
                run_id=run.id,
                trace_id=run.trace_id,
                scope_type=run.scope_type,
                scope_key=run.scope_key,
                storage_cluster_id=run.storage_cluster_id,
                component=run.component,
                outcome=run.outcome,
                data_state=run.data_state,
                records_written=run.records_written,
                error_code=run.error_code,
                started_at=run.started_at,
                finished_at=run.finished_at,
            )
            for run in runs
        ],
        total=total,
    )
