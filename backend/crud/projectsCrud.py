# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any, List

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from crud.questDbCrud import get_real_time_data_by_id
from models import (
    Group,
    Project,
    ProjectStorageEnvironment,
    StorageCluster,
    StorageUsage,
)
from schemas import projectsSchema
from utils.common import convert_GB_to_TB
from utils.query import get_sort_column, require_allowed


def get_project_by_name(db: Session, name: str):
    return db.query(Project).filter_by(name=name).first()


def get_project_by_id(db: Session, id: int):
    return db.query(Project).filter_by(id=id).first()


def get_project_storage_usages_real_time_data_by_id(
    db: Session,
    project_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    indicator: str = "used",
):
    return get_real_time_data_by_id(
        db=db,
        attribute_id=project_id,
        start_time=start_time,
        end_time=end_time,
        indicator=indicator,
        table_prefix="project",
    )


def create_project(db: Session, project: projectsSchema.ProjectUpdate):
    project_db = Project(
        name=project.name,
        descriptions=project.descriptions,
        status=project.status,
        is_common=project.is_common,
        project_process_code=project.project_process_code,
        recipients=" ".join(map(str, project.recipient_ids)) if project.recipient_ids else None,
        is_alert=project.is_alert,
        in_charge_user_id=project.in_charge_user_id,
        pt_user_id=project.pt_user_id,
    )
    db.add(project_db)
    db.commit()
    db.refresh(project_db)
    return project_db


def update_project(db: Session, project_id: int, project: projectsSchema.ProjectUpdate):
    project_db = db.query(Project).filter(Project.id == project_id).first()
    if project_db:
        project_db.name = project.name
        project_db.descriptions = project.descriptions
        project_db.status = project.status
        project_db.is_common = project.is_common
        project_db.recipients = " ".join(map(str, project.recipient_ids)) if project.recipient_ids else None
        project_db.is_alert = project.is_alert
        project_db.in_charge_user_id = project.in_charge_user_id
        project_db.pt_user_id = project.pt_user_id
        project_db.project_process_code = project.project_process_code
        project_db.updated_at = datetime.now()
        db.commit()
        db.refresh(project_db)
    return project_db


def get_projects(
    db: Session,
    page: int = 1,
    size: int = 20,
    nameLike: str | None = None,
    project_id: int | None = None,
    prop: str | None = None,
    order: str | None = None,
    status: int | None = None,
):
    query = db.query(Project)
    if nameLike and len(nameLike.strip()) > 0:
        query = query.filter(Project.name.like(f"%{nameLike}%"))
    if project_id:
        query = query.filter(Project.id == project_id)
    if status is not None and status in [1, 2]:
        query = query.filter(Project.status == status)

    total = query.count()
    sort_column = get_sort_column(Project, prop)
    if sort_column is not None:
        query = query.order_by(desc(sort_column) if order and order.lower() == "descending" else asc(sort_column))
    else:
        query = query.order_by(Project.name.asc())

    projects_db = query.offset((page - 1) * size).limit(size).all()
    _attach_storage_environment_overviews(db, projects_db)
    return projects_db, total


def _attach_storage_environment_overviews(
    db: Session,
    projects: list[Project],
) -> None:
    overviews = {
        project.id: {
            "storage_environment_count": 0,
            "active_storage_environment_count": 0,
            "storage_cluster_types": set(),
            "storage_environment_status_counts": {
                "pending": 0,
                "success": 0,
                "failed": 0,
                "inactive": 0,
            },
        }
        for project in projects
    }
    if not overviews:
        return

    rows = (
        db.query(
            ProjectStorageEnvironment.project_id,
            ProjectStorageEnvironment.is_active,
            ProjectStorageEnvironment.collection_status,
            StorageCluster.storage_type,
            func.count(ProjectStorageEnvironment.id),
        )
        .join(
            StorageCluster,
            StorageCluster.id == ProjectStorageEnvironment.storage_cluster_id,
        )
        .filter(ProjectStorageEnvironment.project_id.in_(overviews))
        .group_by(
            ProjectStorageEnvironment.project_id,
            ProjectStorageEnvironment.is_active,
            ProjectStorageEnvironment.collection_status,
            StorageCluster.storage_type,
        )
        .all()
    )
    for project_id, is_active, collection_status, storage_type, count in rows:
        overview = overviews[project_id]
        overview["storage_environment_count"] += count
        overview["storage_cluster_types"].add(storage_type)
        if is_active:
            overview["active_storage_environment_count"] += count
            overview["storage_environment_status_counts"][collection_status] += count
        else:
            overview["storage_environment_status_counts"]["inactive"] += count

    for project in projects:
        overview = overviews[project.id]
        overview["storage_cluster_types"] = sorted(
            overview["storage_cluster_types"]
        )
        for field, value in overview.items():
            setattr(project, field, value)


def get_common_project(db: Session):
    return db.query(Project).filter(Project.is_common.is_(True)).first()


