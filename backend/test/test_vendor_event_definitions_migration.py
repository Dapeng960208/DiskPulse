# -*- coding: utf-8 -*-
import importlib.util
import io
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

from appConfig import base_config


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    BACKEND_ROOT / "migrate" / "versions" / "000000000016_vendor_event_definitions.py"
)
PREVIOUS_REVISION = "000000000015"
REVISION = "000000000016"


def _alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


def _migration_module():
    spec = importlib.util.spec_from_file_location(MIGRATION_PATH.stem, MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_vendor_event_definitions_revision_is_the_current_alembic_head():
    scripts = ScriptDirectory.from_config(_alembic_config())

    assert scripts.get_heads() == [REVISION]
    assert scripts.get_revision(REVISION).down_revision == PREVIOUS_REVISION


@pytest.mark.parametrize("dialect_name", ("sqlite", "postgresql", "mysql"))
def test_vendor_event_definitions_migration_compiles_for_supported_dialects(
    dialect_name,
    monkeypatch,
):
    migration = _migration_module()
    # Offline (as_sql) migration contexts cannot execute the SELECT used by the
    # seed step; the real seed insert runs in the sqlite round-trip test below.
    monkeypatch.setattr(migration, "_insert_missing_rows", lambda bind, rows: None)
    output = io.StringIO()
    migration.op = Operations(
        MigrationContext.configure(
            dialect_name=dialect_name,
            opts={"as_sql": True, "output_buffer": output},
        )
    )

    migration.upgrade()
    migration.downgrade()

    sql = output.getvalue().lower()
    assert "vendor_event_definitions" in sql
    assert "uq_vendor_event_definition_storage_code" in sql
    assert "ck_vendor_event_definition_reviewed_evidence" in sql
    assert "ix_vendor_event_definition_filters" in sql
    assert "drop table vendor_event_definitions" in sql


def test_sqlite_upgrade_seeds_catalog_and_downgrade_removes_it(monkeypatch, tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'vendor-event-definitions.sqlite').as_posix()}"
    alembic_config = _alembic_config()
    monkeypatch.setattr(base_config, "get_sqlalchemy_database_url", lambda: database_url)
    migration = _migration_module()

    command.stamp(alembic_config, PREVIOUS_REVISION)
    command.upgrade(alembic_config, REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            inspector = sa.inspect(connection)
            assert "vendor_event_definitions" in inspector.get_table_names()
            rows = connection.execute(
                sa.text(
                    "SELECT storage_type, event_code, review_status, is_active "
                    "FROM vendor_event_definitions"
                )
            ).all()
            assert len(rows) == len(migration._COMMON_SEEDS)
            assert {(row[0], row[1]) for row in rows} == {
                (seed[0], seed[1]) for seed in migration._COMMON_SEEDS
            }
            assert all(row[3] for row in rows)
            reviewed = [row for row in rows if row[2] == "reviewed"]
            pending = [row for row in rows if row[2] == "pending"]
            assert len(reviewed) + len(pending) == len(rows)
            assert reviewed and pending

        with engine.begin() as connection:
            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(
                    sa.text(
                        "INSERT INTO vendor_event_definitions "
                        "(storage_type, event_code, association_type, title_zh, "
                        "description_zh, review_status) "
                        "VALUES ('netapp', 'bad.reviewed', 'fault_log', '标题', "
                        "'描述', 'reviewed')"
                    )
                )
    finally:
        engine.dispose()

    command.downgrade(alembic_config, PREVIOUS_REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert "vendor_event_definitions" not in sa.inspect(
                connection
            ).get_table_names()
    finally:
        engine.dispose()
