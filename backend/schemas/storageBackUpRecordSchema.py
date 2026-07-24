# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict, field_serializer
from utils.datetime_utils import to_utc_z
from datetime import datetime
from schemas.usersSchema import OnlyUser


from schemas.base import UTCBaseModel as BaseModel


class StorageBackUpRecordBase(BaseModel):
    source_path: str
    destination_path: str
    start_time: datetime
    end_time: datetime
    # 0 移动失败 1 移动中 2 移动成功 3 已删除
    status: int = 1
    process_uid: str | None = None


class StorageBackUpRecord(StorageBackUpRecordBase):
    id: int
    user_id: int
    user: OnlyUser | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("start_time", "end_time", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return to_utc_z(value) if value else None
