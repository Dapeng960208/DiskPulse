# -*- coding: utf-8 -*-
import io
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from schemas import (
    commonSchema,
    storageClusterSchema,
    storageHealthAnalyticsSchema,
    storageTrendSchema,
)
from crud import storageClusterCrud
from crud.questDbCrud import get_storage_cluster_real_time
from dependencies import CurrentUserDep, UseRatioMaximum, UseRatioMinimum, get_db, require_super_admin, validate_use_ratio_range
from services import audit_service
from services.storageClusterService import schedule_storage_collection as _schedule_storage_collection
from services.storageTrendService import build_storage_trend_meta, format_trend_data, resolve_trend_indicator, trend_data_unit
from services.storageHealthAnalyticsService import (
    export_storage_health,
    get_capacity_change,
    get_error_severity,
    get_repeated_faults,
    get_system_event_detail,
    get_system_events,
    get_top_latency,
    validate_time_range,
)

router = APIRouter(
    prefix="/storage-clusters",
    tags=["storage-clusters"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(require_super_admin)],
)


def _analytics_time_range(
    start_time: Annotated[datetime, Query()],
    end_time: Annotated[datetime, Query()],
) -> tuple[datetime, datetime]:
    try:
        validate_time_range(start_time, end_time)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return start_time, end_time


AnalyticsTimeRange = Annotated[tuple[datetime, datetime], Depends(_analytics_time_range)]


def _require_storage_cluster(db: Session, storage_cluster_id: int) -> None:
    if storageClusterCrud.get_storage_cluster(db, storage_cluster_id) is None:
        raise HTTPException(status_code=404, detail="StorageCluster not found")


@router.get(
    "/",
    response_model=commonSchema.ResponseModel,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "list_storage_clusters",
        "ai_description": "分页查询存储集群",
    },
)
def read_storage_clusters(
        page: int | None = 1,
        size: int | None = 20,
        nameLike: str | None = None,
        prop: str | None = None,
        order: str | None = None,
        is_active: Optional[bool] = None,
        use_ratio_min: UseRatioMinimum = None,
        use_ratio_max: UseRatioMaximum = None,
    db: Session = Depends(get_db)
):
    use_ratio_min, use_ratio_max = validate_use_ratio_range(use_ratio_min, use_ratio_max)
    total,storage_clusters = storageClusterCrud.get_storage_clusters(
        db, page, size, nameLike, prop, order, is_active, use_ratio_min, use_ratio_max,
    )
    return commonSchema.ResponseModel[storageClusterSchema.StorageCluster](content=storage_clusters, total=total)


@router.post(
    "/",
    response_model=storageClusterSchema.StorageCluster,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "create_storage_cluster",
        "ai_description": "创建存储集群",
    },
)
def create_storage_cluster(
    storage_cluster: storageClusterSchema.StorageClusterCreate,
    request: Request,
    current_user: CurrentUserDep,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    db_cluster = storageClusterCrud.create_storage_cluster(db=db, storage_cluster=storage_cluster)
    if db_cluster.is_active:
        _schedule_storage_collection(
            db_cluster.id,
            audit_context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
        )
    return db_cluster


@router.get(
    "/{storage_cluster_id}",
    response_model=storageClusterSchema.StorageCluster,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "get_storage_cluster",
        "ai_description": "查询指定存储集群",
    },
)
def read_storage_cluster(storage_cluster_id: int, db: Session = Depends(get_db)):
    db_cluster = storageClusterCrud.get_storage_cluster(db, storage_cluster_id=storage_cluster_id)
    if db_cluster is None:
        raise HTTPException(status_code=404, detail="StorageCluster not found")
    return db_cluster


