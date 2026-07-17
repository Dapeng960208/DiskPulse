# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


AuditPhase = Literal["attempt", "result"]
AuditOutcome = Literal["success", "denied", "failure"]


class AuditEventOut(BaseModel):
    id: str
    operation_id: str
    phase: AuditPhase
    occurred_at: datetime
    actor_type: str
    actor_user_id: int | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    project_id: int | None = None
    outcome: AuditOutcome
    reason_code: str | None = None
    before_summary: Any | None = None
    after_summary: Any | None = None
    metadata: Any | None = Field(
        default=None,
        validation_alias=AliasChoices("event_metadata", "metadata"),
        serialization_alias="metadata",
    )
    request_id: str
    trace_id: str

    model_config = ConfigDict(from_attributes=True)


class AuditEventPage(BaseModel):
    content: list[AuditEventOut]
    total: int
