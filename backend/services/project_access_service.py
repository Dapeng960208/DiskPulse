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