@router.put(
    "/{storage_cluster_id}",
    response_model=storageClusterSchema.StorageCluster,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "update_storage_cluster",
        "ai_description": "更新存储集群",
    },
)
def update_storage_cluster(
    storage_cluster_id: int,
    storage_cluster: storageClusterSchema.StorageClusterUpdate,
    request: Request,
    current_user: CurrentUserDep,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    db_cluster = storageClusterCrud.get_storage_cluster(db, storage_cluster_id=storage_cluster_id)
    if db_cluster is None:
        raise HTTPException(status_code=404, detail="StorageCluster not found")
    db_cluster = storageClusterCrud.update_storage_cluster(db=db, storage_cluster_id=storage_cluster_id,
                                                           storage_cluster=storage_cluster)
    if db_cluster.is_active:
        _schedule_storage_collection(
            db_cluster.id,
            audit_context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
        )
    return db_cluster


@router.delete(
    "/{storage_cluster_id}",
)
def delete_storage_cluster(
    storage_cluster_id: int,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_cluster = storageClusterCrud.get_storage_cluster(db, storage_cluster_id=storage_cluster_id)
    if db_cluster is None:
        raise HTTPException(status_code=404, detail="StorageCluster not found")
    storageClusterCrud.delete_storage_cluster(db=db, storage_cluster_id=storage_cluster_id)
    return {"message": "success"}


@router.get("/{storage_cluster_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel, openapi_extra={"ai_exposed": True, "ai_name": "get_storage_cluster_realtime", "ai_description": "查询存储集群实时容量趋势"})
def read_storage_cluster_realtime(
    storage_cluster_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    indicator: storageTrendSchema.TrendIndicator = 'used',
    db: Session = Depends(get_db)
):
    db_cluster = storageClusterCrud.get_storage_cluster(db, storage_cluster_id=storage_cluster_id)
    if db_cluster is None:
        raise HTTPException(status_code=404, detail="StorageCluster not found")
    trend_meta = build_storage_trend_meta(db, target_type="storage_cluster", target=db_cluster)
    real_time_data = get_storage_cluster_real_time(
        db=db,
        storage_cluster_id=storage_cluster_id,
        start_time=start_time,
        end_time=end_time,
        indicator=resolve_trend_indicator(indicator, trend_meta)
    )
    data_unit = trend_data_unit("storage_cluster", indicator)
    return commonSchema.ResponseStorageUsageModel[storageClusterSchema.StorageCluster](
        data=format_trend_data(real_time_data, data_unit),
        info=db_cluster,
        trend_meta=trend_meta,
        data_unit=data_unit,
    )


@router.get("/{storage_cluster_id}/analytics/capacity-change", response_model=dict)
def read_capacity_change(
    storage_cluster_id: int,
    time_range: AnalyticsTimeRange,
    db: Session = Depends(get_db),
) -> dict:
    db_cluster = storageClusterCrud.get_storage_cluster(db, storage_cluster_id)
    if db_cluster is None:
        raise HTTPException(status_code=404, detail="StorageCluster not found")
    result = get_capacity_change(db, storage_cluster_id, *time_range)
    return {
        **result,
        "trend_meta": build_storage_trend_meta(
            db,
            target_type="storage_cluster",
            target=db_cluster,
        ).model_dump(),
    }


@router.get("/{storage_cluster_id}/analytics/error-severity", response_model=dict)
def read_error_severity(
    storage_cluster_id: int,
    time_range: AnalyticsTimeRange,
    db: Session = Depends(get_db),
) -> dict:
    _require_storage_cluster(db, storage_cluster_id)
    return get_error_severity(db, storage_cluster_id, *time_range)


@router.get("/{storage_cluster_id}/analytics/top-latency", response_model=dict | list)
def read_top_latency(
    storage_cluster_id: int,
    time_range: AnalyticsTimeRange,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    object_type: Annotated[
        Literal["volume", "workload", "node"] | None,
        Query(),
    ] = None,
    db: Session = Depends(get_db),
) -> dict | list:
    _require_storage_cluster(db, storage_cluster_id)
    return get_top_latency(
        db,
        storage_cluster_id,
        *time_range,
        limit=limit,
        object_type=object_type,
    )


@router.get(
    "/{storage_cluster_id}/analytics/repeated-faults",
    response_model=(
        storageHealthAnalyticsSchema.RepeatedFaultList
        | list[storageHealthAnalyticsSchema.RepeatedFaultOut]
    ),
)
def read_repeated_faults(
    storage_cluster_id: int,
    time_range: AnalyticsTimeRange,
    db: Session = Depends(get_db),
) -> storageHealthAnalyticsSchema.RepeatedFaultList | list[
    storageHealthAnalyticsSchema.RepeatedFaultOut
]:
    _require_storage_cluster(db, storage_cluster_id)
    return get_repeated_faults(db, storage_cluster_id, *time_range)


@router.get(
    "/{storage_cluster_id}/analytics/system-events",
    response_model=storageHealthAnalyticsSchema.SystemEventPage,
    response_model_exclude_unset=True,
)
def read_system_events(
    storage_cluster_id: int,
    time_range: AnalyticsTimeRange,
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    severity: Annotated[
        Literal["critical", "error", "warning", "info"] | None,
        Query(),
    ] = None,
    fingerprint: Annotated[str | None, Query(max_length=512)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
) -> storageHealthAnalyticsSchema.SystemEventPage:
    _require_storage_cluster(db, storage_cluster_id)
    query = {
        "keyword": keyword.strip() if keyword else None,
        "severity": severity,
        "page": page,
        "page_size": page_size,
    }
    if fingerprint is not None:
        query["fingerprint"] = fingerprint
    return get_system_events(db, storage_cluster_id, *time_range, **query)


@router.get(
    "/{storage_cluster_id}/analytics/system-events/{event_id}",
    response_model=storageHealthAnalyticsSchema.SystemEventOut,
)
def read_system_event_detail(
    storage_cluster_id: int,
    event_id: Annotated[int, Path(ge=1)],
    db: Session = Depends(get_db),
) -> storageHealthAnalyticsSchema.SystemEventOut:
    _require_storage_cluster(db, storage_cluster_id)
    event = get_system_event_detail(db, storage_cluster_id, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="厂商系统事件不存在")
    return event


@router.get("/{storage_cluster_id}/analytics/export")
def export_analytics(
    storage_cluster_id: int,
    time_range: AnalyticsTimeRange,
    export_format: Annotated[
        Literal["csv", "excel", "pdf"],
        Query(alias="format"),
    ],
    section: Annotated[
        Literal["capacity", "severity", "latency", "faults", "all"],
        Query(),
    ] = "all",
    db: Session = Depends(get_db),
) -> StreamingResponse:
    _require_storage_cluster(db, storage_cluster_id)
    content, media_type, filename = export_storage_health(
        db,
        storage_cluster_id,
        *time_range,
        export_format=export_format,
        section=section,
    )
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
