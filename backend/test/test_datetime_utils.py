# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

import pytest

from utils.datetime_utils import (
    format_for_user_time_zone,
    from_questdb_utc,
    parse_source_datetime,
    questdb_to_system_local_naive,
    to_questdb_utc_naive,
    to_system_local_naive,
    to_utc_z,
    utc_now,
)


def test_system_local_naive_uses_diskpulse_timezone_not_host_timezone():
    assert to_system_local_naive(
        datetime(2026, 7, 15, 2, 0, tzinfo=timezone.utc)
    ) == datetime(2026, 7, 15, 10, 0)
    assert to_system_local_naive(
        datetime(2026, 7, 14, 21, 0, tzinfo=timezone(timedelta(hours=-5)))
    ) == datetime(2026, 7, 15, 10, 0)


def test_system_local_naive_preserves_already_local_wall_time():
    value = datetime(2026, 7, 15, 10, 0)

    assert to_system_local_naive(value) is value


def test_utc_now_is_the_aware_utc_clock_for_persistence():
    now = utc_now()

    assert now.tzinfo is timezone.utc
    assert now.utcoffset() == timedelta(0)


def test_utc_z_rejects_naive_values_at_api_boundaries():
    with pytest.raises(ValueError, match="timezone-aware"):
        to_utc_z(datetime(2026, 7, 15, 10, 0))


def test_utc_z_preserves_the_instant_of_aware_values():
    assert to_utc_z(
        datetime(2026, 7, 15, 10, 0, tzinfo=timezone(timedelta(hours=8)))
    ) == "2026-07-15T02:00:00Z"


def test_source_datetime_requires_the_declared_source_timezone_for_naive_device_values():
    assert parse_source_datetime(
        datetime(2026, 7, 15, 10, 0),
        "Asia/Shanghai",
    ) == datetime(2026, 7, 15, 2, 0, tzinfo=timezone.utc)


def test_user_timezone_formatting_is_only_applied_at_the_presentation_boundary():
    instant = datetime(2026, 7, 15, 2, 0, tzinfo=timezone.utc)

    assert format_for_user_time_zone(instant, "Asia/Shanghai") == "2026-07-15 10:00:00"
    assert format_for_user_time_zone(instant, "America/Los_Angeles") == "2026-07-14 19:00:00"


def test_questdb_write_rejects_naive_values():
    with pytest.raises(ValueError, match="timezone-aware"):
        to_questdb_utc_naive(datetime(2026, 7, 15, 10, 0))


def test_questdb_write_preserves_aware_timestamp_instant():
    assert to_questdb_utc_naive(
        datetime(2026, 7, 15, 10, 0, tzinfo=timezone(timedelta(hours=8)))
    ) == datetime(2026, 7, 15, 2, 0)


def test_questdb_read_interprets_driver_naive_timestamp_as_utc():
    assert from_questdb_utc(datetime(2026, 7, 15, 2, 0)) == datetime(
        2026, 7, 15, 2, 0, tzinfo=timezone.utc
    )


def test_questdb_read_converts_utc_timestamp_to_system_wall_time():
    assert questdb_to_system_local_naive(datetime(2026, 7, 15, 2, 0)) == datetime(
        2026, 7, 15, 10, 0
    )
