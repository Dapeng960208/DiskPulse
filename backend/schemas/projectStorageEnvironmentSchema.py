# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectStorageEnvironmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=128)
    storage_cluster_id: int
    description: str | None = None
    is_active: bool = True


class ProjectStorageEnvironmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def reject_null_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("name must not be null")
        return value


class StorageClusterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    storage_type: str


class ProjectStorageEnvironment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    storage_cluster_id: int
    name: str
    description: str | None
    is_active: bool
    limit: float | None
    soft_limit: float | None
    used: float | None
    use_ratio: float | None
    soft_use_ratio: float | None
    collection_status: str
    last_collected_at: datetime | None
    created_at: datetime
    updated_at: datetime
    storage_cluster: StorageClusterSummary


class ProjectStorageEnvironmentPage(BaseModel):
    content: list[ProjectStorageEnvironment]
    total: int


class ProjectStorageEnvironmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    limit: float | None
    soft_limit: float | None
    used: float | None
    use_ratio: float | None
    soft_use_ratio: float | None
    collection_status: str
    last_collected_at: datetime | None
    storage_cluster: StorageClusterSummary


class ProjectStorageEnvironmentRealtime(BaseModel):
    info: ProjectStorageEnvironmentSummary
    data: list[list[str | int | float | None]]
