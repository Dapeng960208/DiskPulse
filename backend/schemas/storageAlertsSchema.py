# -*- coding: utf-8 -*-
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StorageAlert(BaseModel):
    id: int
    storage_cluster_id: Optional[int] = None
    source: str = "diskpulse"
    external_event_id: Optional[str] = None
    fingerprint: Optional[str] = None
    severity: str = "info"
    alert_level: str
    alert_type:str
    updated_at: datetime
    description: Optional[str]
    threshold: int
    avg_use_ratio: float
    related_id: Optional[int] = None
    related_type: str
    related_info: Optional[dict] | None = None
    event_type: str = "trigger"
    quota_basis: str = "hard"
    delivery_status: str = "legacy"

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
        }
