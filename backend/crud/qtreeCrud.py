# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session
from models import Qtree, Volume
from schemas import qtreeSchema
from sqlalchemy import or_, desc, asc
from crud.questDbCrud import get_real_time_data_by_id
from datetime import datetime, timedelta


def get_qtree_by_id(db: Session, qtree_id: int):
    return db.query(Qtree).filter(Qtree.id == qtree_id).first()


def get_qtrees(db: Session, page: int, size: int, nameLike: str | None = None, prop: str | None = None,
               order: str | None = None, volume_id: int | None = None, storage_cluster_id: int | None = None):
    query = db.query(Qtree)
    conditions = []
    if nameLike and len(nameLike.strip()) > 0:
        query = query.join(Volume, Qtree.volume)
        conditions.append(or_(Qtree.name.like(f"%{nameLike}%"), Volume.name.like(f"%{nameLike}%")))
    if volume_id:
        conditions.append(Qtree.volume_id == volume_id)
    if storage_cluster_id:
        conditions.append(Qtree.storage_cluster_id == storage_cluster_id)
    query = query.filter(*conditions)
    total = query.count()
    if prop:
        if order and order.lower() == 'descending':
            query = query.order_by(desc(getattr(Qtree, prop)))
        else:
            query = query.order_by(asc(getattr(Qtree, prop)))
    else:
        query = query.order_by(Qtree.use_ratio.desc())
    qtrees = query.offset((page - 1) * size).limit(size).all()

    return qtrees, total


def get_qtree_real_time_data_by_id(db: Session, qtree_id: int, start_time: datetime | None = None,
                                   end_time: datetime | None = None, indicator: str = 'used'):
    return get_real_time_data_by_id(db=db, attribute_id=qtree_id, start_time=start_time, end_time=end_time,
                                    indicator=indicator, table_prefix='qtree')


def create_qtree(db: Session, qtree: qtreeSchema.QtreeCreate):
    db_qtree = Qtree(**qtree.dict())
    db.add(db_qtree)
    db.commit()
    db.refresh(db_qtree)
    return db_qtree


def update_qtree(db: Session, qtree_id: int, qtree: qtreeSchema.QtreeUpdate):
    db_qtree = db.query(Qtree).filter(Qtree.id == qtree_id).first()
    if db_qtree:
        for key, value in qtree.dict().items():
            setattr(db_qtree, key, value)
        db.commit()
        db.refresh(db_qtree)
    return db_qtree


def delete_qtree(db: Session, qtree_id: int):
    db_qtree = db.query(Qtree).filter(Qtree.id == qtree_id).first()
    if db_qtree:
        db.delete(db_qtree)
        db.commit()
    return db_qtree
