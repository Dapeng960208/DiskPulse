# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from schemas import volumeSchema, commonSchema, storageTrendSchema
from crud import volumeCrud
from dependencies import get_db, require_super_admin
from services.storageTrendService import build_storage_trend_meta, resolve_trend_indicator

router = APIRouter(
    prefix="/volumes",
    tags=["volumes"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=volumeSchema.Volume)
def create_volume(
    volume: volumeSchema.VolumeCreate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return volumeCrud.create_volume(db=db, volume=volume)


@router.get("/", response_model=commonSchema.ResponseModel, openapi_extra={"ai_exposed": True, "ai_name": "list_volumes", "ai_description": "分页查询存储空间"})
def read_volumes(page: int | None = 1, size: int | None = 20, nameLike: str | None = None, prop: str | None = None,
                 order: str | None = None, storage_cluster_id: int | None = None, db: Session = Depends(get_db)):
    volumes, total = volumeCrud.get_volumes(db=db, page=page, size=size, nameLike=nameLike, prop=prop, order=order,
                                           storage_cluster_id=storage_cluster_id)
    return commonSchema.ResponseModel[volumeSchema.Volume](content=volumes, total=total)


@router.get("/{volume_id}", response_model=volumeSchema.Volume, openapi_extra={"ai_exposed": True, "ai_name": "get_volume", "ai_description": "查询指定存储空间"})
def read_volume(volume_id: int, db: Session = Depends(get_db)):
    db_volume = volumeCrud.get_volume_by_id(db, volume_id=volume_id)
    if db_volume is None:
        raise HTTPException(status_code=404, detail="Volume not found")
    return db_volume


@router.get("/{volume_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel, openapi_extra={"ai_exposed": True, "ai_name": "get_volume_realtime", "ai_description": "查询存储空间实时容量趋势"})
def read_volume_realtime_data(volume_id: int, start_time: datetime | None = None,
                              end_time: datetime | None = None,
                              indicator: storageTrendSchema.TrendIndicator = 'used', db: Session = Depends(get_db)):
    db_volume = volumeCrud.get_volume_by_id(db, volume_id=volume_id)
    if db_volume is None:
        raise HTTPException(status_code=404, detail="Volume not found")
    trend_meta = build_storage_trend_meta(db, target_type="volume", target=db_volume)
    real_time_data = volumeCrud.get_volume_real_time_data_by_id(db=db, start_time=start_time,
                                                                end_time=end_time,
                                                                volume_id=volume_id,
                                                                indicator=resolve_trend_indicator(indicator, trend_meta))
    return commonSchema.ResponseStorageUsageModel[volumeSchema.Volume](data=real_time_data,
                                                                       info=db_volume,
                                                                       trend_meta=trend_meta)


@router.put("/{volume_id}", response_model=volumeSchema.Volume)
def update_volume(
    volume_id: int,
    volume: volumeSchema.VolumeUpdate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_volume = volumeCrud.get_volume_by_id(db, volume_id=volume_id)
    if db_volume is None:
        raise HTTPException(status_code=404, detail="Volume not found")
    return volumeCrud.update_volume(db=db, volume_id=volume_id, volume=volume)


@router.delete("/{volume_id}", response_model=volumeSchema.Volume)
def delete_volume(
    volume_id: int,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_volume = volumeCrud.get_volume_by_id(db, volume_id=volume_id)
    if db_volume is None:
        raise HTTPException(status_code=404, detail="Volume not found")
    return volumeCrud.delete_volume(db=db, volume_id=volume_id)
