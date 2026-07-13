# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from models import StorageCluster
from schemas.storageClusterSchema import StorageClusterCreate, StorageClusterUpdate
from typing import Optional, List
from utils.query import get_sort_column


def get_storage_cluster(db: Session, storage_cluster_id: int) -> Optional[StorageCluster]:
    return db.query(StorageCluster).filter(StorageCluster.id == storage_cluster_id).first()


def get_storage_clusters(db: Session, page: int | None = None, size: int | None = None, nameLike: str | None = None,
                       prop: str | None = None,
                       order: str | None = None, is_active: Optional[bool] = None):
    query = db.query(StorageCluster)
    if is_active is not None:
        query = query.filter(StorageCluster.is_active.is_(is_active))
    if nameLike and len(nameLike.strip()) > 0:
        query = query.filter(StorageCluster.name.like(f"%{nameLike}%"))
    total = query.count()
    sort_column = get_sort_column(StorageCluster, prop)
    if sort_column is not None:
        if order and order.lower() == 'descending':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(StorageCluster.use_ratio.desc())
    if page and size:
        query = query.offset((page - 1) * size).limit(size)

    storage_clusters = query.all()
    return total,storage_clusters


def create_storage_cluster(db: Session, storage_cluster: StorageClusterCreate) -> StorageCluster:

    db_storage_cluster = StorageCluster(**storage_cluster.model_dump())
    db.add(db_storage_cluster)
    db.commit()
    db.refresh(db_storage_cluster)
    return db_storage_cluster


def update_storage_cluster(db: Session, storage_cluster_id: int, storage_cluster: StorageClusterUpdate) -> Optional[StorageCluster]:
    db_storage_cluster = get_storage_cluster(db, storage_cluster_id)
    if db_storage_cluster:
        update_data = storage_cluster.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_storage_cluster, key, value)
        db.commit()
        db.refresh(db_storage_cluster)
    return db_storage_cluster


def delete_storage_cluster(db: Session, storage_cluster_id: int) -> bool:
    db_storage_cluster = get_storage_cluster(db, storage_cluster_id)
    if db_storage_cluster:
        db.delete(db_storage_cluster)
        db.commit()
        return True
    return False
