# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session, joinedload
from models import Group, Project, StorageUsage
from schemas import groupSchema
from sqlalchemy import or_, desc, asc
from datetime import datetime, timedelta
from crud.questDbCrud import get_real_time_data_by_id
from utils.query import get_sort_column


def get_group_by_id(db: Session, group_id: int):
    return db.query(Group).filter(Group.id == group_id).first()


def get_groups(db: Session, page: int | None = None, size: int | None = None, nameLike: str | None = None,
               prop: str | None = None,
               order: str | None = None, qtree_id: int | None = None, project_id: int | None = None,
               storage_cluster_id: int | None = None):
    query = db.query(Group)
    conditions = []
    if nameLike:
        conditions.append(or_(Group.name.like(f"%{nameLike}%"), Group.linux_path.like(f"%{nameLike}%")))
    if qtree_id:
        conditions.append(Group.qtree_id == qtree_id)
    if project_id:
        conditions.append(Group.project_id == project_id)
    if storage_cluster_id:
        conditions.append(Group.storage_cluster_id == storage_cluster_id)

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


def create_group(db: Session, group: groupSchema.GroupCreate):
    db_group = Group(**group.model_dump(exclude={'in_charge_user'}))
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


def update_group(db: Session, group_id: int, group: groupSchema.GroupUpdate):
    db_group = db.query(Group).filter(Group.id == group_id).first()
    if db_group:
        for key, value in group.model_dump(exclude={'in_charge_user'}).items():
            setattr(db_group, key, value)
        db.commit()
        db.refresh(db_group)
    return db_group


def delete_group(db: Session, group_id: int):
    #  先删除group下用户信息
    db.query(StorageUsage).filter_by(group_id=group_id).delete()
    db.commit()
    db_group = db.query(Group).options(
        joinedload(Group.project),
        joinedload(Group.qtree)
    ).filter(Group.id == group_id).first()
    if db_group:
        db.delete(db_group)
        db.commit()
