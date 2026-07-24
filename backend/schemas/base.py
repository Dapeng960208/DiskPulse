# -*- coding: utf-8 -*-
"""Shared schema defaults for the public API contract."""

from datetime import datetime

from pydantic import BaseModel, field_serializer

from utils.datetime_utils import to_utc_z


class UTCBaseModel(BaseModel):
    """Serialize all schema datetime fields as strict RFC 3339 UTC values."""

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_datetime_fields(self, value):
        return to_utc_z(value) if isinstance(value, datetime) else value
