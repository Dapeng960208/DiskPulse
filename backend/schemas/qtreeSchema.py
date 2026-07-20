# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from schemas.volumeSchema import VolumeBase,VolumeName
from schemas.capacitySchema import CapacityResponseBase
from schemas.storageClusterSchema import StorageCluster

class QtreeVolume(CapacityResponseBase):
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

    model_config = ConfigDict(from_attributes=True)


class QtreeCreate(QtreeBase):
    pass


class QtreeUpdate(QtreeBase):
    pass


class Qtree(CapacityResponseBase, QtreeBase):
    id: int
    volume: VolumeBase
    storage_cluster: StorageCluster | None = None

    model_config = ConfigDict(from_attributes=True)


class QtreeForGroup(BaseModel):
    name: str
    volume: VolumeName
    model_config = ConfigDict(from_attributes=True)

Qtree.model_rebuild()
