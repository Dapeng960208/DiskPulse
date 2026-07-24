# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Annotated, List
from datetime import datetime
from schemas import aggregateSchema, commonSchema, storageTrendSchema
from crud import aggregateCrud
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
router = APIRouter(
    prefix="/aggregates",
    tags=["aggregates"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(require_super_admin)],
)


@router.post(
    "/",
    response_model=aggregateSchema.Aggregate,
)
def create_aggregate(
    aggregate: aggregateSchema.AggregateCreate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return aggregateCrud.create_aggregate(db=db, aggregate=aggregate)


@router.get(
    "/",
    response_model=commonSchema.ResponseModel,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "list_aggregates",
        "ai_description": "分页查询容量池",
        "ai_blacklist_fields": AI_STORAGE_CLUSTER_BLACKLIST_FIELDS,
    },
)
def read_aggregates(page: int | None = 1, size: int | None = 20, nameLike: str | None = None, prop: str | None = None,
                    order: str | None = None, storage_cluster_id: int | None = None,
                    use_ratio_min: UseRatioMinimum = None, use_ratio_max: UseRatioMaximum = None,
                    db: Session = Depends(get_db)):
    use_ratio_min, use_ratio_max = validate_use_ratio_range(use_ratio_min, use_ratio_max)
    aggregates, total = aggregateCrud.get_aggregates(db=db, page=page, size=size, nameLike=nameLike, prop=prop,
                                                     order=order, storage_cluster_id=storage_cluster_id,
                                                     use_ratio_min=use_ratio_min, use_ratio_max=use_ratio_max)
    return commonSchema.ResponseModel[aggregateSchema.Aggregate](content=aggregates, total=total)


@router.get(
    "/{aggregate_id}",
    response_model=aggregateSchema.Aggregate,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "get_aggregate",
        "ai_description": "查询指定容量池",
        "ai_blacklist_fields": AI_STORAGE_CLUSTER_BLACKLIST_FIELDS,
    },
)
def read_aggregate(aggregate_id: int, db: Session = Depends(get_db)):
    db_aggregate = aggregateCrud.get_aggregate_by_id(db, aggregate_id=aggregate_id)
    if db_aggregate is None:
        raise HTTPException(status_code=404, detail="Aggregate not found")
    return db_aggregate


@router.get("/{aggregate_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel, openapi_extra={"ai_exposed": True, "ai_system_management": True, "ai_name": "get_aggregate_realtime", "ai_description": "查询容量池实时容量趋势", "ai_blacklist_fields": AI_STORAGE_CLUSTER_BLACKLIST_FIELDS})
def read_aggregate_realtime_data(aggregate_id: int, start_time: datetime | None = None,
                                 end_time: datetime | None = None,
                                 indicator: storageTrendSchema.TrendIndicator = 'used', db: Session = Depends(get_db)):
    db_aggregate = aggregateCrud.get_aggregate_by_id(db, aggregate_id=aggregate_id)
    if db_aggregate is None:
        raise HTTPException(status_code=404, detail="Aggregate not found")
    trend_meta = build_storage_trend_meta(db, target_type="aggregate", target=db_aggregate)
    real_time_data = aggregateCrud.get_aggregate_real_time_data_by_id(db=db, start_time=start_time,
                                                                      end_time=end_time,
                                                                      aggregate_id=aggregate_id,
                                                                      indicator=resolve_trend_indicator(indicator, trend_meta))
    data_unit = trend_data_unit("aggregate", indicator)
    return commonSchema.ResponseStorageUsageModel[aggregateSchema.Aggregate](data=format_trend_data(real_time_data, data_unit),
                                                                             info=db_aggregate,
                                                                             trend_meta=trend_meta,
                                                                             data_unit=data_unit)


@router.put(
    "/{aggregate_id}",
    response_model=aggregateSchema.Aggregate,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "update_aggregate",
        "ai_description": "更新容量池",
        "ai_blacklist_fields": AI_STORAGE_CLUSTER_BLACKLIST_FIELDS,
    },
)
def update_aggregate(
    aggregate_id: int,
    aggregate: aggregateSchema.AggregateUpdate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_aggregate = aggregateCrud.get_aggregate_by_id(db, aggregate_id=aggregate_id)
    if db_aggregate is None:
        raise HTTPException(status_code=404, detail="Aggregate not found")
    return aggregateCrud.update_aggregate(db=db, aggregate_id=aggregate_id, aggregate=aggregate)


@router.delete(
    "/{aggregate_id}",
    response_model=aggregateSchema.Aggregate,
)
def delete_aggregate(
    aggregate_id: int,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_aggregate = aggregateCrud.get_aggregate_by_id(db, aggregate_id=aggregate_id)
    if db_aggregate is None:
        raise HTTPException(status_code=404, detail="Aggregate not found")
    return aggregateCrud.delete_aggregate(db=db, aggregate_id=aggregate_id)


@router.get('/storage-trees/', response_model=commonSchema.ResponseResourceModel, openapi_extra={"ai_exposed": True, "ai_system_management": True, "ai_name": "list_aggregate_storage_trees", "ai_description": "查询容量池存储树"})
def get_aggregate_storage_trees(
    value_type: str = 'limit',
    storage_cluster_id: Annotated[int | None, Query(ge=1)] = None,
    use_ratio_min: UseRatioMinimum = None,
    use_ratio_max: UseRatioMaximum = None,
    db: Session = Depends(get_db),
):
    use_ratio_min, use_ratio_max = validate_use_ratio_range(use_ratio_min, use_ratio_max)
    tree = aggregateCrud.get_aggregate_tree_summary(
        db=db,
        value_type=value_type,
        storage_cluster_id=storage_cluster_id,
        use_ratio_min=use_ratio_min,
        use_ratio_max=use_ratio_max,
    )
    return commonSchema.ResponseResourceModel(data=tree, data_unit="TB")


@router.get('/{aggregate_id}/storage-tree', response_model=commonSchema.ResponseResourceModel, openapi_extra={"ai_exposed": True, "ai_system_management": True, "ai_name": "get_aggregate_storage_tree", "ai_description": "查询指定容量池存储树"})
def get_aggregate_storage_tree_by_id(
    aggregate_id: int,
    value_type: str = 'used',
    use_ratio_min: UseRatioMinimum = None,
    use_ratio_max: UseRatioMaximum = None,
    db: Session = Depends(get_db),
):
    use_ratio_min, use_ratio_max = validate_use_ratio_range(use_ratio_min, use_ratio_max)
    db_aggregate = aggregateCrud.get_aggregate_by_id(db, aggregate_id=aggregate_id)
    if db_aggregate is None:
        raise HTTPException(status_code=404, detail="Aggregate not found")
    tree = aggregateCrud.get_aggregate_tree_summary_by_name(db=db, aggregate_name=db_aggregate.name,
                                                            value_type=value_type,
                                                            use_ratio_min=use_ratio_min,
                                                            use_ratio_max=use_ratio_max)
    return commonSchema.ResponseResourceModel(data=tree, data_unit="TB")
