# -*- coding: utf-8 -*-
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from sqlalchemy.exc import IntegrityError

from models import Group, StorageCluster
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
        if update_data.get("protocol", db_storage_cluster.protocol) == "http":
            update_data["tls_verify"] = False
        storage_type = update_data.get("storage_type", db_storage_cluster.storage_type)
        cache_mode = update_data.get(
            "isilon_session_cache_mode",
            db_storage_cluster.isilon_session_cache_mode,
        )
        if storage_type != "isilon":
            update_data["isilon_session_cache_mode"] = "none"
            update_data["isilon_session_cache_path"] = None
        elif cache_mode == "file":
            update_data["isilon_session_cache_path"] = (
                update_data.get("isilon_session_cache_path")
                or db_storage_cluster.isilon_session_cache_path
                or ".isilon_cache/cache.json"
            )
        else:
            update_data["isilon_session_cache_path"] = None
        for key, value in update_data.items():
            setattr(db_storage_cluster, key, value)
        db.commit()
        db.refresh(db_storage_cluster)
    return db_storage_cluster


def delete_storage_cluster(db: Session, storage_cluster_id: int) -> bool:
    db_storage_cluster = get_storage_cluster(db, storage_cluster_id)
    if db_storage_cluster:
        referenced = (
            db.query(Group.id)
            .filter(Group.storage_cluster_id == storage_cluster_id)
            .first()
        )
        if referenced:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Storage cluster is referenced by a group",
            )
        try:
            db.delete(db_storage_cluster)
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Storage cluster is referenced",
            ) from error
        return True
    return False
