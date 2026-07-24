# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from schemas import usersSchema


ProjectRole = Literal["reader", "editor", "project_admin"]
AssignableProjectRole = Literal["reader", "editor"]


from schemas.base import UTCBaseModel as BaseModel


class ProjectMembershipCreate(BaseModel):
    user_id: int
    role: ProjectRole


class ProjectMembershipUpdate(BaseModel):
    role: ProjectRole


class ProjectMembershipOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: ProjectRole
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime
    user: usersSchema.OnlyUser | None = None

    model_config = ConfigDict(from_attributes=True)
