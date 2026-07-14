# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from schemas import projectsSchema, qtreeSchema, usersSchema


class GroupDiskBase(BaseModel):
    id: int
    limit: float | None = None
    soft_limit: float | None = None
    used: float
    use_ratio: float | None = None
    soft_use_ratio: float | None = None
    updated_at: datetime


class GroupWriteBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    project_id: int | None = None
    storage_cluster_id: int | None = None
    group_tag_id: int | None = None
    volume_id: int | None = None
    qtree_id: int | None = None
    monitor_host_id: int | None = None
    linux_path: str | None = None
    back_path: str | None = None
    limit: float | None = 0
    soft_limit: float | None = None
    used: float | None = 0
    use_ratio: float | None = 0
    soft_use_ratio: float | None = None
    associated_mail_groups: str | list | None = None
    in_charge_user_id: int | None = None
    associate_multiple_groups: bool = False
    enable_monitoring: bool = True
    completed: bool | None = False
    back_up_enabled: bool | None = True
    updated_at: datetime | None = None

    @field_validator("associated_mail_groups", mode="before")
    @classmethod
    def normalize_mail_groups(cls, value):
        if isinstance(value, list):
            return ",".join(value)
        return value


class GroupBindingCreate(GroupWriteBase):
    name: str
    project_id: int
    storage_cluster_id: int
    group_tag_id: int

    @model_validator(mode="after")
    def validate_target(self):
        if (self.volume_id is None) == (self.qtree_id is None):
            raise ValueError("Exactly one of volume_id or qtree_id is required")
        return self


class GroupBindingUpdate(GroupWriteBase):
    @model_validator(mode="after")
    def validate_binding_update(self):
        binding_fields = {
            "project_id",
            "storage_cluster_id",
            "group_tag_id",
            "volume_id",
            "qtree_id",
        }
        if not self.model_fields_set.intersection(binding_fields):
            return self
        if any(
            getattr(self, field) is None
            for field in ("project_id", "storage_cluster_id", "group_tag_id")
        ):
            raise ValueError(
                "project_id, storage_cluster_id and group_tag_id are required "
                "when changing storage target"
            )
        if (self.volume_id is None) == (self.qtree_id is None):
            raise ValueError("Exactly one of volume_id or qtree_id is required")
        return self


class GroupTagSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class StorageClusterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    storage_type: str


class StorageTargetSummary(BaseModel):
    type: Literal["volume", "qtree"]
    id: int
    name: str


class GroupBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int | None = None
    storage_cluster_id: int | None = None
    group_tag_id: int | None = None
    volume_id: int | None = None
    monitor_host_id: int | None = None
    name: str
    qtree_id: int | None = None
    linux_path: str | None = None
    back_path: str | None = None
    limit: float | None = 0
    soft_limit: float | None = None
    used: float | None = 0
    use_ratio: float | None = 0
    soft_use_ratio: float | None = None
    associated_mail_groups: str | list | None = None
    in_charge_user_id: int | None = None
    associate_multiple_groups: bool = False
    enable_monitoring: bool = True
    updated_at: datetime | None = None
    in_charge_user: usersSchema.OnlyUser | None = None
    completed: bool | None = False
    back_up_enabled: bool | None = True


class Group(GroupBase):
    id: int
    project_id: int
    storage_cluster_id: int
    group_tag_id: int
    project: projectsSchema.ProjectBaseInfo
    group_tag: GroupTagSummary
    qtree: qtreeSchema.QtreeForGroup | None = None
    storage_cluster: StorageClusterSummary | None = None
    storage_target: StorageTargetSummary | None = None


Group.model_rebuild()
