# -*- coding: utf-8 -*-
import math
from typing import Any, ClassVar, Literal, Mapping

from pydantic import BaseModel, computed_field


CapacityUnit = Literal["MB", "GB", "TB", "PB"]
_GB_PER_TB = 1024
_GB_PER_PB = _GB_PER_TB * _GB_PER_TB


from schemas.base import UTCBaseModel as BaseModel


class CapacityDisplay(BaseModel):
    value: int | float
    unit: CapacityUnit


def _rounded(value: float) -> int | float:
    rounded = round(value, 2)
    return int(rounded) if rounded.is_integer() else rounded


def format_capacity(value: float | int | None) -> CapacityDisplay | None:
    """Convert a GB-based capacity value into its explicit display unit."""
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    magnitude = abs(numeric)
    if magnitude > _GB_PER_PB:
        return CapacityDisplay(value=_rounded(numeric / _GB_PER_PB), unit="PB")
    if magnitude > _GB_PER_TB:
        return CapacityDisplay(value=_rounded(numeric / _GB_PER_TB), unit="TB")
    if magnitude < 1:
        return CapacityDisplay(value=_rounded(numeric * _GB_PER_TB), unit="MB")
    return CapacityDisplay(value=_rounded(numeric), unit="GB")


def format_capacity_fields(values: Mapping[str, Any]) -> dict[str, dict[str, int | float | str]]:
    return {
        name: display.model_dump()
        for name, value in values.items()
        if (display := format_capacity(value)) is not None
    }


class CapacityResponseBase(BaseModel):
    """Adds a display-safe capacity map while preserving raw GB fields."""

    capacity_field_names: ClassVar[tuple[str, ...]] = (
        "limit", "soft_limit", "used", "allocated", "storage_used",
        "limit_gb", "used_gb", "available_gb", "quota_limit_gb", "capacity_delta",
    )

    @computed_field
    @property
    def capacity(self) -> dict[str, dict[str, int | float | str]]:
        return format_capacity_fields({
            field: getattr(self, field)
            for field in self.capacity_field_names
            if hasattr(self, field)
        })
