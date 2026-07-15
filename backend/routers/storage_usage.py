# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import os.path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, BackgroundTasks, status
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from schemas import storageUsageSchema, commonSchema
from crud import storageUsageCrud, usersCrud, groupCrud, volumeCrud
from dependencies import get_db, require_super_admin
from datetime import datetime, timedelta
from utils.plot import plot_real_time_line
from utils.common import convert_timestamp_to_datetime
import logging
from routers.common import handle_exceptions
from celery_tasks.manager.storageMonitor import StorageManagement
from utils.storageTarget import resolve_group_storage_target
from fastapi.responses import StreamingResponse
import urllib.parse
from routers.common import create_user_folder_by_storage_usage_id, back_up_user_storage_usage_by_storage_usage_id

logger = logging.getLogger('app:storage-usages')
router = APIRouter(
    prefix="/storage-usages",
    tags=["storage-usages"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=storageUsageSchema.StorageUsage)
@handle_exceptions
def create_storage_usage(storage_usage: storageUsageSchema.StorageUsageCreate, background_tasks: BackgroundTasks,
                         _admin: None = Depends(require_super_admin),
                         db: Session = Depends(get_db)):
    user_db = usersCrud.get_user_by_id(db, storage_usage.user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    group_db = groupCrud.get_group_by_id(db, storage_usage.group_id)
    if not group_db:
        raise HTTPException(status_code=404, detail="Group not found")
    linux_path = os.path.join(group_db.linux_path, user_db.rd_username)
    storage_exit, storage_usage_db = storageUsageCrud.create_storage_usage(db=db, storage_usage=storage_usage,
                                                                           linux_path=linux_path,
                                                                           group=group_db)
    if storage_exit is True:
        raise HTTPException(status_code=400, detail="Folder exited .")
    if not storage_usage_db:
        raise HTTPException(status_code=400, detail="Failed to create user folder")
    background_tasks.add_task(create_user_folder_by_storage_usage_id, logger, storage_usage_db.id)
    return storageUsageCrud.serialize_storage_usage(storage_usage_db)


@router.get("/", response_model=commonSchema.ResponseModel, openapi_extra={"ai_exposed": True, "ai_name": "list_storage_usages", "ai_description": "分页查询用户目录和存储使用情况"})
@handle_exceptions
def read_storage_usages(page: int | None = 1, size: int | None = 20, nameLike: str | None = None,
                         prop: str | None = None,
                         order: str | None = None, user_id: int | str = Query(None), group_id: int | None = None,
                         storage_cluster_id: int | None = None, project_id: int | None = None,
                         group_tag_id: int | None = None, db: Session = Depends(get_db)):
    if user_id == "":
        user_id = None
    storage_usages, total = storageUsageCrud.get_storage_usages(db=db, page=page, size=size, nameLike=nameLike,
                                                                 prop=prop, order=order, user_id=user_id,
                                                                 group_id=group_id, storage_cluster_id=storage_cluster_id,
                                                                 project_id=project_id,
                                                                 group_tag_id=group_tag_id)
    return commonSchema.ResponseModel[storageUsageSchema.StorageUsage](
        content=[storageUsageCrud.serialize_storage_usage(item) for item in storage_usages],
        total=total,
    )


@router.get("/export/")
def export_storage_usages(export_type: str = 'pdf', nameLike: str | None = None, prop: str | None = None,
                          order: str | None = None, user_id: int | str = Query(None), group_id: int | None = None,
                          storage_cluster_id: int | None = None, project_id: int | None = None,
                          group_tag_id: int | None = None, db: Session = Depends(get_db)):
    if user_id == "":
        user_id = None
    headers = {
        "Content-Disposition": "attachment;",
        "Access-Control-Expose-Headers": "Content-Disposition, Filename",
    }
    if export_type == 'pdf':
        content = storageUsageCrud.export_storage_usage_to_pdf(
            db, nameLike, prop, order, user_id, group_id, storage_cluster_id,
            project_id, group_tag_id,
        )
        file_name = f"存储使用明细报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        media_type = "application/pdf"
    elif export_type == 'excel':
        content = storageUsageCrud.export_storage_usage_to_excel(
            db, nameLike, prop, order, user_id, group_id, storage_cluster_id,
            project_id, group_tag_id,
        )
        file_name = f"存储使用明细报表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise HTTPException(status_code=400, detail=f"No export type like {export_type}")
    encoded_file_name = urllib.parse.quote(file_name)
    headers['filename'] = encoded_file_name
    return StreamingResponse(content, media_type=media_type, headers=headers)


@router.get("/{storage_usage_id}", response_model=storageUsageSchema.StorageUsage, openapi_extra={"ai_exposed": True, "ai_name": "get_storage_usage", "ai_description": "查询指定用户目录或存储使用记录"})
def read_storage_usage(storage_usage_id: int, db: Session = Depends(get_db)):
    db_storage_usage = storageUsageCrud.get_storage_usage_by_id(db, storage_usage_id=storage_usage_id)
    if db_storage_usage is None:
        raise HTTPException(status_code=404, detail="StorageUsage not found")

    return storageUsageCrud.serialize_storage_usage(db_storage_usage)


@router.post("/{storage_usage_id}/back-up", status_code=status.HTTP_200_OK)
def back_up_storage_usage(storage_usage_id: int, background_tasks: BackgroundTasks,
                          storage_usage: storageUsageSchema.BackUp,
                          _admin: None = Depends(require_super_admin),
                          db: Session = Depends(get_db)):
    db_storage_usage = storageUsageCrud.get_storage_usage_by_id(db, storage_usage_id=storage_usage_id)
    if db_storage_usage is None:
        logger.error(f"{storage_usage_id} not exited in db .")
        return Response(status_code=status.HTTP_200_OK)
    if db_storage_usage.group.back_up_enabled is False:
        raise HTTPException(status_code=400,
                            detail="The project team disables the user backup function. Please check the project team Settings.")
    logger.warning(f"closed:{storage_usage.closed}")
    closed = False if storage_usage.closed is None else storage_usage.closed
    background_tasks.add_task(back_up_user_storage_usage_by_storage_usage_id, logger, storage_usage_id, closed)
    return Response(status_code=status.HTTP_200_OK)


@router.get("/{storage_usage_id}/realtime", response_model=commonSchema.ResponseStorageUsageModel, openapi_extra={"ai_exposed": True, "ai_name": "get_storage_usage_realtime", "ai_description": "查询用户目录实时容量趋势"})
def read_storage_usage_realtime_data(storage_usage_id: int, start_time: datetime | None = None,
                                     end_time: datetime | None = None,
                                     indicator: str = 'used', db: Session = Depends(get_db)):
    db_storage_usage = storageUsageCrud.get_storage_usage_by_id(db, storage_usage_id=storage_usage_id)
    if db_storage_usage is None:
        raise HTTPException(status_code=404, detail="StorageUsage not found")
    real_time_data = storageUsageCrud.get_storage_usages_real_time_data_by_id(db=db, storage_usage_id=storage_usage_id,
                                                                              start_time=start_time, end_time=end_time,
                                                                              indicator=indicator)
    return commonSchema.ResponseStorageUsageModel[storageUsageSchema.StorageUsage](data=real_time_data,
                                                                                   info=storageUsageCrud.serialize_storage_usage(db_storage_usage))


@router.post("/expand")
def expand_storage_usage_limit(
    payload: storageUsageSchema.StorageUsageExpand,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    expand_id = payload.expand_id
    expand_type = payload.expand_type
    size = payload.size
    if expand_type == "Group":
        target = groupCrud.get_group_by_id(db, expand_id)
        cluster = target.storage_cluster if target is not None else None
    elif expand_type == "StorageUsage":
        target = storageUsageCrud.get_storage_usage_by_id(db, expand_id)
        cluster = target.group.storage_cluster if target is not None and target.group is not None else None
    elif expand_type == "Volume":
        target = volumeCrud.get_volume_by_id(db, expand_id)
        cluster = target.storage_cluster if target is not None else None
    else:
        cluster = None
    if cluster is not None and (cluster.storage_type or "").lower() == "isilon":
        raise HTTPException(status_code=422, detail="Isilon storage targets do not support expansion")
    manage = StorageManagement(db, logger)
    try:
        manage.expand(expand_id=expand_id, size=size, expand_type=expand_type)
        result = {"id": expand_id, "size": size, "type": expand_type, "message": "Expansion successful"}
    except Exception as e:
        logger.error(f"Error expanding storage: {e}")
        raise HTTPException(status_code=400, detail="Expansion failed") from e

    return result


@router.get("/{storage_usage_id}/image")
def get_storage_usage_image_by_id(storage_usage_id: int, end_time: str | None = None, role: str = 'manager',
                                  db: Session = Depends(get_db)):
    try:
        if end_time is None:
            end_time = datetime.now()
        else:
            end_time = convert_timestamp_to_datetime(end_time)
        storage_usage_db = storageUsageCrud.get_storage_usage_by_id(db, storage_usage_id)
        if storage_usage_db is None:
            raise HTTPException(status_code=404, detail="StorageUsage not found")
        start_time = end_time - timedelta(days=31)
        result = storageUsageCrud.get_storage_usages_real_time_data_by_id(db=db, storage_usage_id=storage_usage_id,
                                                                          start_time=start_time, end_time=end_time)
        logger.info(result)
        # if not result:
        #     raise HTTPException(status_code=404, detail="No data found for the given storage usage ID")
        if role == 'cad':
            volume = resolve_group_storage_target(storage_usage_db.group)["volume"]
            if volume is None:
                raise HTTPException(status_code=422, detail="Group storage target does not exist")
            message = f"Volume {volume.name} 限额{round(volume.limit / 1024, 2)}T,已分配{round(volume.allocated / 1024, 2)}T,可用内存为:{round((volume.limit - volume.used) / 1024, 2)}T,使用率{volume.use_ratio}%"
            if volume.use_ratio >= 95 and volume.allocated > volume.limit:
                message += "(不建议扩容)"
        else:
            message = f"{storage_usage_db.linux_path}限额{round(storage_usage_db.limit / 1024, 2)}T,可用内存{round((storage_usage_db.limit - storage_usage_db.used) / 1024, 2)}T,使用率{storage_usage_db.use_ratio}%"
            if storage_usage_db.use_ratio < 80:
                message += "(不建议扩容)"
        image_path = plot_real_time_line(data=result, model_db=storage_usage_db,
                                         message=message, role=role, logger=logger)
        return FileResponse(image_path, media_type='image/png')
    except Exception as e:
        logger.exception("Failed to generate storage usage image")
        raise HTTPException(status_code=500, detail="Failed to generate storage usage image") from e


@router.put("/{storage_usage_id}", response_model=storageUsageSchema.StorageUsage)
def update_storage_usage(storage_usage_id: int, storage_usage: storageUsageSchema.StorageUsageUpdate,
                         _admin: None = Depends(require_super_admin),
                         db: Session = Depends(get_db)):
    db_storage_usage = storageUsageCrud.get_storage_usage_by_id(db, storage_usage_id=storage_usage_id)
    if db_storage_usage is None:
        raise HTTPException(status_code=404, detail="StorageUsage not found")
    updated = storageUsageCrud.update_storage_usage(
        db=db, storage_usage_id=storage_usage_id, storage_usage=storage_usage
    )
    return storageUsageCrud.serialize_storage_usage(updated)


@router.delete("/{storage_usage_id}", response_model=storageUsageSchema.StorageUsage)
def delete_storage_usage(
    storage_usage_id: int,
    _admin: None = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_storage_usage = storageUsageCrud.get_storage_usage_by_id(db, storage_usage_id=storage_usage_id)
    if db_storage_usage is None:
        raise HTTPException(status_code=404, detail="StorageUsage not found")
    return storageUsageCrud.delete_storage_usage(db=db, storage_usage_id=storage_usage_id)
