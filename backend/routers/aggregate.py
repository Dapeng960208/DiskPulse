# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Annotated, List
from datetime import datetime
from schemas import aggregateSchema, commonSchema
from crud import aggregateCrud
from dependencies import get_db, require_super_admin

router = APIRouter(
    prefix="/aggregates",
    tags=["aggregates"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=aggregateSchema.Aggregate)
def create_aggregate(
    aggregate: aggregateSchema.AggregateCreate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return aggregateCrud.create_aggregate(db=db, aggregate=aggregate)


@router.get("/", response_model=commonSchema.ResponseModel)
def read_aggregates(page: int | None = 1, size: int | None = 20, nameLike: str | None = None, prop: str | None = None,
                    order: str | None = None, storage_cluster_id: int | None = None, db: Session = Depends(get_db)):
    aggregates, total = aggregateCrud.get_aggregates(db=db, page=page, size=size, nameLike=nameLike, prop=prop,
                                                     order=order, storage_cluster_id=storage_cluster_id)
    return commonSchema.ResponseModel[aggregateSchema.Aggregate](content=aggregates, total=total)


@router.get("/{aggregate_id}", response_model=aggregateSchema.Aggregate)
def read_aggregate(aggregate_id: int, db: Session = Depends(get_db)):
    db_aggregate = aggregateCrud.get_aggregate_by_id(db, aggregate_id=aggregate_id)
    if db_aggregate is None:
        raise HTTPException(status_code=404, detail="Aggregate not found")
    return db_aggregate


@router.get("/{aggregate_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel)
def read_aggregate_realtime_data(aggregate_id: int, start_time: datetime | None = None,
                                 end_time: datetime | None = None,
                                 indicator: str = 'used', db: Session = Depends(get_db)):
    db_aggregate = aggregateCrud.get_aggregate_by_id(db, aggregate_id=aggregate_id)
    if db_aggregate is None:
        raise HTTPException(status_code=404, detail="Qtree not found")
    real_time_data = aggregateCrud.get_aggregate_real_time_data_by_id(db=db, start_time=start_time,
                                                                      end_time=end_time,
                                                                      aggregate_id=aggregate_id,
                                                                      indicator=indicator)
    return commonSchema.ResponseStorageUsageModel[aggregateSchema.Aggregate](data=real_time_data,
                                                                             info=db_aggregate)


@router.put("/{aggregate_id}", response_model=aggregateSchema.Aggregate)
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


@router.delete("/{aggregate_id}", response_model=aggregateSchema.Aggregate)
def delete_aggregate(
    aggregate_id: int,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_aggregate = aggregateCrud.get_aggregate_by_id(db, aggregate_id=aggregate_id)
    if db_aggregate is None:
        raise HTTPException(status_code=404, detail="Aggregate not found")
    return aggregateCrud.delete_aggregate(db=db, aggregate_id=aggregate_id)


@router.get('/storage-trees/', response_model=commonSchema.ResponseResourceModel)
def get_aggregate_storage_trees(
    value_type: str = 'limit',
    storage_cluster_id: Annotated[int | None, Query(ge=1)] = None,
    db: Session = Depends(get_db),
):
    tree = aggregateCrud.get_aggregate_tree_summary(
        db=db,
        value_type=value_type,
        storage_cluster_id=storage_cluster_id,
    )
    return commonSchema.ResponseResourceModel(data=tree)


@router.get('/{aggregate_id}/storage-tree', response_model=commonSchema.ResponseResourceModel)
def get_aggregate_storage_tree_by_id(aggregate_id: int, value_type: str = 'used', db: Session = Depends(get_db)):
    db_aggregate = aggregateCrud.get_aggregate_by_id(db, aggregate_id=aggregate_id)
    if db_aggregate is None:
        raise HTTPException(status_code=404, detail="Aggregate not found")
    tree = aggregateCrud.get_aggregate_tree_summary_by_name(db=db, aggregate_name=db_aggregate.name,
                                                            value_type=value_type)
    return commonSchema.ResponseResourceModel(data=tree)
