# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session
from models import Aggregate, Volume, Qtree
from schemas import aggregateSchema
from sqlalchemy import or_, desc, asc
from utils.common import convert_GB_to_TB
from typing import List
from datetime import datetime
from crud.questDbCrud import get_real_time_data_by_id


def get_aggregate_by_id(db: Session, aggregate_id: int):
    return db.query(Aggregate).filter(Aggregate.id == aggregate_id).first()


def get_aggregates(db: Session, page: int, size: int, nameLike: str | None = None, prop: str | None = None,
                   order: str | None = None, storage_cluster_id: int | None = None):
    query = db.query(Aggregate)
    if nameLike and len(nameLike.strip()) > 0:
        query = query.filter(Aggregate.name.like(f"%{nameLike}%"))
    if storage_cluster_id:
        query = query.filter(Aggregate.storage_cluster_id == storage_cluster_id)
    total = query.count()
    if prop:
        if order and order.lower() == 'descending':
            query = query.order_by(desc(getattr(Aggregate, prop)))
        else:
            query = query.order_by(asc(getattr(Aggregate, prop)))
    else:
        query = query.order_by(Aggregate.use_ratio.desc())
    aggregates = query.offset((page - 1) * size).limit(size).all()

    return aggregates, total


def create_aggregate(db: Session, aggregate: aggregateSchema.AggregateCreate):
    db_aggregate = Aggregate(**aggregate.dict())
    db.add(db_aggregate)
    db.commit()
    db.refresh(db_aggregate)
    return db_aggregate


def update_aggregate(db: Session, aggregate_id: int, aggregate: aggregateSchema.AggregateUpdate):
    db_aggregate = db.query(Aggregate).filter(Aggregate.id == aggregate_id).first()
    if db_aggregate:
        for key, value in aggregate.dict().items():
            setattr(db_aggregate, key, value)
        db.commit()
        db.refresh(db_aggregate)
    return db_aggregate


def delete_aggregate(db: Session, aggregate_id: int):
    db_aggregate = db.query(Aggregate).filter(Aggregate.id == aggregate_id).first()
    if db_aggregate:
        db.delete(db_aggregate)
        db.commit()
    return db_aggregate


def get_aggregate_tree_summary(db: Session, value_type: str) -> List:
    volume_dbs = db.query(Volume).filter(Volume.used >= 0).all()
    volumes = []
    for volume_db in volume_dbs:
        qtree_dbs = db.query(Qtree).filter(Qtree.volume_id == volume_db.id, Qtree.used >= 0).all()
        qtrees = [{'limit': convert_GB_to_TB(qtree_db.limit),
                   'used': convert_GB_to_TB(qtree_db.used),
                   'value': convert_GB_to_TB(getattr(qtree_db, value_type, 0)),
                   'name': qtree_db.name,
                   'path': qtree_db.name,
                   'used_ratio': qtree_db.use_ratio}
                  for qtree_db in qtree_dbs]

        volumes.append(
            {'limit': convert_GB_to_TB(volume_db.limit),
             'used': convert_GB_to_TB(volume_db.used),
             'value': convert_GB_to_TB(getattr(volume_db, value_type)),
             'name': volume_db.name,
             'path': volume_db.name,
             'used_ratio': volume_db.use_ratio,
             'children': qtrees
             }
        )
    return volumes


def get_aggregate_tree_summary_by_name(db: Session, aggregate_name: str, value_type: str) -> List:
    volume_dbs = db.query(Volume).filter(Volume.aggregate == aggregate_name, Volume.used >= 0).all()
    volumes = []
    for volume_db in volume_dbs:
        qtree_dbs = db.query(Qtree).filter(Qtree.volume_id == volume_db.id, Qtree.used >= 0).all()
        qtrees = [
            {
                "limit": convert_GB_to_TB(qtree_db.limit),
                "used": convert_GB_to_TB(qtree_db.used),
                "value": convert_GB_to_TB(getattr(qtree_db, value_type, 0)),
                "name": qtree_db.name,
                "path": qtree_db.name,
                "used_ratio": qtree_db.use_ratio,
            }
            for qtree_db in qtree_dbs
        ]
        volumes.append(
            {
                "limit": convert_GB_to_TB(volume_db.limit),
                "used": convert_GB_to_TB(volume_db.used),
                "value": convert_GB_to_TB(getattr(volume_db, value_type, 0)),
                "name": volume_db.name,
                "path": volume_db.name,
                "used_ratio": volume_db.use_ratio,
                "children": qtrees,
            }
        )
    return volumes


def get_aggregate_real_time_data_by_id(db: Session, aggregate_id: int, start_time: datetime | None = None,
                                       end_time: datetime | None = None, indicator: str = 'used'):
    return get_real_time_data_by_id(db=db, attribute_id=aggregate_id, start_time=start_time, end_time=end_time,
                                    indicator=indicator, table_prefix='aggregate')
