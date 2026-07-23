# -*- coding: utf-8 -*-
from argparse import Namespace

import pytest

from scripts.repair_questdb_timestamps import (
    TABLES,
    build_audit_statements,
    build_create_statement,
    build_copy_statement,
    build_repair_table_names,
    validate_apply_args,
)


def test_repair_registry_covers_every_production_questdb_timestamp_table():
    assert {table.name for table in TABLES} == {
        "storage_cluster_storage_usages",
        "aggregate_storage_usages",
        "volume_storage_usages",
        "qtree_storage_usages",
        "project_storage_usages",
        "group_storage_usages",
        "storage_usages",
        "user_storage_usages",
        "storage_performance_metrics",
    }


def test_repair_sql_rebuilds_designated_timestamp_and_preserves_performance_ttl():
    table = next(item for item in TABLES if item.name == "storage_performance_metrics")

    create_sql = build_create_statement(table, "storage_performance_metrics__utc_repair")
    copy_sql = build_copy_statement(
        table,
        source_name=table.name,
        target_name="storage_performance_metrics__utc_repair",
    )

    assert "TIMESTAMP(collected_at) PARTITION BY DAY TTL 180 DAYS WAL" in create_sql
    assert "dateadd('h', -8, collected_at) AS collected_at" in copy_sql
    assert "SELECT *" not in copy_sql


def test_capacity_repair_sql_preserves_soft_quota_columns():
    table = next(item for item in TABLES if item.name == "volume_storage_usages")

    copy_sql = build_copy_statement(
        table,
        source_name=table.name,
        target_name="volume_storage_usages__utc_repair",
    )

    assert "soft_limit" in copy_sql
    assert "soft_use_ratio" in copy_sql
    assert "dateadd('h', -8, updated_at) AS updated_at" in copy_sql


def test_numeric_timestamp_suffix_builds_safe_repair_and_backup_table_names():
    repair_name, backup_name = build_repair_table_names(
        "storage_performance_metrics",
        "20260723141953",
    )

    assert repair_name == (
        "storage_performance_metrics__utc_repair_20260723141953"
    )
    assert backup_name == (
        "storage_performance_metrics__local_time_backup_20260723141953"
    )


def test_audit_avoids_postgresql_filter_aggregate_not_supported_by_questdb():
    table = TABLES[0]

    summary_sql, future_sql = build_audit_statements(table)

    assert "FILTER" not in summary_sql.upper()
    assert "FILTER" not in future_sql.upper()
    assert "count()" in future_sql
    assert f"{table.timestamp_column} > :now_utc" in future_sql


@pytest.mark.parametrize(
    ("writes_stopped", "legacy_confirmed"),
    [(False, False), (True, False), (False, True)],
)
def test_apply_requires_both_destructive_safety_confirmations(
    writes_stopped, legacy_confirmed
):
    args = Namespace(
        apply=True,
        confirm_writes_stopped=writes_stopped,
        confirm_all_rows_are_legacy_local_time=legacy_confirmed,
    )

    with pytest.raises(ValueError):
        validate_apply_args(args)


def test_dry_run_does_not_require_destructive_safety_confirmations():
    validate_apply_args(
        Namespace(
            apply=False,
            confirm_writes_stopped=False,
            confirm_all_rows_are_legacy_local_time=False,
        )
    )
