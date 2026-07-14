# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from schemas import storageClusterSchema, commonSchema
from crud import storageClusterCrud
from crud.questDbCrud import get_storage_cluster_real_time
from dependencies import get_db, require_super_admin
from services.storageClusterService import schedule_storage_collection as _schedule_storage_collection

router = APIRouter(
    prefix="/storage-clusters",
    tags=["storage-clusters"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=commonSchema.ResponseModel)
def read_storage_clusters(
        page: int | None = 1,
        size: int | None = 20,
        nameLike: str | None = None,
        prop: str | None = None,
        order: str | None = None,
        is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    total,storage_clusters = storageClusterCrud.get_storage_clusters(db, page, size, nameLike, prop, order, is_active)
    return commonSchema.ResponseModel[storageClusterSchema.StorageCluster](content=storage_clusters, total=total)


@router.post("/", response_model=storageClusterSchema.StorageCluster)
def create_storage_cluster(
    storage_cluster: storageClusterSchema.StorageClusterCreate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    db_cluster = storageClusterCrud.create_storage_cluster(db=db, storage_cluster=storage_cluster)
    if db_cluster.is_active:
        _schedule_storage_collection(db_cluster.id)
    return db_cluster


@router.get("/{storage_cluster_id}", response_model=storageClusterSchema.StorageCluster)
def read_storage_cluster(storage_cluster_id: int, db: Session = Depends(get_db)):
    db_cluster = storageClusterCrud.get_storage_cluster(db, storage_cluster_id=storage_cluster_id)
    if db_cluster is None:
        raise HTTPException(status_code=404, detail="StorageCluster not found")
    return db_cluster


@router.put("/{storage_cluster_id}", response_model=storageClusterSchema.StorageCluster)
def update_storage_cluster(
    storage_cluster_id: int,
    storage_cluster: storageClusterSchema.StorageClusterUpdate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    db_cluster = storageClusterCrud.get_storage_cluster(db, storage_cluster_id=storage_cluster_id)
    if db_cluster is None:
        raise HTTPException(status_code=404, detail="StorageCluster not found")
    db_cluster = storageClusterCrud.update_storage_cluster(db=db, storage_cluster_id=storage_cluster_id,
                                                           storage_cluster=storage_cluster)
    if db_cluster.is_active:
        _schedule_storage_collection(db_cluster.id)
    return db_cluster


@router.delete("/{storage_cluster_id}")
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


@router.get("/{storage_cluster_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel)
def read_storage_cluster_realtime(
    storage_cluster_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    indicator: str = 'used',
    db: Session = Depends(get_db)
):
    db_cluster = storageClusterCrud.get_storage_cluster(db, storage_cluster_id=storage_cluster_id)
    if db_cluster is None:
        raise HTTPException(status_code=404, detail="StorageCluster not found")
    real_time_data = get_storage_cluster_real_time(
        db=db,
        storage_cluster_id=storage_cluster_id,
        start_time=start_time,
        end_time=end_time,
        indicator=indicator
    )
    return commonSchema.ResponseStorageUsageModel[storageClusterSchema.StorageCluster](
        data=real_time_data,
        info=db_cluster
    )
