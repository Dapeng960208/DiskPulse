# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from dependencies import CurrentUserDep, get_db
from schemas import projectMembershipSchema
from services import project_membership_service


router = APIRouter(prefix="/projects", tags=["project-memberships"])
DBDep = Annotated[Session, Depends(get_db)]


@router.get("/{project_id}/members", response_model=list[projectMembershipSchema.ProjectMembershipOut])
def list_project_members(project_id: int, current_user: CurrentUserDep, db: DBDep):
    return project_membership_service.list_memberships(
        db,
        project_id=project_id,
        current_user=current_user,
    )


@router.post(
    "/{project_id}/members",
    response_model=projectMembershipSchema.ProjectMembershipOut,
    status_code=status.HTTP_201_CREATED,
)
def create_project_member(
    project_id: int,
    payload: projectMembershipSchema.ProjectMembershipCreate,
    current_user: CurrentUserDep,
    db: DBDep,
):
    return project_membership_service.create_membership(
        db,
        project_id=project_id,
        user_id=payload.user_id,
        role=payload.role,
        current_user=current_user,
    )


@router.patch("/{project_id}/members/{user_id}", response_model=projectMembershipSchema.ProjectMembershipOut)
def update_project_member(
    project_id: int,
    user_id: int,
    payload: projectMembershipSchema.ProjectMembershipUpdate,
    current_user: CurrentUserDep,
    db: DBDep,
):
    return project_membership_service.update_membership(
        db,
        project_id=project_id,
        user_id=user_id,
        role=payload.role,
        current_user=current_user,
    )


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_member(project_id: int, user_id: int, current_user: CurrentUserDep, db: DBDep):
    project_membership_service.delete_membership(
        db,
        project_id=project_id,
        user_id=user_id,
        current_user=current_user,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
