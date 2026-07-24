# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session
from models import Group, StorageUsage, User
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
from utils.query import apply_use_ratio_range, get_sort_column
from utils.storageTarget import resolve_group_storage_target
from utils.datetime_utils import format_for_user_time_zone, utc_now


def get_storage_usage_by_id(db: Session, storage_usage_id: int):
    return db.query(StorageUsage).filter(StorageUsage.id == storage_usage_id).first()


def get_storage_usages(db: Session, page: int | None = None, size: int | None = None, nameLike: str | None = None,
                       prop: str | None = None,
                       order: str | None = None, user_id: int | None = None,
                       rd_username: str | None = None, group_id: int | None = None,
                        storage_cluster_id: int | None = None, project_id: int | None = None,
                        group_tag_id: int | None = None,
                        accessible_project_ids: set[int] | None = None,
                        use_ratio_min: float | None = None, use_ratio_max: float | None = None):
    query = db.query(StorageUsage)
    conditions = []
    if nameLike and len(nameLike.strip()) > 0:
        conditions.append(StorageUsage.linux_path.like(f"%{nameLike}%"))
    if user_id:
        conditions.append(StorageUsage.user_id == user_id)
    if rd_username is not None:
        conditions.append(StorageUsage.user.has(User.rd_username == rd_username))
    if group_id:
        conditions.append(StorageUsage.group_id == group_id)
    if (
        project_id is not None
        or group_tag_id is not None
        or storage_cluster_id is not None
        or accessible_project_ids is not None
    ):
        query = query.join(Group, Group.id == StorageUsage.group_id)
    if project_id is not None:
        conditions.append(Group.project_id == project_id)
    if accessible_project_ids is not None:
        conditions.append(Group.project_id.in_(accessible_project_ids))
    if group_tag_id is not None:
        conditions.append(Group.group_tag_id == group_tag_id)
    if storage_cluster_id is not None:
        conditions.append(Group.storage_cluster_id == storage_cluster_id)
    query = query.filter(*conditions)
    query = apply_use_ratio_range(query, StorageUsage, use_ratio_min, use_ratio_max)
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


def create_storage_usage(
    db: Session,
    storage_usage: storageUsageSchema.StorageUsageCreate,
    linux_path: str,
    group: Group | None = None,
):
    group = group or db.query(Group).filter(Group.id == storage_usage.group_id).first()
    existing_assignment = db.query(StorageUsage).filter(
        StorageUsage.user_id == storage_usage.user_id,
        StorageUsage.group_id == storage_usage.group_id,
    ).first()
    if existing_assignment:
        existing_assignment.storage_cluster_id = (
            group.storage_cluster_id if group is not None else None
        )
        db.commit()
        db.refresh(existing_assignment)
        return False, existing_assignment
    exit_storage_usage = db.query(StorageUsage).filter(StorageUsage.linux_path == linux_path).first()
    if exit_storage_usage:
        return True, exit_storage_usage
    db_storage_usage = StorageUsage(
        user_id=storage_usage.user_id,
        group_id=storage_usage.group_id,
        storage_cluster_id=(
            group.storage_cluster_id if group is not None else None
        ),
        linux_path=linux_path,
        updated_at=utc_now(),
    )
    db.add(db_storage_usage)
    db.commit()
    db.refresh(db_storage_usage)
    return False, db_storage_usage


def update_storage_usage(db: Session, storage_usage_id: int, storage_usage: storageUsageSchema.StorageUsageUpdate):
    db_storage_usage = db.query(StorageUsage).filter(StorageUsage.id == storage_usage_id).first()
    if db_storage_usage:
        data = storage_usage.model_dump(exclude_unset=True)
        group = db.query(Group).filter(Group.id == data["group_id"]).first()
        if group is not None:
            data["storage_cluster_id"] = group.storage_cluster_id
        for key, value in data.items():
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


def serialize_storage_usage(
    storage_usage: StorageUsage,
    *,
    capabilities: dict[str, bool] | None = None,
) -> dict:
    result = {
        column.name: getattr(storage_usage, column.name)
        for column in StorageUsage.__table__.columns
    }
    result["user"] = storage_usage.user
    result["group"] = storage_usage.group
    result["capabilities"] = capabilities or {}
    if storage_usage.group is None:
        result.update(project=None, group_tag=None, storage_cluster=None, storage_target=None)
        return result

    resolved = resolve_group_storage_target(storage_usage.group)
    target = resolved["target"]
    cluster = resolved["storage_cluster"]
    project = storage_usage.group.project
    result["project"] = (
        {"id": project.id, "name": project.name} if project is not None else None
    )
    result["group_tag"] = storage_usage.group.group_tag
    result["storage_cluster"] = cluster
    result["storage_cluster_id"] = cluster.id if cluster is not None else None
    result["storage_target"] = (
        {
            "type": resolved["target_type"],
            "id": target.id,
            "name": target.name,
        }
        if target is not None
        else None
    )
    return result


