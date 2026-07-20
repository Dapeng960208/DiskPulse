# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime
from schemas import usersSchema, groupSchema
from schemas.capacitySchema import CapacityResponseBase
from typing import ClassVar, List, Optional


class LargeFileBase(BaseModel):
    user_id: int
    group_id: int
    linux_path: str
    size: float = 0.0
    file_type: str = '其他'
    updated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("updated_at", "created_at", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


class LargeFileList(CapacityResponseBase, LargeFileBase):
    capacity_field_names: ClassVar[tuple[str, ...]] = ("size",)
    user: usersSchema.OnlyUser
    group: groupSchema.GroupBase
