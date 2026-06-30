# -*- coding: utf-8 -*-
from pydantic import BaseModel, field_validator
from datetime import datetime
from schemas.usersSchema import OnlyUser


class StorageBackUpRecordBase(BaseModel):
    source_path: str
    destination_path: str
    start_time: datetime
    end_time: datetime
    # 0 移动失败 1 移动中 2 移动成功 3 已删除
    status: int = 1
    is_deleted: bool = False
    process_uid: str | None = None


class StorageBackUpRecord(StorageBackUpRecordBase):
    id: int
    user_id: int
    user: OnlyUser | None = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")
        }
