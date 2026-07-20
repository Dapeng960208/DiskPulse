# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

from utils.datetime_utils import to_system_local_naive, to_utc_z


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


def test_utc_z_interprets_naive_values_in_diskpulse_timezone():
    assert to_utc_z(datetime(2026, 7, 15, 10, 0)) == "2026-07-15T02:00:00Z"


def test_utc_z_preserves_the_instant_of_aware_values():
    assert to_utc_z(
        datetime(2026, 7, 15, 10, 0, tzinfo=timezone(timedelta(hours=8)))
    ) == "2026-07-15T02:00:00Z"
