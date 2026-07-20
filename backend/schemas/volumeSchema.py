# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Literal, Optional
from schemas.capacitySchema import CapacityResponseBase
from schemas.storageClusterSchema import StorageCluster

class VolumeName(BaseModel):
    name: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    performance_object_id: str | None = None
    updated_at: datetime
    storage_cluster_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class VolumeCreate(VolumeBase):
    pass


class VolumeUpdate(VolumeBase):
    pass


class Volume(CapacityResponseBase, VolumeBase):
    id: int
    storage_cluster: Optional[StorageCluster] = None

    model_config = ConfigDict(from_attributes=True)

Volume.model_rebuild()


class VolumeMonitoringBinding(BaseModel):
    group_id: int
    group_name: str
    project_id: int
    project_name: str
    linux_path: str | None = None


class VolumePerformanceSeries(BaseModel):
    metric: str
    unit: str
    data: list[list]
    status: str
    match_source: str


class VolumeMonitoring(BaseModel):
    info: Volume
    binding: VolumeMonitoringBinding | None = None
    capacity: list[list]
    capacity_unit: Literal["TB"] = "TB"
    performance: list[VolumePerformanceSeries]


class VolumeMonitoringToolInfo(BaseModel):
    id: int
    name: str
    storage_cluster_id: int | None = None


class VolumeMonitoringToolBinding(BaseModel):
    group_id: int
    group_name: str
    project_id: int
    project_name: str


class VolumeMonitoringToolOut(BaseModel):
    info: VolumeMonitoringToolInfo
    binding: VolumeMonitoringToolBinding | None = None
    capacity: list[list]
    capacity_unit: Literal["TB"] = "TB"
    performance: list[VolumePerformanceSeries]
