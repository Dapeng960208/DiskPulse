# -*- coding: utf-8 -*-
from fastapi import HTTPException, status

from models import Group, Project, ProjectMembership, StorageUsage, User
from services import project_access_service
from services.audit_service import AuditContext, append_audit_event
from utils.auth_service import is_super_admin


def _actor_is_super_admin(current_user: User) -> bool:
    return is_super_admin(current_user)


def _require_manage_members(db, *, project_id: int, current_user: User) -> bool:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project was not found")
    super_admin = _actor_is_super_admin(current_user)
    if not super_admin:
        project_access_service.require_project_permission(
            db,
            current_user,
            project_id,
            "project_admin",
        )
    return super_admin


def _require_target_user(db, user_id: int) -> None:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user was not found")


def _validate_assignable_role(*, role: str, actor_is_super_admin: bool) -> None:
    if role == "project_admin" and not actor_is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super admin permission required")


def _serialize(membership: ProjectMembership, user: User | None = None) -> dict:
    return {
        "id": membership.id,
        "project_id": membership.project_id,
        "user_id": membership.user_id,
        "role": membership.role,
        "created_by": membership.created_by,
        "updated_by": membership.updated_by,
        "created_at": membership.created_at,
        "updated_at": membership.updated_at,
        "user": user,
    }


def list_memberships(db, *, project_id: int, current_user: User) -> list[dict]:
    _require_manage_members(db, project_id=project_id, current_user=current_user)
    rows = (
        db.query(ProjectMembership, User)
        .join(User, User.id == ProjectMembership.user_id)
        .filter(ProjectMembership.project_id == project_id)
        .order_by(User.rd_username.asc(), User.id.asc())
        .all()
    )
    return [_serialize(membership, user) for membership, user in rows]


def create_membership(
    db,
    *,
    project_id: int,
    user_id: int,
    role: str,
    current_user: User,
    audit_context: AuditContext | None = None,
) -> dict:
    actor_is_super_admin = _require_manage_members(db, project_id=project_id, current_user=current_user)
    _validate_assignable_role(role=role, actor_is_super_admin=actor_is_super_admin)
    _require_target_user(db, user_id)
    if (
        db.query(ProjectMembership)
        .filter(ProjectMembership.project_id == project_id, ProjectMembership.user_id == user_id)
        .one_or_none()
        is not None
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="project member already exists")
    membership = ProjectMembership(
        project_id=project_id,
        user_id=user_id,
        role=role,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(membership)
    if audit_context is not None:
        append_audit_event(
            db,
            context=audit_context,
            phase="result",
            action="project.membership.create",
            resource_type="project_membership",
            resource_id=user_id,
            project_id=project_id,
            outcome="success",
            after_summary={"role": role},
        )
    db.commit()
    db.refresh(membership)
    return _serialize(membership, db.get(User, user_id))


def update_membership(
    db,
    *,
    project_id: int,
    user_id: int,
    role: str,
    current_user: User,
    audit_context: AuditContext | None = None,
) -> dict:
    actor_is_super_admin = _require_manage_members(db, project_id=project_id, current_user=current_user)
    _validate_assignable_role(role=role, actor_is_super_admin=actor_is_super_admin)
    membership = (
        db.query(ProjectMembership)
        .filter(ProjectMembership.project_id == project_id, ProjectMembership.user_id == user_id)
        .one_or_none()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project member was not found")
    previous_role = membership.role
    membership.role = role
    membership.updated_by = current_user.id
    if audit_context is not None:
        append_audit_event(
            db,
            context=audit_context,
            phase="result",
            action="project.membership.update",
            resource_type="project_membership",
            resource_id=user_id,
            project_id=project_id,
            outcome="success",
            before_summary={"role": previous_role},
            after_summary={"role": role},
        )
    db.commit()
    db.refresh(membership)
    return _serialize(membership, db.get(User, user_id))


def delete_membership(
    db,
    *,
    project_id: int,
    user_id: int,
    current_user: User,
    audit_context: AuditContext | None = None,
) -> None:
    actor_is_super_admin = _require_manage_members(db, project_id=project_id, current_user=current_user)
    membership = (
        db.query(ProjectMembership)
        .filter(ProjectMembership.project_id == project_id, ProjectMembership.user_id == user_id)
        .one_or_none()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project member was not found")
    _validate_assignable_role(role=membership.role, actor_is_super_admin=actor_is_super_admin)
    owns_project_directory = (
        db.query(StorageUsage.id)
        .join(Group, Group.id == StorageUsage.group_id)
        .filter(
            Group.project_id == project_id,
            StorageUsage.user_id == user_id,
        )
        .first()
        is not None
    )
    if owns_project_directory:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="directory owner project membership is required",
        )
    if audit_context is not None:
        append_audit_event(
            db,
            context=audit_context,
            phase="result",
            action="project.membership.delete",
            resource_type="project_membership",
            resource_id=user_id,
            project_id=project_id,
            outcome="success",
            before_summary={"role": membership.role},
        )
    db.delete(membership)
    db.commit()
