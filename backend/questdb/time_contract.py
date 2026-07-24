# -*- coding: utf-8 -*-
"""Mandatory timestamp contract for every QuestDB designated timestamp table."""

from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from utils.datetime_utils import UTC, to_questdb_utc_naive


QUESTDB_TIME_CONTRACTS: Mapping[str, str] = MappingProxyType(
    {
        "aggregate_storage_usages": "updated_at",
        "group_storage_usages": "updated_at",
        "project_storage_usages": "updated_at",
        "qtree_storage_usages": "updated_at",
        "storage_cluster_storage_usages": "updated_at",
        "storage_usages": "updated_at",
        "volume_storage_usages": "updated_at",
        "storage_performance_metrics": "collected_at",
        "user_storage_usages": "updated_at",
    }
)


def questdb_write_timestamp(table_name: str, value: datetime) -> datetime:
    """Convert an aware UTC instant to QuestDB's UTC-naive driver value."""
    if table_name not in QUESTDB_TIME_CONTRACTS:
        raise ValueError(
            f"unregistered QuestDB timestamp table: {table_name!r}; "
            "add it to QUESTDB_TIME_CONTRACTS before writing"
        )
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("QuestDB timestamps must be aware UTC instants")
    return to_questdb_utc_naive(value)
