# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException,status,Response
from sqlalchemy.orm import Session
from typing import List

from schemas import qtreeSchema, commonSchema
from crud import qtreeCrud
from dependencies import get_db, require_super_admin
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


@router.get("/", response_model=commonSchema.ResponseModel)
def read_qtrees(page: int, size: int, nameLike: str | None = None, prop: str | None = None,
                order: str | None = None, volume_id: int | None = None, storage_cluster_id: int | None = None,
                db: Session = Depends(get_db)):
    qtrees, total = qtreeCrud.get_qtrees(db=db, page=page, size=size, nameLike=nameLike, prop=prop, order=order,
                                         volume_id=volume_id, storage_cluster_id=storage_cluster_id)
    return commonSchema.ResponseModel[qtreeSchema.Qtree](content=qtrees, total=total)


@router.get("/{qtree_id}", response_model=qtreeSchema.Qtree)
def read_qtree(qtree_id: int, db: Session = Depends(get_db)):
    db_qtree = qtreeCrud.get_qtree_by_id(db, qtree_id=qtree_id)
    if db_qtree is None:
        raise HTTPException(status_code=404, detail="Qtree not found")
    return db_qtree


@router.get("/{qtree_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel)
def read_qtree_realtime_data(qtree_id: int, start_time: datetime | None = None,
                             end_time: datetime | None = None,
                             indicator: str = 'used', db: Session = Depends(get_db)):
    db_qtree = qtreeCrud.get_qtree_by_id(db, qtree_id=qtree_id)
    if db_qtree is None:
        raise HTTPException(status_code=404, detail="Qtree not found")
    real_time_data = qtreeCrud.get_qtree_real_time_data_by_id(db=db, qtree_id=qtree_id,
                                                              start_time=start_time, end_time=end_time,
                                                              indicator=indicator)
    return commonSchema.ResponseStorageUsageModel[qtreeSchema.Qtree](data=real_time_data,
                                                                     info=db_qtree)


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
