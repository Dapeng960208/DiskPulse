# -*- coding: utf-8 -*-
"""Mandatory timestamp contract for every QuestDB designated timestamp table."""

from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from utils.datetime_utils import to_questdb_utc_naive


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


def questdb_write_timestamp(table_name: str, value: datetime | str) -> datetime:
    """Normalize a registered table's designated timestamp to UTC naive."""
    if table_name not in QUESTDB_TIME_CONTRACTS:
        raise ValueError(
            f"unregistered QuestDB timestamp table: {table_name!r}; "
            "add it to QUESTDB_TIME_CONTRACTS before writing"
        )
    return to_questdb_utc_naive(value)
