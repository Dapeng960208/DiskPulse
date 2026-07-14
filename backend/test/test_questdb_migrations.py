# -*- coding: utf-8 -*-
import ast
import importlib.util
import sys
from pathlib import Path

import pytest

import questdb.models  # noqa: F401
from questdb.database import QuestDBBase


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_MODULE = BACKEND_ROOT / "questdb" / "migrate.py"
MIGRATION_ROOT = BACKEND_ROOT / "questdb" / "migrations"


class _Rows:
    def __init__(self, rows=()):
        self._rows = rows

    def all(self):
        return list(self._rows)

    def scalars(self):
        return (row[0] if isinstance(row, tuple) else row for row in self._rows)


class _Connection:
    def __init__(self, engine):
        self.engine = engine

    def execute(self, statement, parameters=None):
        sql = " ".join(str(statement).split())
        self.engine.statements.append(sql)
        if sql.startswith("SELECT version, checksum"):
            return _Rows(self.engine.applied_rows or self.engine.applied.items())
        if sql.startswith("SELECT table_name FROM tables()"):
            return _Rows((table_name,) for table_name in self.engine.tables)
        if sql.startswith("CREATE TABLE IF NOT EXISTS diskpulse_schema_migrations"):
            self.engine.tables.add("diskpulse_schema_migrations")
        if sql.startswith("INSERT INTO diskpulse_schema_migrations"):
            self.engine.applied[parameters["version"]] = parameters["checksum"]
        return _Rows()

    def commit(self):
        self.engine.commits += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class _Engine:
    def __init__(self, applied=None, applied_rows=None, tables=None):
        self.applied = dict(applied or {})
        self.applied_rows = applied_rows
        self.tables = set(tables or ())
        self.statements = []
        self.commits = 0

    def connect(self):
        return _Connection(self)


def _load_runner():
    assert MIGRATION_MODULE.is_file(), "QuestDB requires a migration runner"
    spec = importlib.util.spec_from_file_location("diskpulse_questdb_migrate", MIGRATION_MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _normalize(sql: str) -> str:
    return " ".join(sql.split())


def test_questdb_migrations_add_soft_quota_metric_columns():
    runner = _load_runner()
    migrations = runner.load_migrations(MIGRATION_ROOT)

    assert tuple(migration.version for migration in migrations) == (
        "000000000001",
        "000000000002",
    )
    soft_quota_tables = {
        "volume_storage_usages",
        "qtree_storage_usages",
        "project_storage_usages",
        "group_storage_usages",
        "storage_usages",
    }
    expected = {
        f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} DOUBLE"
        for table_name in soft_quota_tables
        for column_name in ("soft_limit", "soft_use_ratio")
    }
    assert set(map(_normalize, migrations[1].statements)) == expected

    for table_name in soft_quota_tables:
        assert {"soft_limit", "soft_use_ratio"} <= set(
            QuestDBBase.metadata.tables[table_name].columns.keys()
        )
    for table_name in {
        "aggregate_storage_usages",
        "storage_cluster_storage_usages",
    }:
        assert "soft_limit" not in QuestDBBase.metadata.tables[table_name].columns
        assert "soft_use_ratio" not in QuestDBBase.metadata.tables[table_name].columns


def test_questdb_upgrade_records_revision_and_is_repeatable():
    runner = _load_runner()
    engine = _Engine()

    assert runner.upgrade(engine) == ("000000000001", "000000000002")
    assert runner.upgrade(engine) == ()
    assert engine.applied.keys() == {"000000000001", "000000000002"}
    assert engine.commits == 2


def test_questdb_upgrade_applies_soft_quota_revision_after_initial_schema():
    runner = _load_runner()
    initial = runner.load_migrations(MIGRATION_ROOT)[0]
    engine = _Engine(
        {"000000000001": initial.checksum},
        tables={"diskpulse_schema_migrations"},
    )

    assert runner.upgrade(engine) == ("000000000002",)
    assert engine.applied.keys() == {"000000000001", "000000000002"}


def test_questdb_upgrade_rejects_changed_applied_revision():
    runner = _load_runner()
    engine = _Engine({"000000000001": "changed"})

    with pytest.raises(RuntimeError, match="checksum"):
        runner.upgrade(engine)


def test_questdb_upgrade_rejects_unknown_or_conflicting_revisions():
    runner = _load_runner()

    with pytest.raises(RuntimeError, match="Unknown applied"):
        runner.upgrade(_Engine({"999999999999": "unknown"}))
    with pytest.raises(RuntimeError, match="conflicting checksums"):
        runner.upgrade(
            _Engine(
                applied_rows=[
                    ("000000000001", "first"),
                    ("000000000001", "second"),
                ]
            )
        )


def test_questdb_migration_filenames_are_valid_and_unique(tmp_path):
    runner = _load_runner()
    (tmp_path / "invalid-name.sql").write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Invalid QuestDB migration filename"):
        runner.load_migrations(tmp_path)

    (tmp_path / "invalid-name.sql").unlink()
    (tmp_path / "000000000001_one.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "000000000001_two.sql").write_text("SELECT 2;", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Duplicate QuestDB migration version"):
        runner.load_migrations(tmp_path)


def test_questdb_current_reports_base_and_applied_revisions():
    runner = _load_runner()

    assert runner.current(_Engine()) == ()
    assert runner.current(
        _Engine(
            {"000000000001": "checksum"},
            tables={"diskpulse_schema_migrations"},
        )
    ) == ("000000000001",)


@pytest.mark.parametrize(
    ("command", "current_versions", "upgraded_versions", "expected"),
    [
        (
            "history",
            (),
            (),
            "000000000001 initial_schema\n000000000002 add_soft_quota_metrics",
        ),
        ("current", ("000000000002",), (), "000000000002"),
        ("current", (), (), "base"),
        ("upgrade", (), ("000000000002",), "upgraded: 000000000002"),
        ("upgrade", (), (), "up to date"),
    ],
)
def test_questdb_migration_cli(
    monkeypatch, capsys, command, current_versions, upgraded_versions, expected
):
    runner = _load_runner()
    monkeypatch.setattr(runner, "current", lambda: current_versions)
    monkeypatch.setattr(runner, "upgrade", lambda: upgraded_versions)

    assert runner.main([command]) == 0
    assert capsys.readouterr().out.strip() == expected


def test_startup_uses_versioned_questdb_migrations():
    source = (BACKEND_ROOT / "main.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    imported_aliases = {
        alias.asname or alias.name
        for node in module.body
        if isinstance(node, ast.ImportFrom) and node.module == "questdb.migrate"
        for alias in node.names
    }
    called_names = {
        node.func.id
        for node in ast.walk(module)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "upgrade_questdb" in imported_aliases
    assert "upgrade_questdb" in called_names
    assert "QuestDBBase.metadata.create_all" not in source
