# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


SYSTEM_TIMEZONE = ZoneInfo("Asia/Shanghai")


def _datetime_value(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError("timestamp must be a datetime or ISO-8601 string")


def to_system_local_naive(value: datetime) -> datetime:
    """Convert an aware instant to DiskPulse local wall time for legacy columns."""
    if value.tzinfo is None:
        return value
    return value.astimezone(SYSTEM_TIMEZONE).replace(tzinfo=None)


def to_utc_z(value: datetime) -> str:
    """Serialize local wall time or an aware instant as UTC RFC 3339 seconds."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=SYSTEM_TIMEZONE)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def to_questdb_utc_naive(value: datetime | str) -> datetime:
    """Convert a DiskPulse timestamp to the UTC-naive value expected by QuestDB."""
    value = _datetime_value(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=SYSTEM_TIMEZONE)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def from_questdb_utc(value: datetime | str) -> datetime:
    """Interpret a QuestDB driver value as a UTC instant."""
    value = _datetime_value(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def questdb_to_system_local_naive(value: datetime | str) -> datetime:
    """Convert a QuestDB UTC timestamp to DiskPulse local wall time for APIs."""
    return from_questdb_utc(value).astimezone(SYSTEM_TIMEZONE).replace(tzinfo=None)
