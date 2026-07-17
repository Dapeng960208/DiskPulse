# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException,status,Response
from sqlalchemy.orm import Session
from typing import List

from schemas import qtreeSchema, commonSchema, storageTrendSchema
from crud import qtreeCrud
from dependencies import get_db, require_super_admin
from services.storageTrendService import build_storage_trend_meta, resolve_trend_indicator
from datetime import datetime
import logging
logger = logging.getLogger('app:qtrees')
router = APIRouter(
    prefix="/qtrees",
    tags=["qtrees"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=qtreeSchema.Qtree)
def create_qtree(
    qtree: qtreeSchema.QtreeCreate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return qtreeCrud.create_qtree(db=db, qtree=qtree)


@router.get("/", response_model=commonSchema.ResponseModel, openapi_extra={"ai_exposed": True, "ai_name": "list_qtrees", "ai_description": "分页查询 Qtree"})
def read_qtrees(page: int, size: int, nameLike: str | None = None, prop: str | None = None,
                order: str | None = None, volume_id: int | None = None, storage_cluster_id: int | None = None,
                db: Session = Depends(get_db)):
    qtrees, total = qtreeCrud.get_qtrees(db=db, page=page, size=size, nameLike=nameLike, prop=prop, order=order,
                                         volume_id=volume_id, storage_cluster_id=storage_cluster_id)
    return commonSchema.ResponseModel[qtreeSchema.Qtree](content=qtrees, total=total)


@router.get("/{qtree_id}", response_model=qtreeSchema.Qtree, openapi_extra={"ai_exposed": True, "ai_name": "get_qtree", "ai_description": "查询指定 Qtree"})
def read_qtree(qtree_id: int, db: Session = Depends(get_db)):
    db_qtree = qtreeCrud.get_qtree_by_id(db, qtree_id=qtree_id)
    if db_qtree is None:
        raise HTTPException(status_code=404, detail="Qtree not found")
    return db_qtree


@router.get("/{qtree_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel, openapi_extra={"ai_exposed": True, "ai_name": "get_qtree_realtime", "ai_description": "查询 Qtree 实时容量趋势"})
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
    return commonSchema.ResponseStorageUsageModel[qtreeSchema.Qtree](data=real_time_data,
                                                                     info=db_qtree,
                                                                     trend_meta=trend_meta)


@router.put("/{qtree_id}", response_model=qtreeSchema.Qtree)
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


@router.delete("/{qtree_id}", status_code=status.HTTP_204_NO_CONTENT)
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
