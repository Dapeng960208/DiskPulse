# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


SYSTEM_TIMEZONE = ZoneInfo("Asia/Shanghai")


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
