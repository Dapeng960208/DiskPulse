# -*- coding: utf-8 -*-
from pydantic import BaseModel
from datetime import datetime
from schemas import usersSchema, groupSchema
from typing import List, Optional


class LargeFileBase(BaseModel):
    user_id: int
    group_id: int
    linux_path: str
    size: float = 0.0
    file_type: str = '其他'
    updated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")
        }


class LargeFileList(LargeFileBase):
    user: usersSchema.OnlyUser
    group: groupSchema.GroupBase
