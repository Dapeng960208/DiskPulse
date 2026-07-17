# -*- coding: utf-8 -*-
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class DashboardScope(BaseModel):
    mode: Literal["global", "project"]
    project_id: int | None = None
    project_name: str | None = None
    start_time: datetime
    end_time: datetime
    updated_at: datetime


class DashboardSummary(BaseModel):
    limit_gb: float
    used_gb: float
    available_gb: float
    use_ratio: float
    storage_cluster_count: int
    alert_count: int


class CapacityTrendPoint(BaseModel):
    timestamp: datetime
    used_gb: float


class CapacityItem(BaseModel):
    id: int
    name: str
    limit_gb: float
    used_gb: float
    available_gb: float
    use_ratio: float


class AlertTrendPoint(BaseModel):
    date: date
    count: int


class DashboardSummaryResponse(BaseModel):
    scope: DashboardScope
    summary: DashboardSummary


class TopUser(BaseModel):
    id: int
    name: str
    used_gb: float
