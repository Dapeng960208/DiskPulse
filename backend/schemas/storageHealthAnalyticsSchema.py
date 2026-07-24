# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AssociationType = Literal[
    "fault_log",
    "performance_anomaly",
    "capacity_threshold",
    "system_activity",
    "telemetry_degradation",
    "unknown",
]


from schemas.base import UTCBaseModel as BaseModel


class VendorEventSemantics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_code: str | None = None
    association_type: AssociationType
    association_type_label: str
    title_zh: str
    description_zh: str
    official_reference_url: str | None = None
    review_status: str | None = None
    recommended_solution_zh: str | None = None


class SystemEventOut(VendorEventSemantics):
    id: int
    source: Literal["netapp", "isilon"]
    fingerprint: str | None = None
    severity: str
    object_id: str
    object_name: str
    object_type: str
    description: str | None = None
    occurred_at: datetime


class SystemEventPage(BaseModel):
    data: list[SystemEventOut]
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class RepeatedFaultOut(VendorEventSemantics):
    source: Literal["netapp", "isilon"]
    fingerprint: str
    sample_event_id: int
    log_excerpt: str | None = None
    count: int = Field(ge=2)
    first_occurred_at: datetime
    last_occurred_at: datetime


class RepeatedFaultList(BaseModel):
    data: list[RepeatedFaultOut]
