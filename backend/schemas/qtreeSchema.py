# -*- coding: utf-8 -*-
from pydantic import BaseModel
from datetime import datetime
from schemas.volumeSchema import VolumeBase,VolumeName
from schemas.storageClusterSchema import StorageCluster

class QtreeVolume(BaseModel):
    name: str
    volume_name: str
    limit: float | None = None
    soft_limit: float | None = None
    used: float | None = None
    use_ratio: float | None = 0
    soft_use_ratio: float | None = None
    style: str
    oplocks: str
    status: str
    updated_at: datetime


class QtreeBase(BaseModel):
    volume_id: int
    name: str
    limit: float | None = None
    soft_limit: float | None = None
    used: float | None = None
    use_ratio: float | None = 0
    soft_use_ratio: float | None = None
    style: str
    oplocks: str
    status: str
    updated_at: datetime
    storage_cluster_id: int | None = None

    class Config:
        from_attributes = True


class QtreeCreate(QtreeBase):
    pass


class QtreeUpdate(QtreeBase):
    pass


class Qtree(QtreeBase):
    id: int
    volume: VolumeBase
    storage_cluster: StorageCluster | None = None

    class Config:
        from_attributes = True


class QtreeForGroup(BaseModel):
    name: str
    volume: VolumeName
    class Config:
        from_attributes = True

Qtree.model_rebuild()
