# -*- coding: utf-8 -*-
import ast
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from questdb.time_contract import (
    QUESTDB_TIME_CONTRACTS,
    questdb_write_timestamp,
)
from scripts.repair_questdb_timestamps import TABLES


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
CREATE_TIMESTAMP_TABLE = re.compile(
    r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"
    r'"?([A-Za-z_][A-Za-z0-9_]*)"?\s*'
    r"\(.*?\)\s*TIMESTAMP\s*"
    r'\(\s*"?([A-Za-z_][A-Za-z0-9_]*)"?\s*\)',
    re.IGNORECASE | re.DOTALL,
)


def _migrated_timestamp_contracts() -> dict[str, str]:
    contracts: dict[str, str] = {}
    for migration in sorted((BACKEND_ROOT / "questdb" / "migrations").glob("*.sql")):
        sql = migration.read_text(encoding="utf-8")
        for table_name, timestamp_column in CREATE_TIMESTAMP_TABLE.findall(sql):
            contracts[table_name] = timestamp_column
    return contracts


def _direct_datetime_utility_bypasses(
    source_paths: list[Path] | None = None,
) -> list[str]:
    violations: list[str] = []
    allowed_paths = {
        BACKEND_ROOT / "utils" / "datetime_utils.py",
        BACKEND_ROOT / "questdb" / "time_contract.py",
    }
    paths = source_paths or list(BACKEND_ROOT.rglob("*.py"))
    for source_path in paths:
        if source_path in allowed_paths or "test" in source_path.parts:
            continue
        try:
            display_path = source_path.relative_to(REPOSITORY_ROOT)
        except ValueError:
            display_path = Path(source_path.name)
        tree = ast.parse(
            source_path.read_text(encoding="utf-8-sig"),
            filename=source_path,
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "utils.datetime_utils":
                if any(alias.name == "to_questdb_utc_naive" for alias in node.names):
                    violations.append(
                        f"{display_path}:{node.lineno}:import"
                    )
            if isinstance(node, ast.Call):
                function = node.func
                if isinstance(function, ast.Name) and function.id == "to_questdb_utc_naive":
                    violations.append(
                        f"{display_path}:{node.lineno}:call"
                    )
    return violations


def test_every_migrated_designated_timestamp_table_is_registered():
    assert dict(QUESTDB_TIME_CONTRACTS) == _migrated_timestamp_contracts()


def test_repair_registry_uses_the_same_designated_timestamp_contract():
    assert {
        table.name: table.timestamp_column for table in TABLES
    } == dict(QUESTDB_TIME_CONTRACTS)


def test_registered_write_guard_accepts_only_aware_utc_instants_and_rejects_unknown_tables():
    assert questdb_write_timestamp(
        "storage_performance_metrics",
        datetime(2026, 7, 23, 6, 30, tzinfo=timezone.utc),
    ) == datetime(2026, 7, 23, 6, 30)

    with pytest.raises(ValueError, match="aware UTC"):
        questdb_write_timestamp("storage_usages", datetime(2026, 7, 23, 14, 30))

    with pytest.raises(ValueError, match="unregistered QuestDB timestamp table"):
        questdb_write_timestamp("new_unregistered_metrics", datetime.now())


def test_business_code_cannot_bypass_the_registered_write_guard():
    assert _direct_datetime_utility_bypasses() == []


def test_guard_reports_a_direct_datetime_utility_bypass(tmp_path):
    violating_writer = tmp_path / "violating_writer.py"
    violating_writer.write_text(
        "from utils.datetime_utils import to_questdb_utc_naive\n"
        "timestamp = to_questdb_utc_naive('2026-07-23T14:30:00')\n",
        encoding="utf-8",
    )

    assert _direct_datetime_utility_bypasses([violating_writer]) == [
        "violating_writer.py:1:import",
        "violating_writer.py:2:call",
    ]


def test_project_instructions_and_database_standard_repeat_the_hard_guardrail():
    agent_instructions = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    database_standard = (
        REPOSITORY_ROOT
        / "docs"
        / "standards"
        / "database"
        / "database-development-standard.md"
    ).read_text(encoding="utf-8")

    for content in (agent_instructions, database_standard):
        assert "QuestDB 时间硬约束" in content
        assert "questdb_write_timestamp" in content
        assert "QUESTDB_TIME_CONTRACTS" in content


def test_ci_runs_the_questdb_time_contract_guard_as_a_named_fail_fast_step():
    workflow = (
        REPOSITORY_ROOT / ".github" / "workflows" / "coverage-ci.yml"
    ).read_text(encoding="utf-8")

    assert "Enforce QuestDB UTC time contract" in workflow
    assert "test_questdb_time_contract_guard.py" in workflow
