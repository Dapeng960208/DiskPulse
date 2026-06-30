# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session
from models import StorageBackUpRecord
from schemas import storageBackUpRecordSchema
from sqlalchemy import or_, desc, asc
from crud.questDbCrud import get_real_time_data_by_id, get_real_time_data_by_ids
from datetime import datetime, timedelta
from io import BytesIO
from datetime import datetime
import os
from sqlalchemy.orm import Session


def get_storage_back_up_records(db: Session, page: int | None = None, size: int | None = None,
                                nameLike: str | None = None,
                                prop: str | None = None,
                                order: str | None = None, user_id: int | None = None):
    query = db.query(StorageBackUpRecord)
    conditions = []
    if nameLike and len(nameLike.strip()) > 0:
        conditions.append(or_(StorageBackUpRecord.source_path.like(f"%{nameLike}%"),
                              StorageBackUpRecord.destination_path.like(f"%{nameLike}%")))
    if user_id:
        conditions.append(StorageBackUpRecord.user_id == user_id)
    query = query.filter(*conditions)
    total = query.count()
    if prop:
        if order and order.lower() == 'descending':
            query = query.order_by(desc(getattr(StorageBackUpRecord, prop)))
        else:
            query = query.order_by(asc(getattr(StorageBackUpRecord, prop)))
    else:
        query = query.order_by(StorageBackUpRecord.end_time.desc())
    if page and size:
        query = query.offset((page - 1) * size).limit(size)
    storage_back_up_records = query.all()
    return storage_back_up_records, total


def get_storage_back_up_record_by_id(db: Session, storage_back_up_record_id: int):
    return db.query(StorageBackUpRecord).filter(StorageBackUpRecord.id == storage_back_up_record_id).first()
