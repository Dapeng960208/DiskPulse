# -*- coding: utf-8 -*-
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models import Group, ProjectStorageEnvironment, Qtree, StorageUsage, Volume
from schemas import groupSchema
from sqlalchemy import or_, desc, asc
from datetime import datetime, timedelta
from crud.questDbCrud import get_real_time_data_by_id
from utils.query import get_sort_column
from utils.storageTarget import resolve_group_storage_target


def get_group_by_id(db: Session, group_id: int):
    return db.query(Group).filter(Group.id == group_id).first()


def get_groups(db: Session, page: int | None = None, size: int | None = None, nameLike: str | None = None,
               prop: str | None = None,
               order: str | None = None, qtree_id: int | None = None, project_id: int | None = None,
               storage_cluster_id: int | None = None, project_environment_id: int | None = None):
    query = db.query(Group)
    conditions = []
    if nameLike:
        conditions.append(or_(Group.name.like(f"%{nameLike}%"), Group.linux_path.like(f"%{nameLike}%")))
    if qtree_id:
        conditions.append(Group.qtree_id == qtree_id)
    if project_id is not None or storage_cluster_id is not None:
        query = query.join(
            ProjectStorageEnvironment,
            ProjectStorageEnvironment.id == Group.project_environment_id,
        )
    if project_id is not None:
        conditions.append(ProjectStorageEnvironment.project_id == project_id)
    if storage_cluster_id is not None:
        conditions.append(
            ProjectStorageEnvironment.storage_cluster_id == storage_cluster_id
        )
    if project_environment_id is not None:
        conditions.append(Group.project_environment_id == project_environment_id)

    query = query.filter(*conditions)
    total = query.count()
    sort_column = get_sort_column(Group, prop)
    if sort_column is not None:
        if order and order.lower() == 'descending':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(Group.use_ratio.desc())
    if page and size:
        query = query.offset((page - 1) * size).limit(size)
    groups = query.all()

    return groups, total


def get_group_real_time_data_by_id(db: Session, group_id: int, start_time: datetime | None = None,
                                   end_time: datetime | None = None, indicator: str = 'used'):
    return get_real_time_data_by_id(db=db, attribute_id=group_id, start_time=start_time, end_time=end_time,
                                    indicator=indicator, table_prefix='group')


def create_group(
    db: Session,
    group: groupSchema.GroupBindingCreate,
):
    data = group.model_dump(exclude_unset=True)
    _validate_binding(db, data)
    data.setdefault("volume_id", None)
    data.setdefault("qtree_id", None)
    db_group = Group(**data)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


def update_group(
    db: Session,
    group_id: int,
    group: groupSchema.GroupBindingUpdate,
):
    db_group = db.query(Group).filter(Group.id == group_id).first()
    if db_group:
        data = group.model_dump(exclude_unset=True)
        if data.get("project_environment_id") is not None:
            _validate_binding(db, data)
            data.setdefault("volume_id", None)
            data.setdefault("qtree_id", None)
        for key, value in data.items():
            setattr(db_group, key, value)
        db.commit()
        db.refresh(db_group)
    return db_group


def _validate_binding(db: Session, data: dict) -> ProjectStorageEnvironment:
    environment = (
        db.query(ProjectStorageEnvironment)
        .filter(ProjectStorageEnvironment.id == data["project_environment_id"])
        .first()
    )
    if environment is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project storage environment not found",
        )

    if data.get("volume_id") is not None:
        target = db.query(Volume).filter(Volume.id == data["volume_id"]).first()
        target_name = "Volume"
    else:
        if (environment.storage_cluster.storage_type or "").lower() == "isilon":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Isilon environments do not support qtree targets",
            )
        target = db.query(Qtree).filter(Qtree.id == data.get("qtree_id")).first()
        target_name = "Qtree"

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{target_name} not found",
        )
    if target.storage_cluster_id != environment.storage_cluster_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{target_name} does not belong to the environment storage cluster",
        )
    return environment


def serialize_group(group: Group) -> dict:
    result = {
        column.name: getattr(group, column.name)
        for column in Group.__table__.columns
    }
    environment = group.project_environment
    project = environment.project
    storage_cluster = environment.storage_cluster
    result["project"] = project
    result["project_environment"] = environment
    result["storage_cluster"] = storage_cluster

    resolved = resolve_group_storage_target(group)
    target = resolved["target"]
    if target is not None:
        result["storage_target"] = {
            "type": resolved["target_type"],
            "id": target.id,
            "name": target.name,
        }
        if resolved["target_type"] == "qtree":
            result["qtree"] = target
    else:
        result["storage_target"] = None
    return result


def delete_group(db: Session, group_id: int):
    #  先删除group下用户信息
    db.query(StorageUsage).filter_by(group_id=group_id).delete()
    db.commit()
    db_group = db.query(Group).options(
        joinedload(Group.project_environment),
        joinedload(Group.qtree)
    ).filter(Group.id == group_id).first()
    if db_group:
        db.delete(db_group)
        db.commit()
