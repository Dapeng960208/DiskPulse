# -*- coding: utf-8 -*-
from typing import Literal

from pydantic import BaseModel


TrendIndicator = Literal["used", "use_ratio", "alert_ratio"]
StorageUsageTrendIndicator = Literal["used", "use_ratio", "alert_ratio", "file_used"]


class StorageTrendThresholds(BaseModel):
    important: int
    serious: int
    emergency: int


class StorageTrendMeta(BaseModel):
    quota_basis: Literal["hard", "soft"]
    rule_source: Literal["system", "project", "group"]
    thresholds: StorageTrendThresholds
    quota_limit_gb: float | None = None
    ratio_indicator: Literal["used_ratio", "soft_use_ratio"]
