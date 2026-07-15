# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from schemas import largeFileSchema, commonSchema
from crud import largeFilesCrud
from dependencies import get_db
import logging
from routers.common import handle_exceptions
from datetime import datetime
import urllib.parse
from fastapi.responses import StreamingResponse

logger = logging.getLogger('app:large-files')
router = APIRouter(
    prefix="/large-files",
    tags=["large-files"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=commonSchema.ResponseModel, openapi_extra={"ai_exposed": True, "ai_name": "list_large_files", "ai_description": "分页查询大文件"})
@handle_exceptions
def read_large_files(page: int | None = 1, size: int | None = 20, nameLike: str | None = None,
                     prop: str | None = None,
                     order: str | None = None, user_id: int | str = Query(None), group_id: int | None = None,
                     db: Session = Depends(get_db)):
    if nameLike == "":
        nameLike = None
    large_files, total = largeFilesCrud.get_large_files(db=db, page=page, size=size, nameLike=nameLike,
                                                        prop=prop, order=order, user_id=user_id,
                                                        group_id=group_id)
    return commonSchema.ResponseModel[largeFileSchema.LargeFileList](content=large_files, total=total)


@router.get("/export/")
def export_large_files(nameLike: str | None = None, user_id: int | str = Query(None), group_id: int | None = None,
                          db: Session = Depends(get_db)):
    if user_id == "":
        user_id = None
    headers = {
        "Content-Disposition": "attachment;",
        "Access-Control-Expose-Headers": "Content-Disposition, Filename",
    }

    content = largeFilesCrud.export_large_files(db, nameLike,user_id, group_id)
    file_name = f"大文件_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    encoded_file_name = urllib.parse.quote(file_name)
    headers['filename'] = encoded_file_name
    return StreamingResponse(content, media_type=media_type, headers=headers)
