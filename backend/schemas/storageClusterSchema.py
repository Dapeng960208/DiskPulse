# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field, model_validator
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
    isilon_session_cache_mode: Literal["none", "file", "redis"] = "none"
    isilon_session_cache_path: str | None = Field(default=None, max_length=1024)
    description: Optional[str] = None
    is_active: bool = True
    limit: Optional[float] = None

    @model_validator(mode="after")
    def disable_tls_verification_for_http(self):
        if self.protocol == "http":
            self.tls_verify = False
        if self.storage_type != "isilon":
            self.isilon_session_cache_mode = "none"
            self.isilon_session_cache_path = None
        elif self.isilon_session_cache_mode == "file":
            self.isilon_session_cache_path = (
                self.isilon_session_cache_path or ".isilon_cache/cache.json"
            )
        else:
            self.isilon_session_cache_path = None
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
    isilon_session_cache_mode: Literal["none", "file", "redis"] | None = None
    isilon_session_cache_path: str | None = Field(default=None, max_length=1024)
    storage_type: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    limit: Optional[float] = None
    used: Optional[float] = None
    use_ratio: Optional[float] = None

    @model_validator(mode="after")
    def disable_tls_verification_for_http(self):
        for field in ("protocol", "tls_verify", "isilon_session_cache_mode"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
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
