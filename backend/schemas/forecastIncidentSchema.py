# -*- coding: utf-8 -*-
from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
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
    ai_urgency: str | None = None
    ai_urgency_reason: str | None = None
    ai_analyzed_at: datetime | None = None
    ai_assessment: "IncidentAiAssessmentOut | None" = None
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
    data_gap_details: list["DataGapDetailOut"] = Field(default_factory=list)
    evidence_summary: "VendorEvidenceSummaryOut | None" = None
    presentation: "IncidentEvidencePresentationOut"


class IncidentEvidencePresentationOut(BaseModel):
    group_key: str
    group_label: str
    title: str
    summary: str
    scope_label: str
    technical_ref: str
    association_type: str | None = None
    association_type_label: str | None = None
    event_code: str | None = None
    log_excerpt: str | None = None
    detail_available: bool = False
    metric_key: str | None = None
    metric_label: str | None = None
    metric_unit: str | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    observed_value: float | None = None
    baseline_value: float | None = None
    reference_lower: float | None = None
    reference_upper: float | None = None
    robust_z_score: float | None = None
    reference_purpose: str
    lookup_hint: str


class DataGapDetailOut(BaseModel):
    code: str
    label: str
    description: str
    impact: str


class VendorEvidenceSummaryOut(BaseModel):
    source_ref: str
    event_code: str
    association_type: str
    association_type_label: str
    title_zh: str
    severity: str


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


class IncidentAiAssessmentOut(BaseModel):
    classification: Literal["actionable", "normal_fluctuation", "insufficient_evidence"]
    urgency: Literal["low", "medium", "high", "critical"]
    summary: str
    evidence_basis: list[str] = Field(default_factory=list)
    investigation_steps: list[str] = Field(default_factory=list)
    resolution_steps: list[str] = Field(default_factory=list)
    proposed_next_status: Literal["open", "acknowledged", "investigating", "mitigated", "resolved"] | None = None
    transition_reason: str | None = None
    model_name: str | None = None
    analyzed_at: datetime | None = None


class IncidentAiSettingsModelOut(BaseModel):
    id: int
    name: str
    provider: str
    model: str


class IncidentAiSettingsOut(BaseModel):
    enabled: bool
    model_ids: list[int] = Field(default_factory=list)
    models: list[IncidentAiSettingsModelOut] = Field(default_factory=list)
    available_models: list[IncidentAiSettingsModelOut] = Field(default_factory=list)
    iops_absolute_floor: float
    iops_baseline_ratio: float
    updated_at: datetime | None = None


class IncidentAiSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    model_ids: list[int] = Field(default_factory=list, max_length=10)
    iops_absolute_floor: float = Field(ge=0, le=1_000_000_000)
    iops_baseline_ratio: float = Field(ge=0, le=1)

    @field_validator("model_ids")
    @classmethod
    def unique_model_ids(cls, value: list[int]) -> list[int]:
        if any(model_id < 1 for model_id in value):
            raise ValueError("model_ids must contain positive identifiers")
        if len(value) != len(set(value)):
            raise ValueError("model_ids must not contain duplicates")
        return value


class DiagnosisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    algorithm_version: str
    candidates: list[dict]
    confidence: str
    evidence_ids: list[str]
    data_gaps: list[str]
    data_gap_details: list[DataGapDetailOut] = Field(default_factory=list)
    evidence_summaries: list[VendorEvidenceSummaryOut] = Field(default_factory=list)
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
    data_gap_details: list[DataGapDetailOut] = Field(default_factory=list)
    evidence_summaries: list[VendorEvidenceSummaryOut] = Field(default_factory=list)


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
