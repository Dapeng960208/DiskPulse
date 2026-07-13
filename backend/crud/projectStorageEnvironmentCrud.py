# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session, joinedload

from models import Group, ProjectStorageEnvironment


def get_environment(
    db: Session,
    environment_id: int,
) -> ProjectStorageEnvironment | None:
    return (
        db.query(ProjectStorageEnvironment)
        .options(joinedload(ProjectStorageEnvironment.storage_cluster))
        .filter(ProjectStorageEnvironment.id == environment_id)
        .first()
    )


def list_environments(
    db: Session,
    *,
    project_id: int,
    page: int,
    size: int,
) -> tuple[list[ProjectStorageEnvironment], int]:
    query = db.query(ProjectStorageEnvironment).filter(
        ProjectStorageEnvironment.project_id == project_id
    )
    total = query.count()
    environments = (
        query.options(joinedload(ProjectStorageEnvironment.storage_cluster))
        .order_by(ProjectStorageEnvironment.id.asc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return environments, total


def get_by_project_and_name(
    db: Session,
    *,
    project_id: int,
    name: str,
    exclude_id: int | None = None,
) -> ProjectStorageEnvironment | None:
    query = db.query(ProjectStorageEnvironment).filter(
        ProjectStorageEnvironment.project_id == project_id,
        ProjectStorageEnvironment.name == name,
    )
    if exclude_id is not None:
        query = query.filter(ProjectStorageEnvironment.id != exclude_id)
    return query.first()


def get_by_project_and_cluster(
    db: Session,
    *,
    project_id: int,
    storage_cluster_id: int,
) -> ProjectStorageEnvironment | None:
    return (
        db.query(ProjectStorageEnvironment)
        .filter(
            ProjectStorageEnvironment.project_id == project_id,
            ProjectStorageEnvironment.storage_cluster_id == storage_cluster_id,
        )
        .first()
    )


def has_linked_group(db: Session, environment_id: int) -> bool:
    return (
        db.query(Group.id)
        .filter(Group.project_environment_id == environment_id)
        .first()
        is not None
    )


def add_environment(
    db: Session,
    environment: ProjectStorageEnvironment,
) -> None:
    db.add(environment)
    db.flush()


def flush(db: Session) -> None:
    db.flush()


def delete_environment(
    db: Session,
    environment: ProjectStorageEnvironment,
) -> None:
    db.delete(environment)
    db.flush()
