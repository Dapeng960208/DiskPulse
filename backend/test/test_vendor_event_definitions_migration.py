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
    BACKEND_ROOT
    / "migrate"
    / "versions"
    / "000000000017_update_vendor_event_associations.py"
)
BASE_REVISION = "000000000015"
PREVIOUS_REVISION = "000000000016"
REVISION = "000000000017"
EXPECTED_CATALOG_SIZE = 68


def _alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


def _migration_module():
    spec = importlib.util.spec_from_file_location(MIGRATION_PATH.stem, MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_vendor_event_association_revision_is_the_current_alembic_head():
    scripts = ScriptDirectory.from_config(_alembic_config())

    assert scripts.get_heads() == [REVISION]
    assert scripts.get_revision(REVISION).down_revision == PREVIOUS_REVISION


@pytest.mark.parametrize("dialect_name", ("sqlite", "postgresql", "mysql"))
def test_vendor_event_association_migration_compiles_for_supported_dialects(
    dialect_name,
    monkeypatch,
):
    migration = _migration_module()
    monkeypatch.setattr(migration, "_upsert_catalog_rows", lambda bind, rows: None)
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
    assert "recommended_solution_zh" in sql
    assert "ck_vendor_event_definition_reviewed_evidence" in sql


def test_sqlite_upgrade_catalog_is_complete_and_replays_from_016(monkeypatch, tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'vendor-event-definitions.sqlite').as_posix()}"
    alembic_config = _alembic_config()
    monkeypatch.setattr(base_config, "get_sqlalchemy_database_url", lambda: database_url)
    migration = _migration_module()

    command.stamp(alembic_config, BASE_REVISION)
    command.upgrade(alembic_config, REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            inspector = sa.inspect(connection)
            assert "vendor_event_definitions" in inspector.get_table_names()
            columns = {column["name"] for column in inspector.get_columns("vendor_event_definitions")}
            assert "recommended_solution_zh" in columns
            rows = connection.execute(
                sa.text(
                    "SELECT storage_type, event_code, association_type, "
                    "official_reference_url, version_scope, review_status, "
                    "recommended_solution_zh FROM vendor_event_definitions"
                )
            ).mappings().all()
            assert len(rows) == EXPECTED_CATALOG_SIZE
            assert {(row["storage_type"], row["event_code"]) for row in rows} == {
                (row["storage_type"], row["event_code"])
                for row in migration.CATALOG_DEFINITIONS
            }
            reviewed = [row for row in rows if row["review_status"] == "reviewed"]
            pending = [row for row in rows if row["review_status"] == "pending"]
            assert reviewed and pending
            assert all(
                row["association_type"] != "unknown"
                and row["official_reference_url"]
                and row["version_scope"]
                and row["recommended_solution_zh"]
                for row in reviewed
            )
            assert all(
                row["association_type"] == "unknown"
                and row["official_reference_url"] is None
                and row["version_scope"] is None
                and row["recommended_solution_zh"] is None
                for row in pending
            )

        with engine.begin() as connection:
            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(
                    sa.text(
                        "INSERT INTO vendor_event_definitions "
                        "(storage_type, event_code, association_type, title_zh, "
                        "description_zh, official_reference_url, version_scope, "
                        "review_status, recommended_solution_zh) "
                        "VALUES ('netapp', 'bad.reviewed', 'fault_log', '标题', "
                        "'描述', 'https://docs.netapp.com/us-en/ontap-ems/', "
                        "'ONTAP 9', 'reviewed', NULL)"
                    )
                )
    finally:
        engine.dispose()

    command.downgrade(alembic_config, PREVIOUS_REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            columns = {
                column["name"]
                for column in sa.inspect(connection).get_columns(
                    "vendor_event_definitions"
                )
            }
            assert "recommended_solution_zh" not in columns
    finally:
        engine.dispose()

    command.upgrade(alembic_config, REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                sa.text("SELECT COUNT(*) FROM vendor_event_definitions")
            ).scalar_one() == EXPECTED_CATALOG_SIZE
    finally:
        engine.dispose()

    command.downgrade(alembic_config, BASE_REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert "vendor_event_definitions" not in sa.inspect(
                connection
            ).get_table_names()
    finally:
        engine.dispose()
