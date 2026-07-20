# -*- coding: utf-8 -*-
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from schemas import usersSchema
from schemas.capacitySchema import CapacityResponseBase
from schemas.storageAlertRuleSchema import StorageAlertRule


class ProjectBaseInfo(CapacityResponseBase):
    id: int
    name: str
    limit: float | None = None
    soft_limit: float | None = None
    used: float | None = None
    use_ratio: float | None = None
    soft_use_ratio: float | None = None
    is_common: bool | None = False
    status: int | None = 1
    project_process_code: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(ProjectBaseInfo):
    recipients: str | None = None
    is_alert: bool | None = True
    storage_alert_rule: StorageAlertRule | None = None
    descriptions: str | None = None
    in_charge_user_id: int | None = None
    in_charge_user: usersSchema.OnlyUser | None = None

    @computed_field
    def recipient_ids(self) -> list[int]:
        return list(map(int, self.recipients.split())) if self.recipients else []


class Project(ProjectBase):
    id: int
    capabilities: dict[str, bool] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class ProjectStorageCluster(BaseModel):
    id: int
    name: str
    storage_type: str


class ProjectOverview(Project):
    storage_cluster_types: list[str] = Field(default_factory=list)
    storage_clusters: list[ProjectStorageCluster] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    recipient_ids: list[int] = Field(default_factory=list)
    is_alert: bool | None = True
    storage_alert_rule: StorageAlertRule | None = None
    descriptions: str | None = None
    name: str
    in_charge_user_id: int | None = None
    is_common: bool | None = False
    status: int | None = 1
    project_process_code: str | None = None


class ProjectResource(Project):
    project_summary: dict[str, Any] = Field(default_factory=dict)
    hosts_summary: dict[str, Any] = Field(default_factory=dict)
