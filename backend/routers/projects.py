# -*- coding: utf-8 -*-
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from crud import projectsCrud
from dependencies import CurrentUserDep, get_db, require_super_admin
from schemas import commonSchema, projectsSchema, storageTrendSchema
from services import project_access_service
from services.storageTrendService import build_storage_trend_meta, resolve_trend_indicator

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=commonSchema.ResponseModel, openapi_extra={"ai_exposed": True, "ai_name": "list_projects", "ai_description": "分页查询项目"})
def read_projects(
    current_user: CurrentUserDep,
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
        accessible_project_ids=project_access_service.accessible_project_ids(db, current_user),
    )
    return commonSchema.ResponseModel[projectsSchema.ProjectOverview](
        content=projects,
        total=total,
    )


@router.post("/", response_model=projectsSchema.Project)
def create_project(
    project: projectsSchema.ProjectUpdate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    if projectsCrud.get_project_by_name(db=db, name=project.name) is not None:
        raise HTTPException(status_code=400, detail="The project exists")
    return projectsCrud.create_project(db=db, project=project)


@router.get("/storage/summary", response_model=commonSchema.ResponseResourceModel, openapi_extra={"ai_exposed": True, "ai_name": "get_project_storage_summary", "ai_description": "查询项目存储汇总"})
def get_project_storage_summary(
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    summary = projectsCrud.get_project_storage_summary(db=db)
    tree = projectsCrud.get_project_tree_summary(db=db)
    return commonSchema.ResponseResourceModel(data=summary, tree=tree)


@router.get("/storage/groups", response_model=commonSchema.ResponseResourceModel, openapi_extra={"ai_exposed": True, "ai_name": "list_project_storage_groups", "ai_description": "查询项目存储组"})
def get_project_groups_storage_usage(
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    groups = projectsCrud.get_project_groups_storage_usage(db=db)
    return commonSchema.ResponseResourceModel(data=groups)


@router.get("/{project_id}/storage", response_model=commonSchema.ResponseStorageUsageModel, openapi_extra={"ai_exposed": True, "ai_name": "get_project_storage", "ai_description": "查询指定项目存储使用情况"})
def read_project_storage_usage_by_id(
    project_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    indicator: storageTrendSchema.TrendIndicator = "used",
    current_user: CurrentUserDep = None,
    db: Session = Depends(get_db),
):
    project_db = projectsCrud.get_project_by_id(db=db, id=project_id)
    if project_db is None:
        raise HTTPException(status_code=404, detail="The project was not found")
    project_access_service.require_project_permission(db, current_user, project_id, "reader")
    trend_meta = build_storage_trend_meta(db, target_type="project", target=project_db)
    real_time_data = projectsCrud.get_project_storage_usages_real_time_data_by_id(
        db=db,
        project_id=project_id,
        start_time=start_time,
        end_time=end_time,
        indicator=resolve_trend_indicator(indicator, trend_meta),
    )
    return commonSchema.ResponseStorageUsageModel[projectsSchema.ProjectBaseInfo](
        data=real_time_data,
        info=project_db,
        trend_meta=trend_meta,
    )


@router.get("/{project_id}", response_model=projectsSchema.Project, openapi_extra={"ai_exposed": True, "ai_name": "get_project", "ai_description": "查询指定项目"})
def read_project_by_id(project_id: int, current_user: CurrentUserDep, db: Session = Depends(get_db)):
    project_db = projectsCrud.get_project_by_id(db=db, id=project_id)
    if project_db is None:
        raise HTTPException(status_code=404, detail="The project was not found")
    project_access_service.require_project_permission(db, current_user, project_id, "reader")
    result = projectsSchema.Project.model_validate(project_db).model_dump()
    result["capabilities"] = project_access_service.project_capabilities(
        db,
        current_user,
        project_id,
    )
    return result


@router.put("/{project_id}", response_model=projectsSchema.Project)
def update_project_by_id(
    project_id: int,
    project: projectsSchema.ProjectUpdate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    project_db = projectsCrud.get_project_by_id(db=db, id=project_id)
    if project_db is None:
        raise HTTPException(status_code=404, detail="The project was not found")
    return projectsCrud.update_project(db=db, project_id=project_id, project=project)


@router.get("/{project_id}/storage-tree", response_model=commonSchema.ResponseResourceModel, openapi_extra={"ai_exposed": True, "ai_name": "get_project_storage_tree", "ai_description": "查询项目存储树"})
def get_project_storage_tree_by_id(
    project_id: int,
    value_type: str = "limit",
    current_user: CurrentUserDep = None,
    db: Session = Depends(get_db),
):
    project_access_service.require_project_permission(db, current_user, project_id, "reader")
    tree = projectsCrud.get_project_tree_summary_by_id(db=db, project_id=project_id, value_type=value_type)
    return commonSchema.ResponseResourceModel(data=tree)
