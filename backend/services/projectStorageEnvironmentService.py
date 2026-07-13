# -*- coding: utf-8 -*-
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import (
    projectStorageEnvironmentCrud,
    projectsCrud,
    questDbCrud,
    storageClusterCrud,
)
from models import Project, ProjectStorageEnvironment, User
from schemas import projectStorageEnvironmentSchema
from utils.auth_service import is_super_admin


def _get_project(db: Session, project_id: int) -> Project:
    project = projectsCrud.get_project_by_id(db=db, id=project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def _get_environment(
    db: Session,
    environment_id: int,
) -> ProjectStorageEnvironment:
    environment = projectStorageEnvironmentCrud.get_environment(db, environment_id)
    if environment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage environment not found",
        )
    return environment


def _require_project_reader(project: Project, current_user: User) -> None:
    if is_super_admin(current_user):
        return
    if current_user.id not in {project.in_charge_user_id, project.pt_user_id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project access forbidden",
        )


def list_environments(
    db: Session,
    *,
    project_id: int,
    current_user: User,
    page: int,
    size: int,
) -> dict:
    project = _get_project(db, project_id)
    _require_project_reader(project, current_user)
    environments, total = projectStorageEnvironmentCrud.list_environments(
        db,
        project_id=project_id,
        page=page,
        size=size,
    )
    return {"content": environments, "total": total}


def get_environment_for_user(
    db: Session,
    *,
    environment_id: int,
    current_user: User,
) -> ProjectStorageEnvironment:
    environment = _get_environment(db, environment_id)
    _require_project_reader(_get_project(db, environment.project_id), current_user)
    return environment


def get_environment_summary(
    db: Session,
    *,
    environment_id: int,
    current_user: User,
) -> ProjectStorageEnvironment:
    return get_environment_for_user(
        db,
        environment_id=environment_id,
        current_user=current_user,
    )


def get_environment_realtime(
    db: Session,
    *,
    environment_id: int,
    current_user: User,
    start_time: datetime | None,
    end_time: datetime | None,
    indicator: str,
) -> dict:
    if (start_time is None) != (end_time is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_time and end_time must be provided together",
        )
    if start_time is not None and start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_time must not be after end_time",
        )

    environment = get_environment_for_user(
        db,
        environment_id=environment_id,
        current_user=current_user,
    )
    data = questDbCrud.get_real_time_data_by_id(
        db=db,
        attribute_id=environment.id,
        start_time=start_time,
        end_time=end_time,
        indicator=indicator,
        table_prefix="project_environment",
    )
    return {"info": environment, "data": data}


def _check_create_conflicts(
    db: Session,
    *,
    project_id: int,
    environment: projectStorageEnvironmentSchema.ProjectStorageEnvironmentCreate,
) -> None:
    if projectStorageEnvironmentCrud.get_by_project_and_name(
        db,
        project_id=project_id,
        name=environment.name,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project environment name already exists",
        )
    if projectStorageEnvironmentCrud.get_by_project_and_cluster(
        db,
        project_id=project_id,
        storage_cluster_id=environment.storage_cluster_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project storage cluster already assigned",
        )


def create_environment(
    db: Session,
    *,
    project_id: int,
    environment: projectStorageEnvironmentSchema.ProjectStorageEnvironmentCreate,
) -> ProjectStorageEnvironment:
    _get_project(db, project_id)
    if storageClusterCrud.get_storage_cluster(db, environment.storage_cluster_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage cluster not found",
        )
    _check_create_conflicts(db, project_id=project_id, environment=environment)
    db_environment = ProjectStorageEnvironment(
        project_id=project_id,
        **environment.model_dump(),
    )
    try:
        projectStorageEnvironmentCrud.add_environment(db, db_environment)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project storage environment conflict",
        ) from error
    except Exception:
        db.rollback()
        raise
    return _get_environment(db, db_environment.id)


def update_environment(
    db: Session,
    *,
    environment_id: int,
    environment: projectStorageEnvironmentSchema.ProjectStorageEnvironmentUpdate,
) -> ProjectStorageEnvironment:
    db_environment = _get_environment(db, environment_id)
    update_data = environment.model_dump(exclude_unset=True)
    name = update_data.get("name")
    if name is not None and projectStorageEnvironmentCrud.get_by_project_and_name(
        db,
        project_id=db_environment.project_id,
        name=name,
        exclude_id=environment_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project environment name already exists",
        )
    for field, value in update_data.items():
        setattr(db_environment, field, value)
    if update_data:
        db_environment.updated_at = datetime.now()
    try:
        projectStorageEnvironmentCrud.flush(db)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project environment name already exists",
        ) from error
    except Exception:
        db.rollback()
        raise
    return _get_environment(db, environment_id)


def delete_environment(db: Session, *, environment_id: int) -> None:
    environment = _get_environment(db, environment_id)
    if projectStorageEnvironmentCrud.has_linked_group(db, environment_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Storage environment has linked group",
        )
    try:
        projectStorageEnvironmentCrud.delete_environment(db, environment)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Storage environment has linked group",
        ) from error
    except Exception:
        db.rollback()
        raise
