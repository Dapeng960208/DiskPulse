# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request, BackgroundTasks, status
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from schemas import storageBackUpRecordSchema, commonSchema
from crud import storageBackUpRecordCrud, usersCrud, groupCrud
from dependencies import get_db, require_super_admin
import logging
from routers.common import delete_storage_back_up_record_by_storage_usage_id,rollback_storage_back_up_record_by_storage_usage_id

logger = logging.getLogger('app:storage-usages')
router = APIRouter(
    prefix="/storage-back-up-records",
    tags=["storage-back-up-records"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/",
    response_model=commonSchema.ResponseModel,
    openapi_extra={
        "ai_exposed": True,
        "ai_system_management": True,
        "ai_name": "list_storage_backup_records",
        "ai_description": "分页查询离职备份记录",
    },
)
def read_storage_back_up_records(page: int | None = 1, size: int | None = 20, nameLike: str | None = None,
                                 prop: str | None = None,
                                 order: str | None = None, user_id: int | str = Query(None),
                                 _admin: None = Depends(require_super_admin),
                                 db: Session = Depends(get_db)):
    if user_id == "":
        user_id = None
    storage_back_up_records, total = storageBackUpRecordCrud.get_storage_back_up_records(db=db, page=page, size=size,
                                                                                         nameLike=nameLike,
                                                                                         prop=prop, order=order,
                                                                                         user_id=user_id)
    return commonSchema.ResponseModel[storageBackUpRecordSchema.StorageBackUpRecord](content=storage_back_up_records,
                                                                                     total=total)


@router.delete(
    "/{storage_back_up_record_id}",
    status_code=status.HTTP_200_OK,
)
def delete_storage_usage(storage_back_up_record_id: int, background_tasks: BackgroundTasks,
                         _admin: None = Depends(require_super_admin),
                         db: Session = Depends(get_db)):
    db_storage_usage = storageBackUpRecordCrud.get_storage_back_up_record_by_id(db, storage_back_up_record_id)
    if db_storage_usage is None:
        raise HTTPException(status_code=404, detail="Storage Back Up record  not found")
    if db_storage_usage.status != 2:
        raise HTTPException(status_code=400,
                            detail="A directory can be deleted only when it is backed up successfully .")
    background_tasks.add_task(delete_storage_back_up_record_by_storage_usage_id, logger, storage_back_up_record_id)
    return Response(status_code=status.HTTP_200_OK)


@router.post("/{storage_back_up_record_id}/rollback", status_code=status.HTTP_200_OK)
def delete_storage_usage(storage_back_up_record_id: int, background_tasks: BackgroundTasks,
                         _admin: None = Depends(require_super_admin),
                         db: Session = Depends(get_db)):
    db_storage_usage = storageBackUpRecordCrud.get_storage_back_up_record_by_id(db, storage_back_up_record_id)
    if db_storage_usage is None:
        raise HTTPException(status_code=404, detail="Storage Back Up record  not found")
    if db_storage_usage.status != 2:
        raise HTTPException(status_code=400,
                            detail="A directory can be rolled back only when it is backed up successfully .")
    background_tasks.add_task(rollback_storage_back_up_record_by_storage_usage_id, logger, storage_back_up_record_id)
    return Response(status_code=status.HTTP_200_OK)
