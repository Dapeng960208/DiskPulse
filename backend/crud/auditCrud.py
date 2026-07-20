# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime
from typing import Iterable

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models import AuditEvent, Group, Project, Qtree, StorageAlerts, StorageCluster, StorageUsage, User, Volume


_RESOURCE_TYPE_ALIASES = {
    "storagecluster": "storage_cluster",
    "storageusage": "storage_usage",
    "storagealert": "storage_alert",
    "projectmembership": "project_membership",
}
_RELATION_PATHS = {
    "group": "项目组 → 项目",
    "project": "项目",
    "qtree": "Qtree → 项目组 → 项目",
    "storage_alert": "存储告警 → 存储集群 → 项目组 → 项目",
    "storage_cluster": "存储集群 → 项目组 → 项目",
    "storage_usage": "用户目录 → 项目组 → 项目",
    "volume": "存储空间 → 项目组 → 项目",
}


def _normalise_resource_type(resource_type: str) -> str:
    value = resource_type.replace("-", "_").casefold()
    return _RESOURCE_TYPE_ALIASES.get(value.replace("_", ""), value)


def _display_name(rd_username: str | None, username: str | None, fallback: str) -> str:
    return rd_username or username or fallback


def _project_reference(project_id: int, name: str) -> dict:
    return {"id": project_id, "name": name}


def _resource_reference(resource_type: str, resource_id: int, name: str) -> dict:
    return {"type": resource_type, "id": str(resource_id), "name": name}


def get_audit_event(db: Session, event_id: str) -> AuditEvent | None:
    return db.get(AuditEvent, event_id)