def get_project_storage_summary(db: Session) -> List[List[Any]]:
    all_groups = (
        db.query(Group.name, Group.used, Project.name)
        .join(Project, Project.id == Group.project_id)
        .filter(Project.name != "Common", Group.enable_monitoring.is_(True), Group.qtree_id.isnot(None))
        .all()
    )
    project_names = sorted(set(group[2] for group in all_groups))
    group_names = sorted(set(group[0] for group in all_groups))
    summary = [["project"] + project_names]
    summary += [[group_name] + [0] * len(project_names) for group_name in group_names]
    project_index = {name: idx for idx, name in enumerate(project_names, start=1)}
    group_index = {name: idx for idx, name in enumerate(group_names, start=1)}

    for group_name, used, project_name in all_groups:
        row_idx = group_index[group_name]
        col_idx = project_index[project_name]
        summary[row_idx][col_idx] = round((used or 0) / 1024, 2)
    return summary


def get_project_tree_summary(db: Session):
    project_dbs = db.query(Project).filter(Project.name != "Common").all()
    result = []
    for project_db in project_dbs:
        group_dbs = (
            db.query(Group)
            .filter(Group.project_id == project_db.id, Group.enable_monitoring.is_(True), Group.qtree_id.isnot(None))
            .all()
        )
        groups = []
        for group_db in group_dbs:
            storage_dbs = db.query(StorageUsage).filter(StorageUsage.group_id == group_db.id).all()
            storages = [
                {
                    "value": convert_GB_to_TB(storage_db.limit),
                    "soft_limit": convert_GB_to_TB(storage_db.soft_limit),
                    "used": convert_GB_to_TB(storage_db.used),
                    "name": storage_db.user.rd_username if storage_db.user else "",
                    "path": storage_db.linux_path,
                    "used_ratio": storage_db.use_ratio,
                    "soft_used_ratio": storage_db.soft_use_ratio,
                }
                for storage_db in storage_dbs
            ]
            groups.append(
                {
                    "value": convert_GB_to_TB(group_db.limit),
                    "soft_limit": convert_GB_to_TB(group_db.soft_limit),
                    "used": convert_GB_to_TB(group_db.used),
                    "name": group_db.name,
                    "path": group_db.linux_path,
                    "used_ratio": group_db.use_ratio,
                    "soft_used_ratio": group_db.soft_use_ratio,
                    "children": storages,
                }
            )
        result.append(
            {
                "value": convert_GB_to_TB(project_db.limit),
                "soft_limit": convert_GB_to_TB(project_db.soft_limit),
                "used": convert_GB_to_TB(project_db.used),
                "name": project_db.name,
                "path": project_db.name,
                "used_ratio": project_db.use_ratio,
                "soft_used_ratio": project_db.soft_use_ratio,
                "children": groups,
            }
        )
    return result


def get_project_tree_summary_by_id(db: Session, project_id: int, value_type: str) -> List:
    value_type = require_allowed(value_type, {"limit", "used", "use_ratio", "soft_limit", "soft_use_ratio"}, "value_type")
    group_dbs = db.query(Group).filter(Group.project_id == project_id).all()
    groups = []
    for group_db in group_dbs:
        storage_dbs = db.query(StorageUsage).filter(StorageUsage.group_id == group_db.id).all()
        storages = [
            {
                "limit": convert_GB_to_TB(storage_db.limit),
                "soft_limit": convert_GB_to_TB(storage_db.soft_limit),
                "used": convert_GB_to_TB(storage_db.used),
                "value": convert_GB_to_TB(getattr(storage_db, value_type, 0)),
                "name": storage_db.user.rd_username if storage_db.user else "",
                "path": storage_db.linux_path,
                "used_ratio": storage_db.use_ratio,
                "soft_used_ratio": storage_db.soft_use_ratio,
            }
            for storage_db in storage_dbs
        ]
        groups.append(
            {
                "limit": convert_GB_to_TB(group_db.limit),
                "soft_limit": convert_GB_to_TB(group_db.soft_limit),
                "used": convert_GB_to_TB(group_db.used),
                "value": convert_GB_to_TB(getattr(group_db, value_type, 0)),
                "name": group_db.name,
                "path": group_db.linux_path,
                "used_ratio": group_db.use_ratio,
                "soft_used_ratio": group_db.soft_use_ratio,
                "children": storages,
            }
        )
    return groups


def get_project_groups_storage_usage(db: Session):
    result = {}
    project_dbs = db.query(Project).all()
    for project_db in project_dbs:
        group_dbs = (
            db.query(Group)
            .filter(Group.project_id == project_db.id, Group.enable_monitoring.is_(True), Group.qtree_id.isnot(None))
            .all()
        )
        if group_dbs:
            categories = [group_db.name for group_db in group_dbs]
            used = [convert_GB_to_TB(group_db.used) if group_db.used else 0 for group_db in group_dbs]
            available = [
                convert_GB_to_TB(group_db.limit - group_db.used) if group_db.limit and group_db.used else 0
                for group_db in group_dbs
            ]
            result[project_db.name] = {"categories": categories, "data": [used, available], "series": ["used", "available"]}
    return result
