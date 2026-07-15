# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from schemas import storageAlertsSchema, commonSchema
from crud import storageAlertCrud
from dependencies import get_db
from datetime import datetime, timedelta
from utils.plot import plot_real_time_line
from utils.common import convert_timestamp_to_datetime
import logging
from routers.common import handle_exceptions

logger = logging.getLogger('app:storage-alerts')
router = APIRouter(
    prefix="/storage-alerts",
    tags=["storage-alerts"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=commonSchema.ResponseModel, openapi_extra={"ai_exposed": True, "ai_name": "list_storage_alerts", "ai_description": "分页查询存储告警"})
@handle_exceptions
async def read_storage_alerts(page: int | None = 1, size: int | None = 20, nameLike: str | None = None,
                              prop: str | None = None, alert_type: str | None = None,
                              order: str | None = None, related_type: str | None = None, related_id: int | None = None,
                              db: Session = Depends(get_db)):
    storage_alerts, total = storageAlertCrud.get_storage_alerts(db=db, page=page, size=size, nameLike=nameLike,
                                                                prop=prop, order=order, related_type=related_type,
                                                                related_id=related_id,alert_type=alert_type)
    return commonSchema.ResponseModel[storageAlertsSchema.StorageAlert](content=storage_alerts, total=total)
