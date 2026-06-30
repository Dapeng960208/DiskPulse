# -*- coding: utf-8 -*-
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from crud import projectsCrud
from dependencies import get_db
from schemas import commonSchema, projectsSchema

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=commonSchema.ResponseModel)
def read_projects(
    page: int = 1,
    size: int = 20,
    nameLike: str | None = None,
    prop: str = Query(None),
    order: str = Query(None),
    status: int | None = None,
    db: Session = Depends(get_db),
):
    projects, total = projectsCrud.get_projects(
        db,
        page=page,
        size=size,
        nameLike=nameLike,
        status=status,
        prop=prop,
        order=order,
    )
    return commonSchema.ResponseModel[projectsSchema.Project](content=projects, total=total)


@router.post("/", response_model=projectsSchema.Project)
def create_project(project: projectsSchema.ProjectUpdate, db: Session = Depends(get_db)):
    if projectsCrud.get_project_by_name(db=db, name=project.name) is not None:
        raise HTTPException(status_code=400, detail="The project exists")
    return projectsCrud.create_project(db=db, project=project)


@router.get("/storage/summary", response_model=commonSchema.ResponseResourceModel)
def get_project_storage_summary(db: Session = Depends(get_db)):
    summary = projectsCrud.get_project_storage_summary(db=db)
    tree = projectsCrud.get_project_tree_summary(db=db)
    return commonSchema.ResponseResourceModel(data=summary, tree=tree)


@router.get("/storage/groups", response_model=commonSchema.ResponseResourceModel)
def get_project_groups_storage_usage(db: Session = Depends(get_db)):
    groups = projectsCrud.get_project_groups_storage_usage(db=db)
    return commonSchema.ResponseResourceModel(data=groups)


@router.get("/{project_id}/storage", response_model=commonSchema.ResponseStorageUsageModel)
def read_project_storage_usage_by_id(
    project_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    indicator: str = "used",
    db: Session = Depends(get_db),
):
    project_db = projectsCrud.get_project_by_id(db=db, id=project_id)
    if project_db is None:
        raise HTTPException(status_code=404, detail="The project was not found")
    real_time_data = projectsCrud.get_project_storage_usages_real_time_data_by_id(
        db=db,
        project_id=project_id,
        start_time=start_time,
        end_time=end_time,
        indicator=indicator,
    )
    return commonSchema.ResponseStorageUsageModel[projectsSchema.ProjectBaseInfo](data=real_time_data, info=project_db)


@router.get("/{project_id}", response_model=projectsSchema.Project)
def read_project_by_id(project_id: int, db: Session = Depends(get_db)):
    project_db = projectsCrud.get_project_by_id(db=db, id=project_id)
    if project_db is None:
        raise HTTPException(status_code=404, detail="The project was not found")
    return project_db


@router.put("/{project_id}", response_model=projectsSchema.Project)
def update_project_by_id(project_id: int, project: projectsSchema.ProjectUpdate, db: Session = Depends(get_db)):
    project_db = projectsCrud.get_project_by_id(db=db, id=project_id)
    if project_db is None:
        raise HTTPException(status_code=404, detail="The project was not found")
    return projectsCrud.update_project(db=db, project_id=project_id, project=project)


@router.get("/{project_id}/storage-tree", response_model=commonSchema.ResponseResourceModel)
def get_project_storage_tree_by_id(project_id: int, value_type: str = "limit", db: Session = Depends(get_db)):
    tree = projectsCrud.get_project_tree_summary_by_id(db=db, project_id=project_id, value_type=value_type)
    return commonSchema.ResponseResourceModel(data=tree)
