# -*- coding: utf-8 -*-
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StorageClusterBase(BaseModel):
    name: str
    storage_type: str  # 'netapp' or 'isilon'
    storage_host: str | None = None
    storage_port: int | None = 22
    storage_user: str | None = None
    description: Optional[str] = None
    is_active: bool = True
    limit: Optional[float] = None


class StorageClusterCreate(StorageClusterBase):
    storage_password: str | None = None


class StorageClusterUpdate(BaseModel):
    name: Optional[str] = None
    storage_host: str | None = None
    storage_port: int | None = 22
    storage_user: str | None = None
    storage_password: str | None = None
    storage_type: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    limit: Optional[float] = None
    used: Optional[float] = None
    use_ratio: Optional[float] = None


class StorageCluster(StorageClusterBase):
    id: int
    used: Optional[float] = None
    use_ratio: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
