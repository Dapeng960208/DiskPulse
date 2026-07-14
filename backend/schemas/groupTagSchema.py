# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict, Field, field_validator


class GroupTagWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=128)

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value:
            raise ValueError("name must not be blank")
        return value


class GroupTag(GroupTagWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int


class GroupTagPage(BaseModel):
    content: list[GroupTag]
    total: int
