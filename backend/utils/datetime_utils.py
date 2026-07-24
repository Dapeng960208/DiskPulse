# -*- coding: utf-8 -*-
"""UTC time-boundary helpers used by persistence, query, and API code."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SYSTEM_TIMEZONE = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc


def utc_now() -> datetime:
    """Return the only clock value allowed for persisted business instants."""
    return datetime.now(UTC)


def _datetime_value(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("timestamp must be an ISO-8601 datetime") from error
    raise TypeError("timestamp must be a datetime or ISO-8601 string")


def normalize_utc(value: datetime | str) -> datetime:
    """Require an aware instant and normalize it to aware UTC."""
    parsed = _datetime_value(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def parse_source_datetime(value: datetime | str, source_time_zone: str) -> datetime:
    """Convert a vendor wall-time value using its explicit IANA source timezone."""
    try:
        source_timezone = ZoneInfo(source_time_zone)
    except (TypeError, ZoneInfoNotFoundError) as error:
        raise ValueError("source_time_zone must be a valid IANA timezone") from error

    parsed = _datetime_value(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=source_timezone)
    return parsed.astimezone(UTC)


def format_for_user_time_zone(
    value: datetime,
    time_zone: str | None,
    *,
    format_string: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """Format an instant for a persisted user IANA timezone at the presentation boundary."""
    try:
        user_timezone = ZoneInfo(time_zone or SYSTEM_TIMEZONE.key)
    except ZoneInfoNotFoundError:
        user_timezone = SYSTEM_TIMEZONE
    return normalize_utc(value).astimezone(user_timezone).strftime(format_string)


def to_system_local_naive(value: datetime) -> datetime:
    """Legacy helper for non-persistent wall-time-only display values."""
    if value.tzinfo is None:
        return value
    return value.astimezone(SYSTEM_TIMEZONE).replace(tzinfo=None)


def to_utc_z(value: datetime | str) -> str:
    """Serialize an aware instant as UTC RFC 3339 seconds."""
    return normalize_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def to_questdb_utc_naive(value: datetime | str) -> datetime:
    """Convert an aware instant to QuestDB driver's UTC-naive representation."""
    return normalize_utc(value).replace(tzinfo=None)


def from_questdb_utc(value: datetime | str) -> datetime:
    """Interpret a QuestDB driver value as an aware UTC instant."""
    parsed = _datetime_value(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def questdb_to_system_local_naive(value: datetime | str) -> datetime:
    """Compatibility helper; API code must return ``from_questdb_utc`` instead."""
    return from_questdb_utc(value).astimezone(SYSTEM_TIMEZONE).replace(tzinfo=None)
