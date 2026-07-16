# -*- coding: utf-8 -*-
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


_SPACE_MULTIPLIERS = {"GiB": 1024 ** 3, "TiB": 1024 ** 4}
_GRACE_MULTIPLIERS = {"minutes": 60, "hours": 3600, "days": 86400}


class QuotaAdjustmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    hard_limit: float = Field(gt=0)
    soft_limit: float | None = Field(default=None, gt=0)
    unit: Literal["GiB", "TiB"]
    soft_grace: int | None = Field(default=None, gt=0)
    soft_grace_unit: Literal["minutes", "hours", "days"] | None = None

    @model_validator(mode="after")
    def validate_limits(self):
        if self.soft_limit is not None and self.soft_limit >= self.hard_limit:
            raise ValueError("soft_limit must be less than hard_limit")
        if (self.soft_grace is None) != (self.soft_grace_unit is None):
            raise ValueError("soft_grace and soft_grace_unit must be provided together")
        if self.soft_limit is None and self.soft_grace is not None:
            raise ValueError("soft_grace requires soft_limit")
        return self

    @computed_field
    @property
    def hard_limit_bytes(self) -> float:
        return self.hard_limit * _SPACE_MULTIPLIERS[self.unit]

    @computed_field
    @property
    def soft_limit_bytes(self) -> float | None:
        return (
            self.soft_limit * _SPACE_MULTIPLIERS[self.unit]
            if self.soft_limit is not None
            else None
        )

    @computed_field
    @property
    def soft_grace_seconds(self) -> int | None:
        return (
            self.soft_grace * _GRACE_MULTIPLIERS[self.soft_grace_unit]
            if self.soft_grace is not None
            else None
        )

    @property
    def hard_limit_gib(self) -> float:
        return self.hard_limit_bytes / _SPACE_MULTIPLIERS["GiB"]

    @property
    def soft_limit_gib(self) -> float | None:
        return (
            self.soft_limit_bytes / _SPACE_MULTIPLIERS["GiB"]
            if self.soft_limit_bytes is not None
            else None
        )


class QuotaAdjustmentResponse(BaseModel):
    id: int
    resource_type: Literal["group", "storage_usage"]
    storage_type: Literal["netapp", "isilon"]
    hard_limit: float
    soft_limit: float | None = None
    unit: Literal["GiB"] = "GiB"
    soft_grace_seconds: int | None = None
