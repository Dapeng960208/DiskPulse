# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any, List

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from crud.questDbCrud import get_real_time_data_by_id
from models import (
    Group,
    Project,
    StorageCluster,
    StorageUsage,
)
from schemas import projectsSchema
from services.project_access_service import ensure_project_owner_membership
from utils.common import convert_GB_to_TB
from utils.datetime_utils import utc_now
from utils.query import apply_use_ratio_range, filter_tree_by_use_ratio, get_sort_column, require_allowed


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
        storage_alert_rule=(
            project.storage_alert_rule.model_dump() if project.storage_alert_rule else None
        ),
        in_charge_user_id=project.in_charge_user_id,
    )
    db.add(project_db)
    db.flush()
    ensure_project_owner_membership(db, project_id=project_db.id)
    db.commit()
    db.refresh(project_db)
    return project_db


def update_project(db: Session, project_id: int, project: projectsSchema.ProjectUpdate):
    project_db = db.query(Project).filter(Project.id == project_id).first()
    if project_db:
        previous_owner_user_id = project_db.in_charge_user_id
        project_db.name = project.name
        project_db.descriptions = project.descriptions
        project_db.status = project.status
        project_db.is_common = project.is_common
        project_db.recipients = " ".join(map(str, project.recipient_ids)) if project.recipient_ids else None
        project_db.is_alert = project.is_alert
        project_db.storage_alert_rule = (
            project.storage_alert_rule.model_dump() if project.storage_alert_rule else None
        )
        project_db.in_charge_user_id = project.in_charge_user_id
        project_db.project_process_code = project.project_process_code
        project_db.updated_at = utc_now()
        db.flush()
        ensure_project_owner_membership(
            db,
            project_id=project_db.id,
            previous_owner_user_id=previous_owner_user_id,
        )
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
    accessible_project_ids: set[int] | None = None,
    use_ratio_min: float | None = None,
    use_ratio_max: float | None = None,
):
    query = db.query(Project)
    if nameLike and len(nameLike.strip()) > 0:
        query = query.filter(Project.name.like(f"%{nameLike}%"))
    if project_id:
        query = query.filter(Project.id == project_id)
    if status is not None and status in [1, 2]:
        query = query.filter(Project.status == status)
    if accessible_project_ids is not None:
        query = query.filter(Project.id.in_(accessible_project_ids))

    query = apply_use_ratio_range(query, Project, use_ratio_min, use_ratio_max)

    total = query.count()
    sort_column = get_sort_column(Project, prop)
    if sort_column is not None:
        query = query.order_by(desc(sort_column) if order and order.lower() == "descending" else asc(sort_column))
    else:
        query = query.order_by(Project.name.asc())

    projects_db = query.offset((page - 1) * size).limit(size).all()
    _attach_storage_cluster_overviews(db, projects_db)
    return projects_db, total


def _attach_storage_cluster_overviews(
    db: Session,
    projects: list[Project],
) -> None:
    overviews = {
        project.id: {
            "storage_cluster_types": set(),
            "storage_clusters": {},
        }
        for project in projects
    }
    if not overviews:
        return

    rows = (
        db.query(
            Group.project_id,
            StorageCluster.id,
            StorageCluster.name,
            StorageCluster.storage_type,
        )
        .join(StorageCluster, StorageCluster.id == Group.storage_cluster_id)
        .filter(Group.project_id.in_(overviews))
        .distinct()
        .all()
    )
    for project_id, cluster_id, cluster_name, storage_type in rows:
        overviews[project_id]["storage_cluster_types"].add(storage_type)
        overviews[project_id]["storage_clusters"][cluster_id] = {
            "id": cluster_id,
            "name": cluster_name,
            "storage_type": storage_type,
        }

    for project in projects:
        overview = overviews[project.id]
        overview["storage_cluster_types"] = sorted(
            overview["storage_cluster_types"]
        )
        overview["storage_clusters"] = sorted(
            overview["storage_clusters"].values(),
            key=lambda cluster: (cluster["name"], cluster["id"]),
        )
        for field, value in overview.items():
            setattr(project, field, value)


def get_common_project(db: Session):
    return db.query(Project).filter(Project.is_common.is_(True)).first()


def _attach_tree_units(nodes: list[dict], value_unit: str) -> list[dict]:
    for node in nodes:
        node["capacity_unit"] = "TB"
        node["value_unit"] = value_unit
        _attach_tree_units(node.get("children", []), value_unit)
    return nodes


def get_project_storage_summary(
    db: Session,
    use_ratio_min: float | None = None,
    use_ratio_max: float | None = None,
) -> List[List[Any]]:
    query = (
        db.query(Group.name, Group.used, Project.name)
        .join(Project, Project.id == Group.project_id)
        .filter(Project.name != "Common", Group.enable_monitoring.is_(True), Group.qtree_id.isnot(None))
    )
    all_groups = apply_use_ratio_range(query, Group, use_ratio_min, use_ratio_max).all()
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


def get_project_tree_summary(
    db: Session,
    use_ratio_min: float | None = None,
    use_ratio_max: float | None = None,
):
    project_dbs = db.query(Project).filter(Project.name != "Common").all()
    result = []
    for project_db in project_dbs:
        group_dbs = (
            db.query(Group)
            .filter(
                Group.project_id == project_db.id,
                Group.enable_monitoring.is_(True),
                Group.qtree_id.isnot(None),
            )
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
    return _attach_tree_units(
        filter_tree_by_use_ratio(result, use_ratio_min, use_ratio_max),
        "TB",
    )


def get_project_tree_summary_by_id(
    db: Session,
    project_id: int,
    value_type: str,
    use_ratio_min: float | None = None,
    use_ratio_max: float | None = None,
) -> List:
    value_type = require_allowed(value_type, {"limit", "used", "use_ratio", "soft_limit", "soft_use_ratio"}, "value_type")
    group_dbs = (
        db.query(Group)
        .filter(Group.project_id == project_id)
        .all()
    )
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
    return _attach_tree_units(
        filter_tree_by_use_ratio(groups, use_ratio_min, use_ratio_max),
        "%" if "ratio" in value_type else "TB",
    )


def get_project_groups_storage_usage(
    db: Session,
    use_ratio_min: float | None = None,
    use_ratio_max: float | None = None,
):
    result = {}
    project_dbs = db.query(Project).all()
    for project_db in project_dbs:
        query = (
            db.query(Group)
            .filter(
                Group.project_id == project_db.id,
                Group.enable_monitoring.is_(True),
                Group.qtree_id.isnot(None),
            )
        )
        group_dbs = apply_use_ratio_range(query, Group, use_ratio_min, use_ratio_max).all()
        if group_dbs:
            categories = [group_db.name for group_db in group_dbs]
            used = [convert_GB_to_TB(group_db.used) if group_db.used else 0 for group_db in group_dbs]
            available = [
                convert_GB_to_TB(group_db.limit - group_db.used) if group_db.limit and group_db.used else 0
                for group_db in group_dbs
            ]
            result[project_db.name] = {"categories": categories, "data": [used, available], "series": ["used", "available"]}
    return result
