# -*- coding: utf-8 -*-
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StorageAlert(BaseModel):
    id: int
    alert_level: str
    alert_type:str
    updated_at: datetime
    description: Optional[str]
    threshold: int
    avg_use_ratio: float
    related_id: int
    related_type: str
    related_info: Optional[dict] | None = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
        }
