# -*- coding: utf-8 -*-
from fastapi import Depends, HTTPException, Query
from routers.transactional import TransactionalAPIRouter
from sqlalchemy.orm import Session
from typing import Annotated, List
from datetime import datetime
from schemas import volumeSchema, commonSchema, storageTrendSchema
from crud import volumeCrud
from dependencies import UseRatioMaximum, UseRatioMinimum, get_db, require_super_admin, validate_use_ratio_range
from services.storageTrendService import build_storage_trend_meta, format_trend_data, resolve_trend_indicator, trend_data_unit

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
    prefix="/volumes",
    tags=["volumes"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(require_super_admin)],
)


@router.post(
    "/",
    response_model=volumeSchema.Volume,
)
def create_volume(
    volume: volumeSchema.VolumeCreate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return volumeCrud.create_volume(db=db, volume=volume)


@router.get(
    "/",
    response_model=commonSchema.ResponseModel,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "list_volumes",
        "ai_description": "分页查询存储空间",
        "ai_blacklist_fields": AI_STORAGE_CLUSTER_BLACKLIST_FIELDS,
    },
)
def read_volumes(page: int | None = 1, size: int | None = 20, nameLike: str | None = None, prop: str | None = None,
                 order: str | None = None, storage_cluster_id: int | None = None,
                 use_ratio_min: UseRatioMinimum = None, use_ratio_max: UseRatioMaximum = None,
                 db: Session = Depends(get_db)):
    use_ratio_min, use_ratio_max = validate_use_ratio_range(use_ratio_min, use_ratio_max)
    volumes, total = volumeCrud.get_volumes(db=db, page=page, size=size, nameLike=nameLike, prop=prop, order=order,
                                           storage_cluster_id=storage_cluster_id,
                                           use_ratio_min=use_ratio_min, use_ratio_max=use_ratio_max)
    return commonSchema.ResponseModel[volumeSchema.Volume](content=volumes, total=total)


@router.get(
    "/{volume_id}",
    response_model=volumeSchema.Volume,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "get_volume",
        "ai_description": "查询指定存储空间",
        "ai_blacklist_fields": AI_STORAGE_CLUSTER_BLACKLIST_FIELDS,
    },
)
def read_volume(volume_id: int, db: Session = Depends(get_db)):
    db_volume = volumeCrud.get_volume_by_id(db, volume_id=volume_id)
    if db_volume is None:
        raise HTTPException(status_code=404, detail="Volume not found")
    return db_volume


@router.get("/{volume_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel, openapi_extra={"ai_exposed": True, "ai_system_management": True, "ai_name": "get_volume_realtime", "ai_description": "查询存储空间实时容量趋势", "ai_blacklist_fields": AI_STORAGE_CLUSTER_BLACKLIST_FIELDS})
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
    data_unit = trend_data_unit("volume", indicator)
    return commonSchema.ResponseStorageUsageModel[volumeSchema.Volume](data=format_trend_data(real_time_data, data_unit),
                                                                       info=db_volume,
                                                                       trend_meta=trend_meta,
                                                                       data_unit=data_unit)


@router.get("/{volume_id}/monitoring", response_model=volumeSchema.VolumeMonitoring)
def read_volume_monitoring(
    volume_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    metrics: Annotated[list[str] | None, Query(alias="metrics[]")] = None,
    db: Session = Depends(get_db),
) -> volumeSchema.VolumeMonitoring:
    try:
        result = volumeCrud.get_volume_monitoring(db, volume_id, start_time, end_time, metrics)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Volume not found")
    return result


@router.get(
    "/{volume_id}/monitoring/ai",
    response_model=volumeSchema.VolumeMonitoringToolOut,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "get_volume_performance_monitoring",
        "ai_description": "查询存储空间性能监控指标和关联项目，不包含目录路径",
    },
)
def read_volume_monitoring_for_ai(
    volume_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    metrics: Annotated[list[str] | None, Query(alias="metrics[]")] = None,
    db: Session = Depends(get_db),
) -> volumeSchema.VolumeMonitoringToolOut:
    try:
        result = volumeCrud.get_volume_monitoring(db, volume_id, start_time, end_time, metrics)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Volume not found")
    info = result["info"]
    binding = result.get("binding")
    return volumeSchema.VolumeMonitoringToolOut(
        info={
            "id": info.id,
            "name": info.name,
            "storage_cluster_id": info.storage_cluster_id,
        },
        binding=None if binding is None else {
            "group_id": binding["group_id"],
            "group_name": binding["group_name"],
            "project_id": binding["project_id"],
            "project_name": binding["project_name"],
        },
        capacity=result["capacity"],
        capacity_unit=result["capacity_unit"],
        performance=result["performance"],
    )


@router.put(
    "/{volume_id}",
    response_model=volumeSchema.Volume,
)
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


@router.delete(
    "/{volume_id}",
    response_model=volumeSchema.Volume,
)
def delete_volume(
    volume_id: int,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_volume = volumeCrud.get_volume_by_id(db, volume_id=volume_id)
    if db_volume is None:
        raise HTTPException(status_code=404, detail="Volume not found")
    return volumeCrud.delete_volume(db=db, volume_id=volume_id)
