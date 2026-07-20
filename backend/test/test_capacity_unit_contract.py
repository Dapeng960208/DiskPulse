# -*- coding: utf-8 -*-
from datetime import datetime

from schemas.capacitySchema import format_capacity
from schemas.forecastIncidentSchema import ForecastOut
from schemas.largeFileSchema import LargeFileList
from schemas.volumeSchema import Volume


def test_capacity_formatter_uses_explicit_binary_units_at_strict_thresholds():
    assert format_capacity(0.5).model_dump() == {"value": 512, "unit": "MB"}
    assert format_capacity(1024).model_dump() == {"value": 1024, "unit": "GB"}
    assert format_capacity(1024.5).model_dump() == {"value": 1.0, "unit": "TB"}
    assert format_capacity(1024 * 1024).model_dump() == {"value": 1024, "unit": "TB"}
    assert format_capacity(1024 * 1024 + 1024).model_dump() == {"value": 1.0, "unit": "PB"}


def test_storage_resource_response_adds_per_field_capacity_display_values():
    volume = Volume.model_validate(
        {
            "id": 1,
            "name": "volume-a",
            "vserver": "svm-a",
            "aggregate": "aggregate-a",
            "type": "rw",
            "state": "online",
            "limit": 2048,
            "soft_limit": 512,
            "used": 0.5,
            "allocated": 1024 * 1024 + 1024,
            "updated_at": datetime(2026, 7, 20, 10, 0, 0),
        }
    )

    assert volume.capacity == {
        "limit": {"value": 2.0, "unit": "TB"},
        "soft_limit": {"value": 512, "unit": "GB"},
        "used": {"value": 512, "unit": "MB"},
        "allocated": {"value": 1.0, "unit": "PB"},
    }


def test_storage_cluster_capacity_change_returns_tb_curve_with_display_units(monkeypatch):
    from services import storageHealthAnalyticsService

    monkeypatch.setattr(
        storageHealthAnalyticsService.storageHealthAnalyticsCrud,
        "get_capacity_boundaries",
        lambda *_args: (1024, 2048),
    )
    monkeypatch.setattr(
        storageHealthAnalyticsService.storageHealthAnalyticsCrud,
        "get_capacity_points",
        lambda *_args: [{"updated_at": datetime(2026, 7, 20, 10), "used": 1024}],
    )

    result = storageHealthAnalyticsService.get_capacity_change(
        None, 1, datetime(2026, 7, 20), datetime(2026, 7, 21)
    )

    assert result["data_unit"] == "TB"
    assert result["start_used"] == 1.0
    assert result["data"][0]["used"] == 1.0
    assert result["capacity"]["end_used"] == {"value": 2, "unit": "TB"}
    assert result["data"][0]["capacity"]["used"] == {"value": 1024, "unit": "GB"}


def test_forecast_and_large_file_responses_include_capacity_units():
    forecast = ForecastOut.model_validate({
        "id": 1,
        "asset_type": "group",
        "asset_id": "1",
        "storage_cluster_id": 1,
        "project_id": 1,
        "vendor": "diskpulse",
        "display_name": "group-a",
        "training_start": datetime(2026, 7, 1),
        "training_end": datetime(2026, 7, 20),
        "hard_limit": 2048,
        "curve": [{"observed_at": datetime(2026, 7, 21), "p10": 0.5, "p50": 2048, "p90": 1024}],
        "exhaustion_dates": {},
        "algorithm_version": "baseline",
        "input_quality": {},
        "backtest_mape": None,
        "created_at": datetime(2026, 7, 20),
    })
    assert forecast.data_unit == "GB"
    assert forecast.capacity["hard_limit"] == {"value": 2, "unit": "TB"}
    assert forecast.curve[0].capacity["p10"] == {"value": 512, "unit": "MB"}

    large_file = LargeFileList.model_validate({
        "user_id": 1, "group_id": 1, "linux_path": "/data/big", "size": 2048,
        "file_type": "data", "updated_at": datetime(2026, 7, 20), "created_at": datetime(2026, 7, 20),
        "user": {"id": 1},
        "group": {"name": "group-a"},
    })
    assert large_file.capacity["size"] == {"value": 2, "unit": "TB"}
