# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from dependencies import CurrentUserDep, get_db, require_super_admin
from schemas import projectStorageEnvironmentSchema
from services import projectStorageEnvironmentService


router = APIRouter(tags=["project-storage-environments"])
DBDep = Annotated[Session, Depends(get_db)]
AdminDep = Annotated[None, Depends(require_super_admin)]


@router.get(
    "/projects/{project_id}/storage-environments",
    response_model=projectStorageEnvironmentSchema.ProjectStorageEnvironmentPage,
)
def list_project_storage_environments(
    project_id: int,
    current_user: CurrentUserDep,
    db: DBDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return projectStorageEnvironmentService.list_environments(
        db,
        project_id=project_id,
        current_user=current_user,
        page=page,
        size=size,
    )


@router.post(
    "/projects/{project_id}/storage-environments",
    response_model=projectStorageEnvironmentSchema.ProjectStorageEnvironment,
    status_code=status.HTTP_201_CREATED,
)
def create_project_storage_environment(
    project_id: int,
    environment: projectStorageEnvironmentSchema.ProjectStorageEnvironmentCreate,
    _admin: AdminDep,
    db: DBDep,
):
    return projectStorageEnvironmentService.create_environment(
        db,
        project_id=project_id,
        environment=environment,
    )


@router.get(
    "/storage-environments/{environment_id}",
    response_model=projectStorageEnvironmentSchema.ProjectStorageEnvironment,
)
def get_project_storage_environment(
    environment_id: int,
    current_user: CurrentUserDep,
    db: DBDep,
):
    return projectStorageEnvironmentService.get_environment_for_user(
        db,
        environment_id=environment_id,
        current_user=current_user,
    )


@router.get(
    "/storage-environments/{environment_id}/summary",
    response_model=projectStorageEnvironmentSchema.ProjectStorageEnvironmentSummary,
)
def get_project_storage_environment_summary(
    environment_id: int,
    current_user: CurrentUserDep,
    db: DBDep,
):
    return projectStorageEnvironmentService.get_environment_summary(
        db,
        environment_id=environment_id,
        current_user=current_user,
    )


@router.get(
    "/storage-environments/{environment_id}/realtime",
    response_model=projectStorageEnvironmentSchema.ProjectStorageEnvironmentRealtime,
)
def get_project_storage_environment_realtime(
    environment_id: int,
    current_user: CurrentUserDep,
    db: DBDep,
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    indicator: Annotated[
        Literal["used", "use_ratio", "used_ratio"],
        Query(),
    ] = "used",
):
    return projectStorageEnvironmentService.get_environment_realtime(
        db,
        environment_id=environment_id,
        current_user=current_user,
        start_time=start_time,
        end_time=end_time,
        indicator=indicator,
    )


@router.put(
    "/storage-environments/{environment_id}",
    response_model=projectStorageEnvironmentSchema.ProjectStorageEnvironment,
)
def update_project_storage_environment(
    environment_id: int,
    environment: projectStorageEnvironmentSchema.ProjectStorageEnvironmentUpdate,
    _admin: AdminDep,
    db: DBDep,
):
    return projectStorageEnvironmentService.update_environment(
        db,
        environment_id=environment_id,
        environment=environment,
    )


@router.delete(
    "/storage-environments/{environment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project_storage_environment(
    environment_id: int,
    _admin: AdminDep,
    db: DBDep,
):
    projectStorageEnvironmentService.delete_environment(
        db,
        environment_id=environment_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
