# -*- coding: utf-8 -*-
from models import Group, LargeFiles
from sqlalchemy import or_, desc, asc
from sqlalchemy.orm import Session
from schemas import largeFileSchema
from io import BytesIO
import pandas as pd
from utils.query import get_sort_column
from utils.datetime_utils import format_for_user_time_zone


def get_large_files(db: Session, page: int | None = None, size: int | None = None, nameLike: str | None = None,
                    prop: str | None = None,
                    order: str | None = None, user_id: int | None = None, group_id: int | None = None,
                    accessible_project_ids: set[int] | None = None):
    query = db.query(LargeFiles)
    conditions = []
    if nameLike and len(nameLike.strip()) > 0:
        conditions.append(or_(LargeFiles.linux_path.like(f"%{nameLike}%"), LargeFiles.file_type.like(f"%{nameLike}%")))
    if user_id:
        conditions.append(LargeFiles.user_id == user_id)
    if group_id:
        conditions.append(LargeFiles.group_id == group_id)
    if accessible_project_ids is not None:
        query = query.join(Group, Group.id == LargeFiles.group_id)
        conditions.append(Group.project_id.in_(accessible_project_ids))
    query = query.filter(*conditions)
    total = query.count()
    sort_column = get_sort_column(LargeFiles, prop)
    if sort_column is not None:
        if order and order.lower() == 'descending':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(LargeFiles.size.desc())
    if page and size:
        query = query.offset((page - 1) * size).limit(size)
    large_files = query.all()
    return large_files, total


def export_large_files(db: Session, nameLike: str | None = None, user_id: int | None = None,
                       group_id: int | None = None,
                       accessible_project_ids: set[int] | None = None,
                       time_zone: str | None = None):
    large_files_dbs, _ = get_large_files(db=db, nameLike=nameLike, user_id=user_id,
                                         group_id=group_id,
                                         accessible_project_ids=accessible_project_ids)

    # 手动构建每条记录的字典，显式提取嵌套字段
    records = []
    for large_files_db in large_files_dbs:
        # 使用 model_validate 获取 Pydantic 模型实例（可选，也可直接从 ORM 对象取值）
        item = largeFileSchema.LargeFileList.model_validate(large_files_db)

        record = {
            "linux_path": item.linux_path,
            "size": item.size,
            "file_type": item.file_type,
            "updated_at": format_for_user_time_zone(item.updated_at, time_zone),
            "rd_username": item.user.rd_username if item.user else None,
            "group_name": item.group.name if item.group else None,
        }
        records.append(record)

    df_large_files = pd.DataFrame(records)

    # 设置中文列名
    large_files_column_headers = {
        'linux_path': '路径',
        'size': "文件大小",
        'file_type': "文件类型",
        'updated_at': "修改时间",
        'rd_username': "用户名",
        'group_name': "组名"
    }
    df_large_files.rename(columns=large_files_column_headers, inplace=True)

    # 导出到 Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_large_files.to_excel(writer, sheet_name='大文件', index=False)
    output.seek(0)
    return output
