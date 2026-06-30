# -*- coding: utf-8 -*-
from typing import Any

from pydantic import BaseModel, Field, computed_field

from schemas import usersSchema


class ProjectBaseInfo(BaseModel):
    id: int
    name: str
    ncpus: int | None = 72
    max_jobs: int | None = 0
    cpuf: float | None = None
    max_mem: float | None = None
    limit: float | None = None
    soft_limit: float | None = None
    used: float | None = None
    use_ratio: float | None = None
    soft_use_ratio: float | None = None
    is_common: bool | None = False
    status: int | None = 1
    project_process_code: str | None = None

    class Config:
        from_attributes = True


class ProjectBase(ProjectBaseInfo):
    mem: float | None = None
    run_jobs: int | None = 0
    ssusp_jobs: int | None = 0
    ususp_jobs: int | None = 0
    pend_jobs: int | None = 0
    slot: float | None = None
    mem_reserved: float | None = None
    slot_reserved: float | None = None
    recipients: str | None = None
    is_alert: bool | None = False
    descriptions: str | None = None
    in_charge_user_id: int | None = None
    in_charge_user: usersSchema.OnlyUser | None = None
    pt_user_id: int | None = None
    pt_user: usersSchema.OnlyUser | None = None

    @computed_field
    def recipient_ids(self) -> list[int]:
        return list(map(int, self.recipients.split())) if self.recipients else []


class Project(ProjectBase):
    id: int

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    recipient_ids: list[int] = Field(default_factory=list)
    is_alert: bool | None = False
    descriptions: str | None = None
    name: str
    in_charge_user_id: int | None = None
    pt_user_id: int | None = None
    is_common: bool | None = False
    status: int | None = 1
    project_process_code: str | None = None


class ProjectResource(Project):
    project_summary: dict[str, Any] = Field(default_factory=dict)
    hosts_summary: dict[str, Any] = Field(default_factory=dict)
