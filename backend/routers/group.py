# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from schemas import groupSchema, commonSchema, quotaSchema, storageTrendSchema
from crud import groupCrud
from dependencies import CurrentUserDep, UseRatioMaximum, UseRatioMinimum, get_db, require_super_admin, validate_use_ratio_range
from services import audit_service, quotaService
from services import project_access_service
from services.storageTrendService import build_storage_trend_meta, format_trend_data, resolve_trend_indicator, trend_data_unit
import logging
from utils.common import convert_timestamp_to_datetime
from utils.plot import plot_real_time_line
from utils.storageTarget import resolve_group_storage_target
from utils.auth_service import is_super_admin
from fastapi.responses import FileResponse

logger = logging.getLogger('app:groups')
router = APIRouter(
    prefix="/groups",
    tags=["groups"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=groupSchema.Group)
def create_group(
    group: groupSchema.GroupBindingCreate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return groupCrud.serialize_group(groupCrud.create_group(db=db, group=group))


@router.get("/", response_model=commonSchema.ResponseModel, openapi_extra={"ai_exposed": True, "ai_name": "list_groups", "ai_description": "分页查询项目组"})
def read_groups(page: int | None = 1, size: int | None = 20, nameLike: str | None = None, prop: str | None = None,
                order: str | None = None, qtree_id: int | None = None,
                volume_id: int | None = None, project_id: int | None = None,
                storage_cluster_id: int | None = None, group_tag_id: int | None = None,
                use_ratio_min: UseRatioMinimum = None, use_ratio_max: UseRatioMaximum = None,
                current_user: CurrentUserDep = None,
                db: Session = Depends(get_db)):
    use_ratio_min, use_ratio_max = validate_use_ratio_range(use_ratio_min, use_ratio_max)
    if project_id is not None:
        project_access_service.require_project_permission(db, current_user, project_id, "reader")
    groups, total = groupCrud.get_groups(db=db, page=page, size=size, nameLike=nameLike, prop=prop, order=order,
                                         qtree_id=qtree_id, volume_id=volume_id,
                                         project_id=project_id,
                                         storage_cluster_id=storage_cluster_id,
                                         group_tag_id=group_tag_id,
                                         accessible_project_ids=project_access_service.accessible_project_ids(db, current_user),
                                         use_ratio_min=use_ratio_min, use_ratio_max=use_ratio_max)
    return commonSchema.ResponseModel[groupSchema.Group](
        content=[
            groupCrud.serialize_group(
                group,
                capabilities=project_access_service.group_capabilities(current_user, group),
            )
            for group in groups
        ],
        total=total,
    )


@router.get("/{group_id}", response_model=groupSchema.Group, openapi_extra={"ai_exposed": True, "ai_name": "get_group", "ai_description": "查询指定项目组"})
def read_group(group_id: int, current_user: CurrentUserDep, db: Session = Depends(get_db)):
    db_group = project_access_service.require_group_permission(db, current_user, group_id)

    return groupCrud.serialize_group(
        db_group,
        capabilities=project_access_service.group_capabilities(current_user, db_group),
    )


@router.get("/{group_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel, openapi_extra={"ai_exposed": True, "ai_name": "get_group_realtime", "ai_description": "查询项目组实时容量趋势"})
def read_group_realtime_data(group_id: int, start_time: datetime | None = None, end_time: datetime | None = None,
                             indicator: storageTrendSchema.TrendIndicator = 'used', current_user: CurrentUserDep = None,
                             db: Session = Depends(get_db)):
    db_group = project_access_service.require_group_permission(db, current_user, group_id)
    trend_meta = build_storage_trend_meta(db, target_type="group", target=db_group)
    real_time_data = groupCrud.get_group_real_time_data_by_id(db=db, group_id=group_id,
                                                              start_time=start_time, end_time=end_time,
                                                              indicator=resolve_trend_indicator(indicator, trend_meta))
    data_unit = trend_data_unit("group", indicator)
    return commonSchema.ResponseStorageUsageModel[groupSchema.Group](data=format_trend_data(real_time_data, data_unit),
                                                                      info=groupCrud.serialize_group(
                                                                          db_group,
                                                                          capabilities=project_access_service.group_capabilities(
                                                                              current_user,
                                                                              db_group,
                                                                          ),
                                                                      ),
                                                                      trend_meta=trend_meta,
                                                                      data_unit=data_unit)


@router.put("/{group_id}", response_model=groupSchema.Group)
def update_group(
    group_id: int,
    group: groupSchema.GroupBindingUpdate,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_group = groupCrud.get_group_by_id(db, group_id=group_id)
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    updated = groupCrud.update_group(db=db, group_id=group_id, group=group)
    project_access_service.ensure_group_directory_readers(db, group_id=updated.id)
    db.commit()
    return groupCrud.serialize_group(updated)


@router.patch(
    "/{group_id}/quota",
    response_model=quotaSchema.QuotaAdjustmentResponse,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "adjust_group_quota",
        "ai_description": "调整项目组限额",
    },
)
def adjust_group_quota(
    group_id: int,
    payload: quotaSchema.QuotaAdjustmentRequest,
    request: Request,
    current_user: CurrentUserDep,
    db: Session = Depends(get_db),
):
    if not is_super_admin(current_user):
        quotaService.require_group_quota_adjustment_permission(
            db=db,
            group_id=group_id,
            current_user=current_user,
        )
    return quotaService.adjust_group_quota(
        db,
        group_id=group_id,
        request=payload,
        current_user=current_user,
        audit_context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
    )


@router.post("/{group_id}/quota/reconcile", response_model=quotaSchema.QuotaAdjustmentResponse)
def reconcile_group_quota(
    group_id: int,
    request: Request,
    current_user: CurrentUserDep,
    db: Session = Depends(get_db),
):
    return quotaService.reconcile_group_quota(
        db,
        group_id=group_id,
        current_user=current_user,
        audit_context=audit_service.audit_context_for_request(request, actor_user_id=current_user.id),
    )


@router.get("/{group_id}/quota/history")
def group_quota_history(
    group_id: int,
    current_user: CurrentUserDep,
    db: Session = Depends(get_db),
):
    return quotaService.group_quota_history(db, group_id=group_id, current_user=current_user)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_group = groupCrud.get_group_by_id(db, group_id=group_id)
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    groupCrud.delete_group(db, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{group_id}/image")
def get_storage_usage_image_by_id(group_id: int, end_time: str | None = None, role: str = 'manager',
                                  current_user: CurrentUserDep = None, db: Session = Depends(get_db)):
    if end_time is None:
        end_time = datetime.now()
    else:
        end_time = convert_timestamp_to_datetime(end_time)
    group_db = project_access_service.require_group_permission(db, current_user, group_id)
    start_time = end_time - timedelta(days=31)
    result = groupCrud.get_group_real_time_data_by_id(db=db, group_id=group_id, start_time=start_time,
                                                      end_time=end_time)
    if not result:
        raise HTTPException(status_code=404, detail="No data found for the given storage usage ID")
    if role == 'cad':
        volume = resolve_group_storage_target(group_db)["volume"]
        if volume is None:
            raise HTTPException(status_code=422, detail="Group storage target does not exist")
        message = f"Volume {volume.name}限额{round(volume.limit / 1024, 2)}T,已分配{round(volume.allocated / 1024, 2)}T,可用内存为:{round((volume.limit - volume.used) / 1024, 2)}T,使用率{volume.use_ratio}%"
        if volume.use_ratio >= 95 and volume.allocated >= volume.limit:
            message += "(不建议扩容)"
    else:
        message = f"{group_db.linux_path}限额{round(group_db.limit / 1024, 2)}T,可用内存{round((group_db.limit - group_db.used) / 1024, 2)}T,使用率{group_db.use_ratio}%"
        if group_db.use_ratio < 80:
            message += "(不建议扩容)"
    image_path = plot_real_time_line(data=result, model_db=group_db,
                                     message=message, role=role, logger=logger)
    return FileResponse(image_path, media_type='image/png')
