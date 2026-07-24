# -*- coding: utf-8 -*-
from typing import List, Dict
from typing import TypeVar, Generic

from pydantic import BaseModel

from schemas.storageTrendSchema import StorageTrendMeta

T = TypeVar('T')


from schemas.base import UTCBaseModel as BaseModel


class ResponseModel(BaseModel, Generic[T]):
    content: List[T]
    total: int


class ResponseResourceModel(BaseModel):
    data: Dict | List
    avg: Dict | None = None
    tree: List | None = None
    data_unit: str | None = None


class ResponseSummary(BaseModel, Generic[T]):
    info: T | None = None
    status_summary: Dict
    alloc_memory_summary: List[Dict]
    host_summary: List[Dict]
    queue_summary: List[Dict]


class ResponseResourceSummaryModel(BaseModel, Generic[T]):
    info: T | None = None
    projects_resource_summary: Dict | None = None
    hosts_summary: Dict | None = None
    hosts_status: Dict | None = None
    tools_summary: List[Dict] | None = None
    days_summary: List[List] | None = None
    project_jobs_summary: List | None = None


class ResponseStorageUsageModel(BaseModel, Generic[T]):
    info: T | None = None
    data: List = None
    trend_meta: StorageTrendMeta | None = None
    data_unit: str | None = None


class ResponseSummaryModel(BaseModel):
    data: Dict | List


class ResponseReport(BaseModel):
    data: List
