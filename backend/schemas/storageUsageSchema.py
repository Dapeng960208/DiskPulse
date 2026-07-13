# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from datetime import datetime
from schemas import usersSchema, groupSchema

class StorageUsageBase(BaseModel):
    user_id: int
    group_id: int
    linux_path: str
    limit: float | None = None
    soft_limit: float | None = None
    used: float | None = None
    use_ratio: float | None = None
    soft_use_ratio: float | None = None
    file_used: float | None = None
    file_limit: float | None = None
    updated_at: datetime
    storage_cluster_id: int | None = None

    class Config:
        from_attributes = True


class StorageUsageCreate(BaseModel):
    user_id: int
    group_id: int


class StorageUsageUpdate(StorageUsageBase):
    pass


class StorageUsage(StorageUsageBase):
    id: int

    size: int | None = 0
    blocks: float | None = 0
    io_block: float | None = 0
    type: str | None = ''
    device: str | None = ''
    inode: str | None = ''
    links: int | None = None
    access: str | None = ''
    gid: str | None = ''
    access_time: datetime | None = None
    modify_time: datetime | None = None
    change_time: datetime | None = None
    birth_time: datetime | None = None
    user: usersSchema.OnlyUser
    group: groupSchema.GroupBase
    project_environment: groupSchema.ProjectEnvironmentSummary | None = None
    storage_cluster: groupSchema.StorageClusterSummary | None = None
    storage_target: groupSchema.StorageTargetSummary | None = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")
        }


StorageUsage.model_rebuild()


class StorageUsageExpand(BaseModel):
    expand_id: int = Field(gt=0)
    expand_type: str = Field(pattern="^(StorageUsage|Group|Volume|Qtree)$")
    size: float = Field(gt=0)


class StorageUsageExport(BaseModel):
    linux_path: str
    limit: float | None = 0
    soft_limit: float | None = None
    used: float | None = 0
    use_ratio: float | None = 0.0
    soft_use_ratio: float | None = None
    file_used: float | None = 0
    access_time: datetime | str | None = ''
    modify_time: datetime | str | None = ''


class BackUp(BaseModel):
    closed: bool | None = None
