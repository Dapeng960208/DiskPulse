# -*- coding: utf-8 -*-
from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field
from schemas.capacitySchema import CapacityResponseBase


class AssetRefOut(BaseModel):
    asset_type: str
    asset_id: str
    storage_cluster_id: int | None
    project_id: int | None
    vendor: str
    display_name: str


class ForecastCurvePoint(CapacityResponseBase):
    capacity_field_names: ClassVar[tuple[str, ...]] = ("p10", "p50", "p90")

    observed_at: datetime
    p10: float
    p50: float
    p90: float


class ForecastOut(CapacityResponseBase, AssetRefOut):
    model_config = ConfigDict(from_attributes=True)

    capacity_field_names: ClassVar[tuple[str, ...]] = ("hard_limit",)

    id: int
    training_start: datetime
    training_end: datetime
    hard_limit: float
    curve: list[ForecastCurvePoint]
    data_unit: Literal["GB"] = "GB"
    exhaustion_dates: dict
    algorithm_version: str
    input_quality: dict
    backtest_mape: float | None
    created_at: datetime


class AnomalyOut(AssetRefOut):
    model_config = ConfigDict(from_attributes=True)

    id: int
    metric: str
    observed_at: datetime
    observed_value: float
    seasonal_baseline: float
    mad: float
    robust_z_score: float
    severity: str
    evidence_window_start: datetime
    evidence_window_end: datetime
    algorithm_version: str


class IncidentOut(AssetRefOut):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    severity: str
    status: str
    assigned_user_id: int | None
    opened_at: datetime
    last_evidence_at: datetime
    resolved_at: datetime | None
    silenced_until: datetime | None
    created_at: datetime
    updated_at: datetime
    capabilities: dict[str, bool] = Field(default_factory=dict)


class IncidentEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    source_ref: str
    evidence_type: str
    observed_at: datetime
    data_gaps: list[str]
    presentation: "IncidentEvidencePresentationOut"


class IncidentEvidencePresentationOut(BaseModel):
    group_key: str
    group_label: str
    title: str
    summary: str
    scope_label: str
    technical_ref: str


class IncidentTimelineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    actor_user_id: int | None
    from_status: str | None
    to_status: str | None
    comment: str | None
    occurred_at: datetime
    presentation: "IncidentTimelinePresentationOut"


class IncidentTimelinePresentationOut(BaseModel):
    action_label: str
    summary: str
    actor_label: str


class DiagnosisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    algorithm_version: str
    candidates: list[dict]
    confidence: str
    evidence_ids: list[str]
    data_gaps: list[str]
    created_at: datetime


class DiagnosisToolOut(BaseModel):
    """Minimal, safe AI-tool payload; it intentionally excludes raw evidence payloads."""

    model_config = ConfigDict(from_attributes=True)

    incident_id: int
    algorithm_version: str
    candidates: list[dict]
    confidence: str
    evidence_ids: list[str]
    data_gaps: list[str]


class IncidentDetailOut(IncidentOut):
    evidence: list[IncidentEvidenceOut] = Field(default_factory=list)
    timeline: list[IncidentTimelineOut] = Field(default_factory=list)
    diagnosis: DiagnosisOut | None = None


class IncidentPatch(BaseModel):
    status: Literal["acknowledged", "investigating", "mitigated", "resolved"] | None = None
    severity: Literal["warning", "critical"] | None = None
    claim: bool | None = None
    silenced_until: datetime | None = None
    silence_reason: str | None = Field(default=None, max_length=500)


class IncidentCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MaintenanceWindowCreate(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    storage_cluster_id: int | None = Field(default=None, ge=1)
    asset_type: str | None = Field(default=None, max_length=32)
    asset_id: str | None = Field(default=None, max_length=128)
    starts_at: datetime
    ends_at: datetime
    reason: str = Field(min_length=1, max_length=500)


class ForecastPage(BaseModel):
    content: list[ForecastOut]
    total: int


class AnomalyPage(BaseModel):
    content: list[AnomalyOut]
    total: int


class IncidentPage(BaseModel):
    content: list[IncidentOut]
    total: int
