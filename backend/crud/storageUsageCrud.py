# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session
from models import StorageUsage, Qtree, User
from schemas import storageUsageSchema
from sqlalchemy import or_, desc, asc
from crud.questDbCrud import get_real_time_data_by_id, get_real_time_data_by_ids
from datetime import datetime, timedelta
from io import BytesIO
from datetime import datetime
import os
from sqlalchemy.orm import Session
import pandas as pd
from utils.pdf.pdfReporter import PDFReportGenerator
from utils.query import get_sort_column


def get_storage_usage_by_id(db: Session, storage_usage_id: int):
    return db.query(StorageUsage).filter(StorageUsage.id == storage_usage_id).first()


def get_storage_usages(db: Session, page: int | None = None, size: int | None = None, nameLike: str | None = None,
                       prop: str | None = None,
                       order: str | None = None, user_id: int | None = None, group_id: int | None = None,
                       storage_cluster_id: int | None = None):
    query = db.query(StorageUsage)
    conditions = []
    if nameLike and len(nameLike.strip()) > 0:
        conditions.append(StorageUsage.linux_path.like(f"%{nameLike}%"))
    if user_id:
        conditions.append(StorageUsage.user_id == user_id)
    if group_id:
        conditions.append(StorageUsage.group_id == group_id)
    if storage_cluster_id:
        conditions.append(StorageUsage.storage_cluster_id == storage_cluster_id)
    query = query.filter(*conditions)
    total = query.count()
    sort_column = get_sort_column(StorageUsage, prop)
    if sort_column is not None:
        if order and order.lower() == 'descending':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(StorageUsage.use_ratio.desc())
    if page and size:
        query = query.offset((page - 1) * size).limit(size)
    storage_usages = query.all()

    return storage_usages, total


def get_storage_usages_real_time_data_by_id(db: Session, storage_usage_id: int, start_time: datetime | None = None,
                                            end_time: datetime | None = None, indicator: str = 'used'):
    return get_real_time_data_by_id(db=db, attribute_id=storage_usage_id, start_time=start_time, end_time=end_time,
                                    indicator=indicator)


def create_storage_usage(db: Session, storage_usage: storageUsageSchema.StorageUsageCreate, linux_path: str):
    exit_storage_usage = db.query(StorageUsage).filter(StorageUsage.linux_path == linux_path).first()
    if exit_storage_usage:
        return True, exit_storage_usage
    db_storage_usage = StorageUsage(user_id=storage_usage.user_id, group_id=storage_usage.group_id,
                                    linux_path=linux_path, updated_at=datetime.now())
    db.add(db_storage_usage)
    db.commit()
    db.refresh(db_storage_usage)
    return False, db_storage_usage


def update_storage_usage(db: Session, storage_usage_id: int, storage_usage: storageUsageSchema.StorageUsageUpdate):
    db_storage_usage = db.query(StorageUsage).filter(StorageUsage.id == storage_usage_id).first()
    if db_storage_usage:
        for key, value in storage_usage.model_dump().items():
            setattr(db_storage_usage, key, value)
        db.commit()
        db.refresh(db_storage_usage)
    return db_storage_usage


def delete_storage_usage(db: Session, storage_usage_id: int):
    db_storage_usage = db.query(StorageUsage).filter(StorageUsage.id == storage_usage_id).first()
    if db_storage_usage:
        db.delete(db_storage_usage)
        db.commit()
    return db_storage_usage


def get_export_data(db: Session, nameLike: str | None = None, prop: str | None = None,
                    order: str | None = None, user_id: int | None = None, group_id: int | None = None,
                    storage_cluster_id: int | None = None):
    storage_usage_dbs, _ = get_storage_usages(db=db, nameLike=nameLike, prop=prop, order=order, user_id=user_id,
                                              group_id=group_id, storage_cluster_id=storage_cluster_id)
    storage_usages = [storageUsageSchema.StorageUsageExport(linux_path=storage_usage_db.linux_path,
                                                            limit=storage_usage_db.limit,
                                                            soft_limit=storage_usage_db.soft_limit,
                                                            used=storage_usage_db.used,
                                                            use_ratio=storage_usage_db.use_ratio,
                                                            soft_use_ratio=storage_usage_db.soft_use_ratio,
                                                            file_used=storage_usage_db.file_used,
                                                            access_time=storage_usage_db.access_time,
                                                            modify_time=storage_usage_db.modify_time) for
                      storage_usage_db in storage_usage_dbs]
    df_storage_usage = pd.DataFrame([storage_usage.model_dump() for storage_usage in storage_usages])
    storage_usage_column_headers = {'linux_path': '路径', 'limit': "硬限额", 'soft_limit': "软限额",
                                    'used': '已使用', 'use_ratio': '硬使用率', 'soft_use_ratio': '软使用率',
                                    'file_used': '文件数', "access_time": "访问时间", "modify_time": "修改时间"}
    df_storage_usage.rename(columns=storage_usage_column_headers, inplace=True)
    return df_storage_usage


def export_storage_usage_to_excel(db: Session, nameLike: str | None = None, prop: str | None = None,
                                  order: str | None = None, user_id: int | None = None, group_id: int | None = None,
                                  storage_cluster_id: int | None = None):
    df_storage_usage = get_export_data(db, nameLike, prop, order, user_id, group_id, storage_cluster_id)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_storage_usage.to_excel(writer, sheet_name='存储使用明细', index=False)
    output.seek(0)
    return output


def export_storage_usage_to_pdf(db: Session, nameLike: str | None = None, prop: str | None = None,
                                order: str | None = None, user_id: int | None = None, group_id: int | None = None,
                                storage_cluster_id: int | None = None):
    from appConfig import base_config
    df_storage_usage = get_export_data(db, nameLike, prop, order, user_id, group_id, storage_cluster_id)
    company_name = base_config.get('application.company_name')
    logo_path = str(base_config.app_logo_path)
    pdf_generator = PDFReportGenerator(company_name=company_name, logo_path=logo_path, title='存储使用明细报告',
                                       app='DiskPulse')
    pdf_generator.create_cover_page()
    resource_quota_col_width_ratios = [0.24, 0.09, 0.09, 0.09, 0.09, 0.09, 0.11, 0.1, 0.1]
    pdf_generator.add_table([df_storage_usage.columns.tolist()] + df_storage_usage.values.tolist(), '存储使用明细',
                            hint='配额和使用额度单位：GB',
                            col_width_ratios=resource_quota_col_width_ratios)
    output_pdf = pdf_generator.generate_pdf()
    output_pdf.seek(0)
    return output_pdf
