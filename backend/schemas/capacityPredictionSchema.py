# -*- coding: utf-8 -*-
from datetime import datetime
import math
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from schemas.capacitySchema import CapacityResponseBase


PredictionAssetType = Literal["group", "storage_usage"]


class CapacityPredictionVisibilityOut(BaseModel):
    visible: bool


class CapacityPredictionAccessOut(CapacityPredictionVisibilityOut):
    can_manage_plans: bool = False


class CapacityPredictionRelatedIncidentOut(BaseModel):
    id: int
    category: str
    severity: str
    status: str
    updated_at: datetime
    rca_confidence: str | None = None


class CapacityPredictionSettingsPatch(BaseModel):
    user_visible: bool


class CapacityPredictionCandidateCreate(BaseModel):
    version: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    ai_model_id: int = Field(ge=1)


class CapacityPredictionEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    baseline_mape: float
    candidate_mape: float
    risk_coverage_ok: bool
    window_start: datetime
    window_end: datetime
    created_at: datetime


class CapacityPredictionCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: str
    ai_model_id: int
    enabled: bool
    created_at: datetime
    evaluations: list[CapacityPredictionEvaluationOut] = Field(default_factory=list)
    activation_ready: bool = False
    forecast_count: int = 0
    fallback_count: int = 0
    fallback_reasons: dict[str, int] = Field(default_factory=dict)


class CapacityPredictionPlanCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    effective_at: datetime
    capacity_delta: float = Field(ge=-1_000_000_000, le=1_000_000_000)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("capacity_delta")
    @classmethod
    def validate_capacity_delta(cls, value: float) -> float:
        if not math.isfinite(value) or value == 0:
            raise ValueError("capacity_delta must be finite and non-zero")
        return value


class CapacityPredictionPlanOut(CapacityResponseBase):
    model_config = ConfigDict(from_attributes=True)

    capacity_field_names: ClassVar[tuple[str, ...]] = ("capacity_delta",)

    id: int
    asset_type: PredictionAssetType
    asset_id: str
    project_id: int
    effective_at: datetime
    capacity_delta: float
    reason: str
    created_at: datetime