def get_audit_event_associations(
    db: Session,
    events: Iterable[AuditEvent],
    *,
    allowed_project_ids: set[int] | None = None,
) -> dict[str, dict]:
    """Batch-resolve display-safe associations for the current page of audit events."""
    rows = list(events)
    associations = {
        event.id: {
            "actor": None,
            "project": None,
            "resource": None,
            "related_projects": [],
            "relation_path": None,
        }
        for event in rows
    }
    resource_keys: dict[str, tuple[str, int]] = {}
    resource_ids: dict[str, set[int]] = defaultdict(set)
    direct_project_ids = {event.project_id for event in rows if event.project_id is not None}
    actor_ids = {event.actor_user_id for event in rows if event.actor_user_id is not None}

    for event in rows:
        if event.resource_id is None:
            continue
        resource_type = _normalise_resource_type(event.resource_type)
        resource_key = (resource_type, event.resource_id)
        resource_keys[event.id] = resource_key
        resource_ids[resource_type].add(event.resource_id)

    cluster_ids = resource_ids["storage_cluster"]
    cluster_rows = (
        db.query(StorageCluster.id, StorageCluster.name)
        .filter(StorageCluster.id.in_(cluster_ids))
        .all()
        if cluster_ids
        else []
    )
    resource_references = {
        ("storage_cluster", row.id): _resource_reference("storage_cluster", row.id, row.name)
        for row in cluster_rows
    }
    resource_projects: dict[tuple[str, int], set[int]] = defaultdict(set)
    relation_paths: dict[tuple[str, int], str] = {}
    if cluster_ids:
        for cluster_id, project_id in (
            db.query(Group.storage_cluster_id, Group.project_id)
            .filter(Group.storage_cluster_id.in_(cluster_ids))
            .distinct()
            .all()
        ):
            resource_projects[("storage_cluster", cluster_id)].add(project_id)
            relation_paths[("storage_cluster", cluster_id)] = _RELATION_PATHS["storage_cluster"]

    volume_ids = resource_ids["volume"]
    volume_rows = (
        db.query(Volume.id, Volume.name)
        .filter(Volume.id.in_(volume_ids))
        .all()
        if volume_ids
        else []
    )
    resource_references.update(
        {
            ("volume", row.id): _resource_reference("volume", row.id, row.name or f"存储空间 #{row.id}")
            for row in volume_rows
        }
    )
    if volume_ids:
        for volume_id, project_id in (
            db.query(Group.volume_id, Group.project_id)
            .filter(Group.volume_id.in_(volume_ids))
            .distinct()
            .all()
        ):
            resource_projects[("volume", volume_id)].add(project_id)
            relation_paths[("volume", volume_id)] = _RELATION_PATHS["volume"]

    qtree_ids = resource_ids["qtree"]
    qtree_rows = (
        db.query(Qtree.id, Qtree.name)
        .filter(Qtree.id.in_(qtree_ids))
        .all()
        if qtree_ids
        else []
    )
    resource_references.update(
        {
            ("qtree", row.id): _resource_reference("qtree", row.id, row.name or f"Qtree #{row.id}")
            for row in qtree_rows
        }
    )
    if qtree_ids:
        for qtree_id, project_id in (
            db.query(Group.qtree_id, Group.project_id)
            .filter(Group.qtree_id.in_(qtree_ids))
            .distinct()
            .all()
        ):
            resource_projects[("qtree", qtree_id)].add(project_id)
            relation_paths[("qtree", qtree_id)] = _RELATION_PATHS["qtree"]

    alert_ids = resource_ids["storage_alert"]
    alert_rows = (
        db.query(
            StorageAlerts.id,
            StorageAlerts.alert_type,
            StorageAlerts.storage_cluster_id,
            StorageAlerts.related_id,
            StorageAlerts.related_type,
        )
        .filter(StorageAlerts.id.in_(alert_ids))
        .all()
        if alert_ids
        else []
    )
    alert_group_ids: set[int] = set()
    alert_usage_ids: set[int] = set()
    alert_cluster_ids: dict[int, int | None] = {}
    for row in alert_rows:
        label = f"{row.alert_type or '存储告警'} #{row.id}"
        resource_references[("storage_alert", row.id)] = _resource_reference("storage_alert", row.id, label)
        related_type = _normalise_resource_type(row.related_type or "")
        if related_type == "group" and row.related_id is not None:
            alert_group_ids.add(row.related_id)
            relation_paths[("storage_alert", row.id)] = "存储告警 → 项目组 → 项目"
        elif related_type == "storage_usage" and row.related_id is not None:
            alert_usage_ids.add(row.related_id)
            relation_paths[("storage_alert", row.id)] = "存储告警 → 用户目录 → 项目组 → 项目"
        else:
            alert_cluster_ids[row.id] = row.storage_cluster_id
            relation_paths[("storage_alert", row.id)] = _RELATION_PATHS["storage_alert"]

    usage_ids = resource_ids["storage_usage"] | alert_usage_ids
    usage_rows = (
        db.query(StorageUsage.id, StorageUsage.user_id, StorageUsage.group_id)
        .filter(StorageUsage.id.in_(usage_ids))
        .all()
        if usage_ids
        else []
    )
    usage_data = {row.id: row for row in usage_rows}
    usage_group_ids = {row.group_id for row in usage_rows if row.group_id is not None}
    usage_user_ids = {row.user_id for row in usage_rows if row.user_id is not None}

    group_ids = resource_ids["group"] | alert_group_ids | usage_group_ids
    group_rows = (
        db.query(Group.id, Group.name, Group.project_id)
        .filter(Group.id.in_(group_ids))
        .all()
        if group_ids
        else []
    )
    group_data = {row.id: row for row in group_rows}
    for row in group_rows:
        resource_references[("group", row.id)] = _resource_reference("group", row.id, row.name or f"项目组 #{row.id}")
        resource_projects[("group", row.id)].add(row.project_id)
        relation_paths[("group", row.id)] = _RELATION_PATHS["group"]

    for usage_id, row in usage_data.items():
        group = group_data.get(row.group_id)
        if group is not None:
            resource_projects[("storage_usage", usage_id)].add(group.project_id)
            relation_paths[("storage_usage", usage_id)] = _RELATION_PATHS["storage_usage"]

    fallback_alert_cluster_ids = {cluster_id for cluster_id in alert_cluster_ids.values() if cluster_id is not None}
    cluster_project_rows = (
        db.query(Group.storage_cluster_id, Group.project_id)
        .filter(Group.storage_cluster_id.in_(fallback_alert_cluster_ids))
        .distinct()
        .all()
        if fallback_alert_cluster_ids
        else []
    )
    cluster_projects: dict[int, set[int]] = defaultdict(set)
    for cluster_id, project_id in cluster_project_rows:
        cluster_projects[cluster_id].add(project_id)

    for alert in alert_rows:
        alert_key = ("storage_alert", alert.id)
        related_type = _normalise_resource_type(alert.related_type or "")
        if related_type == "group":
            group = group_data.get(alert.related_id)
            if group is not None:
                resource_projects[alert_key].add(group.project_id)
        elif related_type == "storage_usage":
            usage = usage_data.get(alert.related_id)
            group = group_data.get(usage.group_id) if usage is not None else None
            if group is not None:
                resource_projects[alert_key].add(group.project_id)
        else:
            cluster_id = alert_cluster_ids.get(alert.id)
            if cluster_id is not None:
                for project_id in cluster_projects[cluster_id]:
                    resource_projects[alert_key].add(project_id)

    user_resource_ids = resource_ids["user"] | resource_ids["project_membership"]
    user_ids = actor_ids | usage_user_ids | user_resource_ids
    user_rows = (
        db.query(User.id, User.rd_username, User.username)
        .filter(User.id.in_(user_ids))
        .all()
        if user_ids
        else []
    )
    user_references = {
        row.id: {"id": row.id, "display_name": _display_name(row.rd_username, row.username, f"用户 #{row.id}")}
        for row in user_rows
    }
    for event in rows:
        if event.actor_user_id is not None:
            associations[event.id]["actor"] = user_references.get(event.actor_user_id)
    for usage_id, row in usage_data.items():
        user = user_references.get(row.user_id)
        name = user["display_name"] if user is not None else f"用户目录 #{usage_id}"
        resource_references[("storage_usage", usage_id)] = _resource_reference("storage_usage", usage_id, name)
    for resource_type in ("user", "project_membership"):
        for user_id in resource_ids[resource_type]:
            user = user_references.get(user_id)
            if user is not None:
                resource_references[(resource_type, user_id)] = _resource_reference(
                    resource_type,
                    user_id,
                    user["display_name"],
                )

    project_resource_ids = resource_ids["project"]
    for project_id in project_resource_ids:
        resource_projects[("project", project_id)].add(project_id)
        relation_paths[("project", project_id)] = _RELATION_PATHS["project"]

    project_ids = set(direct_project_ids) | set(project_resource_ids)
    for related_ids in resource_projects.values():
        project_ids.update(related_ids)
    project_rows = (
        db.query(Project.id, Project.name)
        .filter(Project.id.in_(project_ids))
        .all()
        if project_ids
        else []
    )
    project_references = {row.id: _project_reference(row.id, row.name) for row in project_rows}
    for project_id in project_resource_ids:
        project = project_references.get(project_id)
        if project is not None:
            resource_references[("project", project_id)] = _resource_reference("project", project_id, project["name"])

    for event in rows:
        association = associations[event.id]
        resource_key = resource_keys.get(event.id)
        if resource_key is not None:
            association["resource"] = resource_references.get(resource_key)
        if event.project_id is not None:
            association["project"] = project_references.get(event.project_id)

        related_project_ids = set(resource_projects.get(resource_key, set()))
        if allowed_project_ids is not None:
            related_project_ids &= allowed_project_ids
        if event.project_id is not None:
            related_project_ids.discard(event.project_id)
        association["related_projects"] = [
            project_references[project_id]
            for project_id in sorted(related_project_ids)
            if project_id in project_references
        ]
        if association["related_projects"]:
            association["relation_path"] = relation_paths.get(resource_key)

    return associations


def list_audit_events(
    db: Session,
    *,
    page: int,
    size: int,
    project_id: int | None = None,
    actor_user_id: int | None = None,
    action: str | None = None,
    outcome: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> tuple[list[AuditEvent], int]:
    query = db.query(AuditEvent)
    if project_id is not None:
        query = query.filter(AuditEvent.project_id == project_id)
    if actor_user_id is not None:
        query = query.filter(AuditEvent.actor_user_id == actor_user_id)
    if action:
        query = query.filter(AuditEvent.action == action)
    if outcome:
        query = query.filter(AuditEvent.outcome == outcome)
    if start_time is not None:
        query = query.filter(AuditEvent.occurred_at >= start_time)
    if end_time is not None:
        query = query.filter(AuditEvent.occurred_at <= end_time)

    total = query.count()
    rows = (
        query.order_by(desc(AuditEvent.occurred_at), desc(AuditEvent.id))
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return rows, total
