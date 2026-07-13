# -*- coding: utf-8 -*-
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models import Group, Volume, Qtree
from schemas import volumeSchema
from sqlalchemy import or_, desc, asc
from utils.common import convert_GB_to_TB
from typing import List
from datetime import datetime
from crud.questDbCrud import get_real_time_data_by_id
from utils.query import get_sort_column


def get_volume_by_id(db: Session, volume_id: int):
    return db.query(Volume).filter(Volume.id == volume_id).first()


def get_volumes(db: Session, page: int, size: int, nameLike: str | None = None, prop: str | None = None,
                order: str | None = None, storage_cluster_id: int | None = None):
    query = db.query(Volume)
    if nameLike and len(nameLike.strip()) > 0:
        query = query.filter(or_(Volume.name.like(f"%{nameLike}%"), Volume.vserver.like(f"%{nameLike}%")))
    if storage_cluster_id:
        query = query.filter(Volume.storage_cluster_id == storage_cluster_id)
    total = query.count()
    sort_column = get_sort_column(Volume, prop)
    if sort_column is not None:
        if order and order.lower() == 'descending':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(Volume.use_ratio.desc())
    volumes = query.offset((page - 1) * size).limit(size).all()

    return volumes, total


def create_volume(db: Session, volume: volumeSchema.VolumeCreate):
    db_volume = Volume(**volume.model_dump())
    db.add(db_volume)
    db.commit()
    db.refresh(db_volume)
    return db_volume


def update_volume(db: Session, volume_id: int, volume: volumeSchema.VolumeUpdate):
    db_volume = db.query(Volume).filter(Volume.id == volume_id).first()
    if db_volume:
        for key, value in volume.model_dump().items():
            setattr(db_volume, key, value)
        db.commit()
        db.refresh(db_volume)
    return db_volume


def delete_volume(db: Session, volume_id: int):
    db_volume = db.query(Volume).filter(Volume.id == volume_id).first()
    if db_volume:
        if db.query(Group.id).filter(Group.volume_id == volume_id).first():
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Volume is referenced by a group",
            )
        try:
            db.delete(db_volume)
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Volume is referenced",
            ) from error
    return db_volume


def get_volume_real_time_data_by_id(db: Session, volume_id: int, start_time: datetime | None = None,
                                    end_time: datetime | None = None, indicator: str = 'used'):
    return get_real_time_data_by_id(db=db, attribute_id=volume_id, start_time=start_time, end_time=end_time,
                                    indicator=indicator, table_prefix='volume')

# def get_aggregate_tree_summary_by_name(db: Session, aggregate_name: int, value_type: str) -> List:
#     volume_dbs = db.query(Volume).filter(Volume.aggregate == aggregate_name, Volume.used >= 0).all()
#     volumes = []
#     for volume_db in volume_dbs:
#         qtree_dbs = db.query(Qtree).filter(Qtree.volume_id == volume_db.id, Qtree.used >= 0).all()
#         qtrees = [{'limit': convert_GB_to_TB(qtree_db.limit),
#                    'used': convert_GB_to_TB(qtree_db.used),
#                    'value': convert_GB_to_TB(getattr(qtree_db, value_type, 0)),
#                    'name': qtree_db.name,
#                    'path': qtree_db.name,
#                    'used_ratio': qtree_db.use_ratio}
#                   for qtree_db in qtree_dbs]
#
#         volumes.append(
#             {'limit': convert_GB_to_TB(volume_db.limit),
#              'used': convert_GB_to_TB(volume_db.used),
#              'value': convert_GB_to_TB(getattr(volume_db, value_type)),
#              'name': volume_db.name,
#              'path': volume_db.name,
#              'used_ratio': volume_db.use_ratio,
#              'children': qtrees
#              }
#         )
#     return volumes
#
#
# def get_aggregate_tree_summary(db: Session, value_type: str) -> List:
#     aggregate_dbs = db.query(Volume.vserver).filter(Aggregate.used >= 0).all()
#     return [
#         {'limit': convert_GB_to_TB(aggregate_db.limit),
#          'used': convert_GB_to_TB(aggregate_db.used),
#          'value': convert_GB_to_TB(getattr(aggregate_db, value_type)),
#          'name': aggregate_db.name,
#          'path': aggregate_db.name,
#          'used_ratio': aggregate_db.use_ratio,
#          'children': get_aggregate_tree_summary_by_name(db=db, aggregate_name=aggregate_db.name, value_type=value_type)
#          } for aggregate_db in aggregate_dbs
#     ]
