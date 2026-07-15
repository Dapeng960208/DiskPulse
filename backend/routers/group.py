# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from schemas import groupSchema, commonSchema
from crud import groupCrud
from dependencies import get_db, require_super_admin
import logging
from utils.common import convert_timestamp_to_datetime
from utils.plot import plot_real_time_line
from utils.storageTarget import resolve_group_storage_target
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
                db: Session = Depends(get_db)):
    groups, total = groupCrud.get_groups(db=db, page=page, size=size, nameLike=nameLike, prop=prop, order=order,
                                         qtree_id=qtree_id, volume_id=volume_id,
                                         project_id=project_id,
                                         storage_cluster_id=storage_cluster_id,
                                         group_tag_id=group_tag_id)
    return commonSchema.ResponseModel[groupSchema.Group](
        content=[groupCrud.serialize_group(group) for group in groups],
        total=total,
    )


@router.get("/{group_id}", response_model=groupSchema.Group, openapi_extra={"ai_exposed": True, "ai_name": "get_group", "ai_description": "查询指定项目组"})
def read_group(group_id: int, db: Session = Depends(get_db)):
    db_group = groupCrud.get_group_by_id(db, group_id=group_id)
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    return groupCrud.serialize_group(db_group)


@router.get("/{group_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel, openapi_extra={"ai_exposed": True, "ai_name": "get_group_realtime", "ai_description": "查询项目组实时容量趋势"})
def read_group_realtime_data(group_id: int, start_time: datetime | None = None, end_time: datetime | None = None,
                             indicator: str = 'used', db: Session = Depends(get_db)):
    db_group = groupCrud.get_group_by_id(db, group_id=group_id)
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    real_time_data = groupCrud.get_group_real_time_data_by_id(db=db, group_id=group_id,
                                                              start_time=start_time, end_time=end_time,
                                                              indicator=indicator)
    return commonSchema.ResponseStorageUsageModel[groupSchema.Group](data=real_time_data,
                                                                     info=groupCrud.serialize_group(db_group))


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
    return groupCrud.serialize_group(
        groupCrud.update_group(db=db, group_id=group_id, group=group)
    )


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
                                  db: Session = Depends(get_db)):
    if end_time is None:
        end_time = datetime.now()
    else:
        end_time = convert_timestamp_to_datetime(end_time)
    group_db = groupCrud.get_group_by_id(db, group_id)
    if group_db is None:
        raise HTTPException(status_code=404, detail="Group not found")
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
