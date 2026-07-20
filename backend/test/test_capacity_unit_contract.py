# -*- coding: utf-8 -*-
from datetime import datetime

from schemas.capacitySchema import format_capacity
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
