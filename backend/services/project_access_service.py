# -*- coding: utf-8 -*-
from fastapi import HTTPException, status

from models import Project, ProjectMembership
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
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project was not found")
    if is_super_admin(current_user):
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="project permission required")
