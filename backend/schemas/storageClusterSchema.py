# -*- coding: utf-8 -*-
from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import Literal, Optional


class StorageClusterBase(BaseModel):
    name: str
    storage_type: str  # 'netapp' or 'isilon'
    storage_host: str | None = None
    storage_port: int | None = 22
    protocol: Literal["http", "https"] = "https"
    tls_verify: bool = True
    storage_user: str | None = None
    description: Optional[str] = None
    is_active: bool = True
    limit: Optional[float] = None

    @model_validator(mode="after")
    def disable_tls_verification_for_http(self):
        if self.protocol == "http":
            self.tls_verify = False
        return self


class StorageClusterCreate(StorageClusterBase):
    storage_password: str | None = None


class StorageClusterUpdate(BaseModel):
    name: Optional[str] = None
    storage_host: str | None = None
    storage_port: int | None = 22
    protocol: Literal["http", "https"] | None = None
    tls_verify: bool | None = None
    storage_user: str | None = None
    storage_password: str | None = None
    storage_type: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    limit: Optional[float] = None
    used: Optional[float] = None
    use_ratio: Optional[float] = None

    @model_validator(mode="after")
    def disable_tls_verification_for_http(self):
        if self.protocol == "http":
            self.tls_verify = False
        return self


class StorageCluster(StorageClusterBase):
    id: int
    used: Optional[float] = None
    use_ratio: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
