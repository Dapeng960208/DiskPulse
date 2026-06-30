# -*- coding: utf-8 -*-
from pydantic import BaseModel, field_validator
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List


class UserBase(BaseModel):
    iam_id: int | None = None
    avatar_url: str | None = None
    username: str | None = None
    rd_username: str | None = None
    email: str | None = None
    department: str | None = None
    is_alert: bool | None = True
    run_jobs: int | None = 0
    ssusp_jobs: int | None = 0
    pend_jobs: int | None = 0
    done_jobs: int | None = 0
    exit_jobs: int | None = 0
    user_type: int | None = 2
    storage_used: float | None = 0
    quit_days: int | None = 0
    updated_at: datetime | None = Field(default_factory=datetime.now)

    @field_validator('run_jobs', 'ssusp_jobs', 'pend_jobs', 'done_jobs', 'exit_jobs', mode='before')
    def set_default_jobs(cls, v):
        return v if v is not None else 0


class OnlyUser(BaseModel):
    id: int
    username: str | None = None
    rd_username: str | None = None
    department: str | None = None
    avatar_url: str | None = None
    iam_id: int | None = None
    user_type: int | None = 2
    quit_days: int | None = 0

    class Config:
        from_attributes = True


class User(UserBase):
    id: int

    user_group_ids: List[int] = []

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
        }


class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    user_type: int | None = 2
    is_alert: bool | None = True


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


class UserId(BaseModel):
    id: int

    class Config:
        from_attributes = True




class UsersIds(BaseModel):
    ids: List[int] = []


class IamUser(BaseModel):
    iam_id: int
    username: str
    rd_username: str | None = None
    department: str | None = None
    avatar_url: str | None = None
    email: str | None = None

    class Config:
        from_attributes = True
