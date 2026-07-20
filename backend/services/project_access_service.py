# -*- coding: utf-8 -*-
from fastapi import HTTPException, status

from models import Group, Project, ProjectMembership, StorageUsage
from utils.auth_service import is_super_admin


ROLE_RANK = {"reader": 1, "editor": 2, "project_admin": 3}


def _validate_role(role: str) -> None:
    if role not in ROLE_RANK:
        raise ValueError(f"unsupported project role: {role}")


def ensure_reader_membership(db, *, user_id: int, project_id: int) -> ProjectMembership:
    """Idempotently grant a collected directory owner read access to its project."""
    membership = (
        db.query(ProjectMembership)
        .filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id,
        )
        .one_or_none()
    )
    if membership is not None:
        return membership

    membership = ProjectMembership(project_id=project_id, user_id=user_id, role="reader")
    db.add(membership)
    db.flush()
    return membership


def ensure_reader_memberships(db, *, pairs: set[tuple[int, int]]) -> None:
    """Create missing reader memberships without changing existing roles."""
    if not pairs:
        return

    project_ids = {project_id for project_id, _user_id in pairs}
    user_ids = {user_id for _project_id, user_id in pairs}
    existing = {
        (membership.project_id, membership.user_id)
        for membership in db.query(ProjectMembership)
        .filter(
            ProjectMembership.project_id.in_(project_ids),
            ProjectMembership.user_id.in_(user_ids),
        )
        .all()
    }
    db.add_all(
        [
            ProjectMembership(project_id=project_id, user_id=user_id, role="reader")
            for project_id, user_id in pairs - existing
        ]
    )
    db.flush()


def ensure_group_directory_readers(db, *, group_id: int) -> None:
    """Grant every directory owner in a group read access to its current project."""
    group = db.get(Group, group_id)
    if group is None or group.project_id is None:
        return
    user_ids = {
        user_id
        for (user_id,) in db.query(StorageUsage.user_id)
        .filter(
            StorageUsage.group_id == group_id,
            StorageUsage.user_id.is_not(None),
        )
        .distinct()
        .all()
    }
    ensure_reader_memberships(
        db,
        pairs={(group.project_id, user_id) for user_id in user_ids},
    )


def ensure_project_owner_membership(db, *, project_id: int) -> ProjectMembership | None:
    """Ensure the configured project in-charge user is a project administrator."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project was not found")
    if project.in_charge_user_id is None:
        return None
    return set_project_member(
        db,
        project_id=project.id,
        user_id=project.in_charge_user_id,
        role="project_admin",
        actor_is_super_admin=True,
    )


def set_project_member(
    db,
    *,
    project_id: int,
    user_id: int,
    role: str,
    actor_is_super_admin: bool,
) -> ProjectMembership:
    _validate_role(role)
    if role == "project_admin" and not actor_is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super admin permission required")

    membership = (
        db.query(ProjectMembership)
        .filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id,
        )
        .one_or_none()
    )
    if membership is None:
        membership = ProjectMembership(project_id=project_id, user_id=user_id, role=role)
        db.add(membership)
    else:
        membership.role = role
    db.flush()
    return membership


def require_project_permission(db, current_user, project_id: int, minimum_role: str) -> None:
    _validate_role(minimum_role)
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    if is_super_admin(current_user):
        # Verify project exists after confirming super admin authorization
        if db.get(Project, project_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project was not found")
        return

    membership = (
        db.query(ProjectMembership)
        .filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == current_user.id,
        )
        .one_or_none()
    )
    if membership is None or ROLE_RANK[membership.role] < ROLE_RANK[minimum_role]:
        # Return 403 for both non-existent and unauthorized projects to prevent enumeration
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="project permission required")


def require_group_permission(db, current_user, group_id: int, minimum_role: str = "reader") -> Group:
    """Return a group only after enforcing access through its owning project."""
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="group was not found")
    require_project_permission(db, current_user, group.project_id, minimum_role)
    return group


def require_storage_usage_permission(
    db,
    current_user,
    storage_usage_id: int,
    minimum_role: str = "reader",
) -> StorageUsage:
    """Enforce the StorageUsage -> Group -> Project authorization path.

    A directory without a valid project group is intentionally unscoped and is
    therefore visible only to a super administrator.
    """
    storage_usage = db.get(StorageUsage, storage_usage_id)
    if storage_usage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="StorageUsage not found")
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    group = db.get(Group, storage_usage.group_id) if storage_usage.group_id is not None else None
    if group is None:
        if not is_super_admin(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="project permission required")
        return storage_usage
    require_project_permission(db, current_user, group.project_id, minimum_role)
    return storage_usage


def accessible_project_ids(db, current_user) -> set[int] | None:
    """Return all project scopes visible to a user, or None for a super admin."""
    if current_user is None:
        return set()
    if is_super_admin(current_user):
        return None
    return {
        project_id
        for (project_id,) in db.query(ProjectMembership.project_id)
        .filter(ProjectMembership.user_id == current_user.id)
        .all()
    }


def project_capabilities(db, current_user, project_id: int) -> dict[str, bool]:
    """Return only UI hints; the route and service authorization stay authoritative."""
    if current_user is None:
        return {
            "manage_members": False,
            "view_audit_events": False,
            "manage_project_admins": False,
        }
    if is_super_admin(current_user):
        return {
            "manage_members": True,
            "view_audit_events": True,
            "manage_project_admins": True,
        }
    membership = (
        db.query(ProjectMembership)
        .filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == current_user.id,
        )
        .one_or_none()
    )
    is_project_admin = membership is not None and membership.role == "project_admin"
    return {
        "manage_members": is_project_admin,
        "view_audit_events": is_project_admin,
        "manage_project_admins": False,
    }


def incident_capabilities(db, current_user, project_id: int | None) -> dict[str, bool]:
    """UI hints for derived Incident mutations; services still enforce RBAC."""
    if current_user is None:
        return {"edit": False, "create_maintenance_window": False}
    if is_super_admin(current_user):
        return {"edit": True, "create_maintenance_window": True}
    if project_id is None:
        return {"edit": False, "create_maintenance_window": False}
    membership = (
        db.query(ProjectMembership)
        .filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == current_user.id,
        )
        .one_or_none()
    )
    rank = ROLE_RANK[membership.role] if membership is not None else 0
    return {
        "edit": rank >= ROLE_RANK["editor"],
        "create_maintenance_window": rank >= ROLE_RANK["project_admin"],
    }


def group_capabilities(current_user, group: Group | None) -> dict[str, bool]:
    """Expose the same quota affordance enforced by quotaService."""
    return {
        "adjust_quota": bool(
            group is not None
            and current_user is not None
            and (
                is_super_admin(current_user)
                or group.in_charge_user_id == current_user.id
            )
        )
    }


def storage_usage_capabilities(current_user, storage_usage: StorageUsage) -> dict[str, bool]:
    return group_capabilities(current_user, storage_usage.group)
