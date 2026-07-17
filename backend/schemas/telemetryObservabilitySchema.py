# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HealthStatus(BaseModel):
    status: Literal["ok", "ready", "degraded", "not_ready"]


class TelemetryCollectionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: UUID
    trace_id: str
    scope_type: Literal["cluster", "scheduler"]
    scope_key: str
    storage_cluster_id: int | None
    component: Literal["capacity", "vendor_events", "performance"]
    outcome: Literal["success", "failed", "skipped"] | None
    data_state: Literal["data", "empty", "unsupported"] | None
    records_written: int | None
    error_code: Literal["vendor_auth", "vendor_timeout", "postgres", "questdb", "unknown"] | None
    started_at: datetime
    finished_at: datetime | None


class TelemetryCollectionRunPage(BaseModel):
    content: list[TelemetryCollectionRunRead]
    total: int