def get_export_data(db: Session, nameLike: str | None = None, prop: str | None = None,
                    order: str | None = None, user_id: int | None = None, group_id: int | None = None,
                    storage_cluster_id: int | None = None, project_id: int | None = None,
                    group_tag_id: int | None = None,
                    accessible_project_ids: set[int] | None = None,
                    use_ratio_min: float | None = None, use_ratio_max: float | None = None,
                    time_zone: str | None = None):
    storage_usage_dbs, _ = get_storage_usages(db=db, nameLike=nameLike, prop=prop, order=order, user_id=user_id,
                                              group_id=group_id, storage_cluster_id=storage_cluster_id,
                                              project_id=project_id,
                                              group_tag_id=group_tag_id,
                                              accessible_project_ids=accessible_project_ids,
                                              use_ratio_min=use_ratio_min, use_ratio_max=use_ratio_max)
    rows = []
    for storage_usage in storage_usage_dbs:
        group = storage_usage.group
        if group is None:
            target_type = None
            target = None
            volume = None
            cluster = storage_usage.storage_cluster
            group_tag = None
            project = None
        else:
            resolved = resolve_group_storage_target(group)
            target_type = resolved["target_type"]
            target = resolved["target"]
            volume = resolved["volume"]
            cluster = resolved["storage_cluster"]
            group_tag = group.group_tag
            project = group.project
        rows.append({
            "项目": project.name if project is not None else "",
            "项目组标签": group_tag.name if group_tag is not None else "",
            "存储集群": cluster.name if cluster is not None else "",
            "存储类型": cluster.storage_type if cluster is not None else "",
            "项目组": group.name if group is not None else "",
            "Volume": volume.name if volume is not None else "",
            "Qtree": target.name if target_type == "qtree" else "",
            "路径": storage_usage.linux_path,
            "硬限额": storage_usage.limit,
            "软限额": storage_usage.soft_limit,
            "已使用": storage_usage.used,
            "硬使用率": storage_usage.use_ratio,
            "软使用率": storage_usage.soft_use_ratio,
            "文件数": storage_usage.file_used,
            "访问时间": (
                format_for_user_time_zone(storage_usage.access_time, time_zone)
                if storage_usage.access_time else ""
            ),
            "修改时间": (
                format_for_user_time_zone(storage_usage.modify_time, time_zone)
                if storage_usage.modify_time else ""
            ),
        })
    columns = [
        "项目", "项目组标签", "存储集群", "存储类型", "项目组", "Volume", "Qtree", "路径",
        "硬限额", "软限额", "已使用", "硬使用率", "软使用率", "文件数", "访问时间", "修改时间",
    ]
    return pd.DataFrame(rows, columns=columns)


def export_storage_usage_to_excel(db: Session, nameLike: str | None = None, prop: str | None = None,
                                  order: str | None = None, user_id: int | None = None, group_id: int | None = None,
                                  storage_cluster_id: int | None = None, project_id: int | None = None,
                                  group_tag_id: int | None = None,
                                  accessible_project_ids: set[int] | None = None,
                                  use_ratio_min: float | None = None, use_ratio_max: float | None = None,
                                  time_zone: str | None = None):
    df_storage_usage = get_export_data(db, nameLike, prop, order, user_id, group_id, storage_cluster_id,
                                       project_id, group_tag_id, accessible_project_ids,
                                       use_ratio_min, use_ratio_max, time_zone)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_storage_usage.to_excel(writer, sheet_name='存储使用明细', index=False)
    output.seek(0)
    return output


def export_storage_usage_to_pdf(db: Session, nameLike: str | None = None, prop: str | None = None,
                                order: str | None = None, user_id: int | None = None, group_id: int | None = None,
                                storage_cluster_id: int | None = None, project_id: int | None = None,
                                group_tag_id: int | None = None,
                                accessible_project_ids: set[int] | None = None,
                                use_ratio_min: float | None = None, use_ratio_max: float | None = None,
                                time_zone: str | None = None):
    from appConfig import base_config
    df_storage_usage = get_export_data(db, nameLike, prop, order, user_id, group_id, storage_cluster_id,
                                       project_id, group_tag_id, accessible_project_ids,
                                       use_ratio_min, use_ratio_max, time_zone)
    company_name = base_config.get('application.company_name')
    logo_path = str(base_config.app_logo_path)
    pdf_generator = PDFReportGenerator(company_name=company_name, logo_path=logo_path, title='存储使用明细报告',
                                       app='DiskPulse', time_zone=time_zone)
    pdf_generator.create_cover_page()
    resource_quota_col_width_ratios = [1 / len(df_storage_usage.columns)] * len(df_storage_usage.columns)
    pdf_generator.add_table([df_storage_usage.columns.tolist()] + df_storage_usage.values.tolist(), '存储使用明细',
                            hint='配额和使用额度单位：GB',
                            col_width_ratios=resource_quota_col_width_ratios)
    output_pdf = pdf_generator.generate_pdf()
    output_pdf.seek(0)
    return output_pdf
