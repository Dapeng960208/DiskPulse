# -*- coding: utf-8 -*-
"""Schema and validation boundary for the background Incident AI agent."""
from typing import Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from crud import incidentAiAgentCrud


IncidentAiClassification = Literal["actionable", "normal_fluctuation", "insufficient_evidence"]
IncidentAiUrgency = Literal["low", "medium", "high", "critical"]
IncidentStatus = Literal["open", "acknowledged", "investigating", "mitigated", "resolved"]


class IncidentAiAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    classification: IncidentAiClassification
    urgency: IncidentAiUrgency
    summary: str = Field(min_length=1, max_length=2000)
    investigation_steps: list[str] = Field(default_factory=list, max_length=8)
    resolution_steps: list[str] = Field(default_factory=list, max_length=8)
    proposed_next_status: IncidentStatus | None = None
    transition_reason: str | None = Field(default=None, max_length=1000)


def validate_agent_assessment(assessment: IncidentAiAssessment, *, current_status: str) -> IncidentAiAssessment:
    """Allow the agent to keep state or take exactly one existing state-machine step."""
    if assessment.proposed_next_status in (None, current_status):
        return assessment
    from services.forecastIncidentService import can_transition_incident

    if not can_transition_incident(current_status, assessment.proposed_next_status):
        raise ValueError("AI 建议的状态必须是当前状态的相邻下一步")
    return assessment


def update_settings(
    db,
    *,
    actor_id: int | None,
    enabled: bool,
    model_ids: list[int],
    iops_absolute_floor: float,
    iops_baseline_ratio: float,
):
    normalized_ids = [int(model_id) for model_id in model_ids]
    if len(normalized_ids) != len(set(normalized_ids)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="AI 模型不能重复选择")
    if enabled and not normalized_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="启用 AI 时必须选择至少一个模型")
    models = incidentAiAgentCrud.list_models_by_ids(db, normalized_ids)
    by_id = {model.id: model for model in models}
    if any(model_id not in by_id or not by_id[model_id].enabled for model_id in normalized_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="只能选择已启用的 AI 模型")
    settings = incidentAiAgentCrud.get_or_create_settings(db)
    settings.enabled = bool(enabled)
    settings.iops_absolute_floor = float(iops_absolute_floor)
    settings.iops_baseline_ratio = float(iops_baseline_ratio)
    settings.updated_by = actor_id
    incidentAiAgentCrud.replace_model_bindings(db, settings=settings, model_ids=normalized_ids)
    db.commit()
    db.refresh(settings)
    return settings
