# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from schemas.capacitySchema import CapacityResponseBase
from schemas.storageClusterSchema import StorageCluster


class AggregateBase(BaseModel):
    name: str
    limit: float
    used: float
    use_ratio: float
    updated_at: datetime
    storage_cluster_id: Optional[int] = None


class AggregateCreate(AggregateBase):
    pass


class AggregateUpdate(AggregateBase):
    pass


class Aggregate(CapacityResponseBase, AggregateBase):
    id: int
    storage_cluster: StorageCluster|None = None

    model_config = ConfigDict(from_attributes=True)
