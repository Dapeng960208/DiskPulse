# -*- coding: utf-8 -*-
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DEFAULT_STORAGE_ALERT_RULE = {
    "quota_basis": "hard",
    "important": {"threshold": 80, "repeat_hours": 24},
    "serious": {"threshold": 90, "repeat_hours": 6},
    "emergency": {"threshold": 95, "repeat_hours": 1},
}


from schemas.base import UTCBaseModel as BaseModel


class StorageAlertLevelRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threshold: int = Field(gt=0, le=100, strict=True)
    repeat_hours: int = Field(gt=0, strict=True)


class StorageAlertRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quota_basis: Literal["hard", "soft"]
    important: StorageAlertLevelRule
    serious: StorageAlertLevelRule
    emergency: StorageAlertLevelRule

    @model_validator(mode="after")
    def validate_thresholds(self):
        thresholds = (
            self.important.threshold,
            self.serious.threshold,
            self.emergency.threshold,
        )
        if not 0 < thresholds[0] < thresholds[1] < thresholds[2] <= 100:
            raise ValueError("thresholds must satisfy 0 < important < serious < emergency <= 100")
        return self
