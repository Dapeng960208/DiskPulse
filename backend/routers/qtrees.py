# -*- coding: utf-8 -*-
from fastapi import Depends, HTTPException,status,Response
from routers.transactional import TransactionalAPIRouter
from sqlalchemy.orm import Session
from typing import List

from schemas import qtreeSchema, commonSchema, storageTrendSchema
from crud import qtreeCrud
from dependencies import UseRatioMaximum, UseRatioMinimum, get_db, require_super_admin, validate_use_ratio_range
from services.storageTrendService import build_storage_trend_meta, format_trend_data, resolve_trend_indicator, trend_data_unit
from datetime import datetime
import logging
logger = logging.getLogger('app:qtrees')
AI_STORAGE_CLUSTER_BLACKLIST_FIELDS = (
    "isilon_session_cache_mode",
    "isilon_session_cache_path",
    "protocol",
    "storage_host",
    "storage_port",
    "storage_user",
    "tls_verify",
)
router = TransactionalAPIRouter(
    prefix="/qtrees",
    tags=["qtrees"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(require_super_admin)],
)


@router.post(
    "/",
    response_model=qtreeSchema.Qtree,
)
def create_qtree(
    qtree: qtreeSchema.QtreeCreate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return qtreeCrud.create_qtree(db=db, qtree=qtree)


@router.get(
    "/",
    response_model=commonSchema.ResponseModel,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "list_qtrees",
        "ai_description": "分页查询 Qtree（NetApp）",
        "ai_blacklist_fields": AI_STORAGE_CLUSTER_BLACKLIST_FIELDS,
    },
)
def read_qtrees(page: int, size: int, nameLike: str | None = None, prop: str | None = None,
                order: str | None = None, volume_id: int | None = None, storage_cluster_id: int | None = None,
                use_ratio_min: UseRatioMinimum = None, use_ratio_max: UseRatioMaximum = None,
                db: Session = Depends(get_db)):
    use_ratio_min, use_ratio_max = validate_use_ratio_range(use_ratio_min, use_ratio_max)
    qtrees, total = qtreeCrud.get_qtrees(db=db, page=page, size=size, nameLike=nameLike, prop=prop, order=order,
                                         volume_id=volume_id, storage_cluster_id=storage_cluster_id,
                                         use_ratio_min=use_ratio_min, use_ratio_max=use_ratio_max)
    return commonSchema.ResponseModel[qtreeSchema.Qtree](content=qtrees, total=total)


@router.get(
    "/{qtree_id}",
    response_model=qtreeSchema.Qtree,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "get_qtree",
        "ai_description": "查询指定 Qtree（NetApp）",
        "ai_blacklist_fields": AI_STORAGE_CLUSTER_BLACKLIST_FIELDS,
    },
)
def read_qtree(qtree_id: int, db: Session = Depends(get_db)):
    db_qtree = qtreeCrud.get_qtree_by_id(db, qtree_id=qtree_id)
    if db_qtree is None:
        raise HTTPException(status_code=404, detail="Qtree not found")
    return db_qtree


@router.get(
    "/{qtree_id}/realtime",
    response_model=commonSchema.ResponseStorageUsageModel,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "get_qtree_realtime",
        "ai_description": "查询 Qtree（NetApp）实时容量趋势",
        "ai_blacklist_fields": AI_STORAGE_CLUSTER_BLACKLIST_FIELDS,
    },
)
def read_qtree_realtime_data(qtree_id: int, start_time: datetime | None = None,
                             end_time: datetime | None = None,
                             indicator: storageTrendSchema.TrendIndicator = 'used', db: Session = Depends(get_db)):
    db_qtree = qtreeCrud.get_qtree_by_id(db, qtree_id=qtree_id)
    if db_qtree is None:
        raise HTTPException(status_code=404, detail="Qtree not found")
    trend_meta = build_storage_trend_meta(db, target_type="qtree", target=db_qtree)
    real_time_data = qtreeCrud.get_qtree_real_time_data_by_id(db=db, qtree_id=qtree_id,
                                                              start_time=start_time, end_time=end_time,
                                                              indicator=resolve_trend_indicator(indicator, trend_meta))
    data_unit = trend_data_unit("qtree", indicator)
    return commonSchema.ResponseStorageUsageModel[qtreeSchema.Qtree](data=format_trend_data(real_time_data, data_unit),
                                                                     info=db_qtree,
                                                                     trend_meta=trend_meta,
                                                                     data_unit=data_unit)


@router.put(
    "/{qtree_id}",
    response_model=qtreeSchema.Qtree,
)
def update_qtree(
    qtree_id: int,
    qtree: qtreeSchema.QtreeUpdate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_qtree = qtreeCrud.get_qtree_by_id(db, qtree_id=qtree_id)
    if db_qtree is None:
        raise HTTPException(status_code=404, detail="Qtree not found")
    return qtreeCrud.update_qtree(db=db, qtree_id=qtree_id, qtree=qtree)


@router.delete(
    "/{qtree_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_qtree(
    qtree_id: int,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_qtree = qtreeCrud.get_qtree_by_id(db, qtree_id=qtree_id)
    if db_qtree is None:
        raise HTTPException(status_code=404, detail="Qtree not found")
    qtreeCrud.delete_qtree(db=db, qtree_id=qtree_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
