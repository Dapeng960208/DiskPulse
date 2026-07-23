# -*- coding: utf-8 -*-
"""Audit and repair legacy Asia/Shanghai wall-clock timestamps in QuestDB.

The historical DiskPulse writers sent timezone-naive Asia/Shanghai values to a
QuestDB connection configured as UTC.  QuestDB designated timestamps cannot be
updated in place, so repair requires rebuilding each table and swapping names.

Audit is the default.  Applying a repair requires collectors to be stopped and
two explicit confirmations.  Original tables are retained as timestamped
backups and are never dropped by this script.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import text

from dependencies import QuestDBSession
from utils.datetime_utils import to_utc_z


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LEGACY_OFFSET = timedelta(hours=8)


@dataclass(frozen=True)
class QuestDBTable:
    name: str
    columns: tuple[tuple[str, str], ...]
    timestamp_column: str
    ttl: str | None = None


TABLES = (
    QuestDBTable(
        "storage_cluster_storage_usages",
        (
            ("storage_cluster_id", "SYMBOL"),
            ("used", "DOUBLE"),
            ("use_ratio", "DOUBLE"),
            ("updated_at", "TIMESTAMP"),
        ),
        "updated_at",
    ),
    QuestDBTable(
        "aggregate_storage_usages",
        (
            ("storage_cluster_id", "SYMBOL"),
            ("aggregate_id", "SYMBOL"),
            ("used", "DOUBLE"),
            ("used_ratio", "DOUBLE"),
            ("updated_at", "TIMESTAMP"),
        ),
        "updated_at",
    ),
    QuestDBTable(
        "volume_storage_usages",
        (
            ("volume_id", "SYMBOL"),
            ("used", "DOUBLE"),
            ("used_ratio", "DOUBLE"),
            ("soft_limit", "DOUBLE"),
            ("soft_use_ratio", "DOUBLE"),
            ("updated_at", "TIMESTAMP"),
        ),
        "updated_at",
    ),
    QuestDBTable(
        "qtree_storage_usages",
        (
            ("qtree_id", "SYMBOL"),
            ("used", "DOUBLE"),
            ("used_ratio", "DOUBLE"),
            ("soft_limit", "DOUBLE"),
            ("soft_use_ratio", "DOUBLE"),
            ("updated_at", "TIMESTAMP"),
        ),
        "updated_at",
    ),
    QuestDBTable(
        "project_storage_usages",
        (
            ("project_id", "SYMBOL"),
            ("used", "DOUBLE"),
            ("used_ratio", "DOUBLE"),
            ("soft_limit", "DOUBLE"),
            ("soft_use_ratio", "DOUBLE"),
            ("updated_at", "TIMESTAMP"),
        ),
        "updated_at",
    ),
    QuestDBTable(
        "group_storage_usages",
        (
            ("group_id", "SYMBOL"),
            ("used", "DOUBLE"),
            ("used_ratio", "DOUBLE"),
            ("soft_limit", "DOUBLE"),
            ("soft_use_ratio", "DOUBLE"),
            ("updated_at", "TIMESTAMP"),
        ),
        "updated_at",
    ),
    QuestDBTable(
        "storage_usages",
        (
            ("storage_usage_id", "SYMBOL"),
            ("user_id", "SYMBOL"),
            ("used", "DOUBLE"),
            ("used_ratio", "DOUBLE"),
            ("file_used", "DOUBLE"),
            ("soft_limit", "DOUBLE"),
            ("soft_use_ratio", "DOUBLE"),
            ("updated_at", "TIMESTAMP"),
        ),
        "updated_at",
    ),
    QuestDBTable(
        "user_storage_usages",
        (
            ("user_id", "SYMBOL"),
            ("limit", "DOUBLE"),
            ("soft_limit", "DOUBLE"),
            ("used", "DOUBLE"),
            ("use_ratio", "DOUBLE"),
            ("soft_use_ratio", "DOUBLE"),
            ("file_used", "DOUBLE"),
            ("updated_at", "TIMESTAMP"),
        ),
        "updated_at",
    ),
    QuestDBTable(
        "storage_performance_metrics",
        (
            ("storage_cluster_id", "SYMBOL"),
            ("vendor", "SYMBOL"),
            ("object_type", "SYMBOL"),
            ("object_id", "SYMBOL"),
            ("object_name", "SYMBOL"),
            ("latency_read", "DOUBLE"),
            ("latency_write", "DOUBLE"),
            ("latency_total", "DOUBLE"),
            ("iops_total", "DOUBLE"),
            ("throughput_total", "DOUBLE"),
            ("collected_at", "TIMESTAMP"),
        ),
        "collected_at",
        ttl="180 DAYS",
    ),
)


def _identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"unsafe QuestDB identifier: {value!r}")
    return value


def build_repair_table_names(table_name: str, suffix: str) -> tuple[str, str]:
    table_name = _identifier(table_name)
    if not suffix:
        raise ValueError("QuestDB repair suffix must not be empty")
    return (
        _identifier(f"{table_name}__utc_repair_{suffix}"),
        _identifier(f"{table_name}__local_time_backup_{suffix}"),
    )


def build_create_statement(table: QuestDBTable, target_name: str) -> str:
    target_name = _identifier(target_name)
    columns = ", ".join(
        f"{_identifier(name)} {column_type}" for name, column_type in table.columns
    )
    ttl = f" TTL {table.ttl}" if table.ttl else ""
    return (
        f"CREATE TABLE {target_name} ({columns}) "
        f"TIMESTAMP({_identifier(table.timestamp_column)}) "
        f"PARTITION BY DAY{ttl} WAL"
    )


def build_copy_statement(
    table: QuestDBTable,
    *,
    source_name: str,
    target_name: str,
) -> str:
    source_name = _identifier(source_name)
    target_name = _identifier(target_name)
    column_names = [_identifier(name) for name, _type in table.columns]
    timestamp_column = _identifier(table.timestamp_column)
    projection = [
        (
            f"dateadd('h', -8, {name}) AS {name}"
            if name == timestamp_column
            else name
        )
        for name in column_names
    ]
    return (
        f"INSERT INTO {target_name} ({', '.join(column_names)}) "
        f"SELECT {', '.join(projection)} FROM {source_name} "
        f"ORDER BY {timestamp_column}"
    )


def build_audit_statements(table: QuestDBTable) -> tuple[str, str]:
    table_name = _identifier(table.name)
    timestamp_column = _identifier(table.timestamp_column)
    return (
        f"SELECT count(), min({timestamp_column}), max({timestamp_column}) "
        f"FROM {table_name}",
        f"SELECT count() FROM {table_name} "
        f"WHERE {timestamp_column} > :now_utc",
    )


def validate_apply_args(args: argparse.Namespace) -> None:
    if not args.apply:
        return
    if not args.confirm_writes_stopped:
        raise ValueError("--apply requires --confirm-writes-stopped")
    if not args.confirm_all_rows_are_legacy_local_time:
        raise ValueError(
            "--apply requires --confirm-all-rows-are-legacy-local-time"
        )


def _audit_table(session, table: QuestDBTable, now_utc: str) -> dict:
    summary_sql, future_sql = build_audit_statements(table)
    row_count, minimum, maximum = session.execute(text(summary_sql)).one()
    future_count = session.execute(
        text(future_sql), {"now_utc": now_utc}
    ).scalar_one()
    return {
        "table": table.name,
        "row_count": int(row_count),
        "minimum": minimum,
        "maximum": maximum,
        "future_count": int(future_count),
    }


def audit_tables(session, tables: Iterable[QuestDBTable]) -> list[dict]:
    now_utc = to_utc_z(datetime.now(timezone.utc))
    return [_audit_table(session, table, now_utc) for table in tables]


def _table_exists(session, table_name: str) -> bool:
    count = session.execute(
        text("SELECT count() FROM tables() WHERE table_name = :table_name"),
        {"table_name": _identifier(table_name)},
    ).scalar_one()
    return bool(count)


def _wait_for_row_count(
    session,
    table_name: str,
    expected_count: int,
    *,
    timeout_seconds: float = 30,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    statement = text(f"SELECT count() FROM {_identifier(table_name)}")
    while time.monotonic() < deadline:
        if int(session.execute(statement).scalar_one()) == expected_count:
            return
        time.sleep(0.5)
    raise TimeoutError(
        f"QuestDB WAL did not materialize {expected_count} rows in {table_name}"
    )


def _verify_shift(
    source_audit: dict,
    repaired_audit: dict,
    *,
    repaired_name: str,
) -> None:
    if repaired_audit["row_count"] != source_audit["row_count"]:
        raise RuntimeError(
            f"row count mismatch for {repaired_name}: "
            f"{repaired_audit['row_count']} != {source_audit['row_count']}"
        )
    for boundary in ("minimum", "maximum"):
        source = source_audit[boundary]
        repaired = repaired_audit[boundary]
        if source is not None and repaired != source - _LEGACY_OFFSET:
            raise RuntimeError(
                f"{boundary} timestamp mismatch for {repaired_name}: "
                f"{repaired!r} != {source - _LEGACY_OFFSET!r}"
            )


def repair_tables(
    session,
    tables: Iterable[QuestDBTable],
    *,
    suffix: str,
) -> list[dict]:
    """Rebuild and swap tables, preserving each original as a backup."""
    results = []
    now_utc = to_utc_z(datetime.now(timezone.utc))
    for table in tables:
        repair_name, backup_name = build_repair_table_names(table.name, suffix)
        if _table_exists(session, repair_name) or _table_exists(session, backup_name):
            raise RuntimeError(
                f"repair or backup table already exists for {table.name}: {suffix}"
            )

        source_audit = _audit_table(session, table, now_utc)
        session.execute(text(build_create_statement(table, repair_name)))
        session.commit()
        session.execute(
            text(
                build_copy_statement(
                    table,
                    source_name=table.name,
                    target_name=repair_name,
                )
            )
        )
        session.commit()
        _wait_for_row_count(session, repair_name, source_audit["row_count"])

        repair_spec = QuestDBTable(
            repair_name,
            table.columns,
            table.timestamp_column,
            table.ttl,
        )
        repaired_audit = _audit_table(session, repair_spec, now_utc)
        _verify_shift(source_audit, repaired_audit, repaired_name=repair_name)

        session.execute(
            text(f"RENAME TABLE {_identifier(table.name)} TO {_identifier(backup_name)}")
        )
        session.commit()
        session.execute(
            text(f"RENAME TABLE {_identifier(repair_name)} TO {_identifier(table.name)}")
        )
        session.commit()
        results.append(
            {
                **repaired_audit,
                "table": table.name,
                "backup_table": backup_name,
            }
        )
    return results


def _selected_tables(names: list[str] | None) -> tuple[QuestDBTable, ...]:
    if not names:
        return TABLES
    by_name = {table.name: table for table in TABLES}
    unknown = sorted(set(names) - set(by_name))
    if unknown:
        raise ValueError(f"unknown QuestDB tables: {', '.join(unknown)}")
    return tuple(by_name[name] for name in names)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="rebuild and swap selected tables; default is read-only audit",
    )
    parser.add_argument(
        "--confirm-writes-stopped",
        action="store_true",
        help="confirm all QuestDB-producing workers are stopped",
    )
    parser.add_argument(
        "--confirm-all-rows-are-legacy-local-time",
        action="store_true",
        help="confirm selected tables contain no rows written by the corrected UTC writers",
    )
    parser.add_argument(
        "--table",
        dest="tables",
        action="append",
        help="repair one registered table; repeat to select multiple (default: all)",
    )
    parser.add_argument(
        "--suffix",
        default=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        help="safe identifier suffix used for repair and backup table names",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    validate_apply_args(args)
    tables = _selected_tables(args.tables)
    with QuestDBSession() as session:
        result = (
            repair_tables(session, tables, suffix=args.suffix)
            if args.apply
            else audit_tables(session, tables)
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
