# -*- coding: utf-8 -*-
from pydantic import BaseModel, field_validator
from datetime import datetime
from schemas import projectsSchema, qtreeSchema, usersSchema
from schemas.storageClusterSchema import StorageCluster

class GroupDiskBase(BaseModel):
    id: int
    limit: float | None = None
    used: float
    use_ratio: float | None = None
    updated_at: datetime


class GroupBase(BaseModel):
    project_id: int
    monitor_host_id: int | None = None
    name: str
    qtree_id: int | None = None
    linux_path: str | None = None
    back_path: str | None = None
    limit: float | None = 0
    used: float | None = 0
    use_ratio: float | None = 0
    associated_mail_groups: str | list | None = None
    in_charge_user_id: int | None = None
    associate_multiple_groups: bool = False
    enable_monitoring: bool = True
    updated_at: datetime = datetime.now()
    in_charge_user: usersSchema.OnlyUser | None = None
    completed: bool | None = False
    back_up_enabled: bool | None = True
    storage_cluster_id: int | None = None

    @field_validator('associated_mail_groups', mode='before')
    def set_default_jobs(cls, v):
        if v is None:
            return None
        elif isinstance(v, list):
            return ','.join(v)
        else:
            return v.split(',')

    class Config:
        from_attributes = True


class GroupCreate(GroupBase):
    pass


class GroupUpdate(GroupBase):
    pass


class Group(GroupBase):
    id: int
    project: projectsSchema.ProjectBaseInfo
    qtree: qtreeSchema.QtreeForGroup | None = None
    storage_cluster: StorageCluster | None = None

    class Config:
        from_attributes = True


Group.model_rebuild()
