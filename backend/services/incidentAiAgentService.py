# -*- coding: utf-8 -*-
"""Schema and validation boundary for the background Incident AI agent."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
