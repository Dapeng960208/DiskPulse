# -*- coding: utf-8 -*-
from datetime import datetime
from pydantic import BaseModel, Field, computed_field
from schemas import usersSchema
from typing import List, Dict


class ProjectBaseInfo(BaseModel):
    id: int
    name: str
    ncpus: int | None = 72
    max_jobs: int | None = 0
    cpuf: float | None = None
    max_mem: float | None = None
    limit: float | None = None
    used: float | None = None
    use_ratio: float | None = None
    is_common: bool | None = False
    status: int | None = 1
    project_process_code: str | None = None

    class Config:
        from_attributes = True


class ProjectBase(ProjectBaseInfo):
    mem: float | None = None
    master: bool = False
    max_swp: float | None = None
    resources: str | None = None
    run_jobs: int | None = 0
    ssusp_jobs: int | None = 0
    ususp_jobs: int | None = 0
    pend_jobs: int | None = 0
    rsv: int | None = None
    r15s: float | None = None
    r1m: float | None = None
    r15m: float | None = None
    ut: float | None = None
    pg: float | None = None
    ls: float | None = None
    it: float | None = None
    tmp: float | None = None
    swp: float | None = None
    slot: float | None = None
    sut: float | None = None
    mut: float | None = None
    mem_reserved: float | None = None
    slot_reserved: float | None = None
    recipients: str | None = None
    is_alert: bool | None = False
    descriptions: str | None = None
    in_charge_user_id: int | None = None
    in_charge_user: usersSchema.OnlyUser | None = None
    # 增加pt经理
    pt_user_id: int | None = None
    pt_user: usersSchema.OnlyUser | None = None

    @computed_field
    def recipient_ids(self) -> List[int]:
        return list(map(int, self.recipients.split())) if self.recipients else []


class Project(ProjectBase):
    id: int

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    recipient_ids: list = []
    is_alert: bool | None = False
    descriptions: str | None = None
    name: str
    in_charge_user_id: int | None = None
    pt_user_id: int | None = None
    is_common: bool | None = False
    status: int | None = 1
    project_process_code: str | None = None


class ProjectResource(Project):
    project_summary: Dict = {}
    hosts_summary: Dict = {}
