# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Annotated, List, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StrictBool,
    StringConstraints,
    field_serializer,
)
from schemas.capacitySchema import CapacityResponseBase


UserType = Literal[0, 1, 2]
RdUsername = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class UserBase(BaseModel):
    iam_id: int | None = None
    avatar_url: str | None = None
    username: str | None = None
    rd_username: str | None = None
    email: str | None = None
    department: str | None = None
    is_alert: bool | None = True
    user_type: int | None = 2
    storage_used: float | None = 0
    quit_days: int | None = 0
    updated_at: datetime | None = Field(default_factory=datetime.now)

class OnlyUser(BaseModel):
    id: int
    username: str | None = None
    rd_username: str | None = None
    department: str | None = None
    avatar_url: str | None = None
    iam_id: int | None = None
    user_type: int | None = 2
    quit_days: int | None = 0

    model_config = ConfigDict(from_attributes=True)


class User(CapacityResponseBase, UserBase):
    id: int

    user_group_ids: List[int] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("updated_at", when_used="json")
    def serialize_updated_at(self, value: datetime | None) -> str | None:
        return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rd_username: RdUsername
    username: str | None = None
    email: EmailStr | None = None
    department: str | None = None
    user_type: UserType = 2
    is_alert: StrictBool = True


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = None
    email: EmailStr | None = None
    department: str | None = None
    user_type: UserType = 2
    is_alert: StrictBool = True


class UserSyncResult(BaseModel):
    ldap_total: int = Field(ge=0)
    created: int = Field(ge=0)
    updated: int = Field(ge=0)
    reactivated: int = Field(ge=0)
    marked_inactive: int = Field(ge=0)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


class UserId(BaseModel):
    id: int

    model_config = ConfigDict(from_attributes=True)




class UsersIds(BaseModel):
    ids: List[int] = Field(default_factory=list)
