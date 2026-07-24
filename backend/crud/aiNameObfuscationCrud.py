# -*- coding: utf-8 -*-
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    Aggregate,
    Group,
    GroupTag,
    Host,
    Project,
    ProjectMembership,
    Qtree,
    StorageCluster,
    StorageUsage,
    User,
    Volume,
)


def _append(candidates: dict[str, set[str]], value: str | None, entity_kind: str) -> None:
    normalized = value.strip() if isinstance(value, str) else ""
    if normalized:
        candidates[normalized].add(entity_kind)


def list_authorized_name_candidates(
    db: Session,
    *,
    current_user: User,
    project_ids: set[int] | None,
) -> dict[str, set[str]]:
    """Return only managed resource names already visible to this chat user."""
    candidates: dict[str, set[str]] = defaultdict(set)
    if project_ids is None:
        projects = list(db.scalars(select(Project)))
        groups = list(db.scalars(select(Group)))
        clusters = list(db.scalars(select(StorageCluster)))
        aggregates = list(db.scalars(select(Aggregate)))
        volumes = list(db.scalars(select(Volume)))
        qtrees = list(db.scalars(select(Qtree)))
        tags = list(db.scalars(select(GroupTag)))
        hosts = list(db.scalars(select(Host)))
        users = list(db.scalars(select(User)))
    else:
        scoped_project_ids = set(project_ids)
        projects = list(
            db.scalars(select(Project).where(Project.id.in_(scoped_project_ids)))
        ) if scoped_project_ids else []
        groups = list(
            db.scalars(select(Group).where(Group.project_id.in_(scoped_project_ids)))
        ) if scoped_project_ids else []
        cluster_ids = {item.storage_cluster_id for item in groups if item.storage_cluster_id is not None}
        clusters = list(
            db.scalars(select(StorageCluster).where(StorageCluster.id.in_(cluster_ids)))
        ) if cluster_ids else []
        aggregates = list(
            db.scalars(select(Aggregate).where(Aggregate.storage_cluster_id.in_(cluster_ids)))
        ) if cluster_ids else []
        volumes = list(
            db.scalars(select(Volume).where(Volume.storage_cluster_id.in_(cluster_ids)))
        ) if cluster_ids else []
        qtrees = list(
            db.scalars(select(Qtree).where(Qtree.storage_cluster_id.in_(cluster_ids)))
        ) if cluster_ids else []
        tag_ids = {item.group_tag_id for item in groups if item.group_tag_id is not None}
        tags = list(db.scalars(select(GroupTag).where(GroupTag.id.in_(tag_ids)))) if tag_ids else []
        host_ids = {item.monitor_host_id for item in groups if item.monitor_host_id is not None}
        hosts = list(db.scalars(select(Host).where(Host.id.in_(host_ids)))) if host_ids else []
        group_ids = {item.id for item in groups}
        user_ids = {current_user.id}
        user_ids.update(item.in_charge_user_id for item in projects if item.in_charge_user_id is not None)
        user_ids.update(item.in_charge_user_id for item in groups if item.in_charge_user_id is not None)
        user_ids.update(
            db.scalars(
                select(ProjectMembership.user_id).where(
                    ProjectMembership.project_id.in_(scoped_project_ids)
                )
            )
        )
        if group_ids:
            user_ids.update(
                db.scalars(
                    select(StorageUsage.user_id).where(
                        StorageUsage.group_id.in_(group_ids),
                        StorageUsage.user_id.is_not(None),
                    )
                )
            )
        users = list(db.scalars(select(User).where(User.id.in_(user_ids))))

    for item in projects:
        _append(candidates, item.name, "项目")
    for item in users:
        _append(candidates, item.username, "用户")
        _append(candidates, item.rd_username, "用户")
    for item in clusters:
        _append(candidates, item.name, "集群")
    for item in groups:
        _append(candidates, item.name, "项目组")
    for item in tags:
        _append(candidates, item.name, "项目组标签")
    for item in aggregates:
        _append(candidates, item.name, "容量池")
    for item in volumes:
        _append(candidates, item.name, "存储空间")
    for item in qtrees:
        _append(candidates, item.name, "Qtree")
    for item in hosts:
        _append(candidates, item.name, "主机")
    return dict(candidates)
