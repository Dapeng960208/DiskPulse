# -*- coding: utf-8 -*-
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from schemas.storageClusterSchema import StorageCluster

class VolumeName(BaseModel):
    name: str
    updated_at: datetime

    class Config:
        from_attributes = True


class VolumeBase(BaseModel):
    name: str
    vserver: str
    aggregate: str
    type: str
    state: str
    limit: float | None = None
    soft_limit: float | None = None
    used: float | None = None
    use_ratio: float | None = None
    soft_use_ratio: float | None = None
    allocated: float | None = None
    updated_at: datetime
    storage_cluster_id: Optional[int] = None

    class Config:
        from_attributes = True


class VolumeCreate(VolumeBase):
    pass


class VolumeUpdate(VolumeBase):
    pass


class Volume(VolumeBase):
    id: int
    storage_cluster: Optional[StorageCluster] = None

    class Config:
        from_attributes = True

Volume.model_rebuild()
