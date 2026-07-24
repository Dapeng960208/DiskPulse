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
COMPATIBILITY_REVISION = "000000000018"
QUESTDB_TIME_REPAIR_REVISION = "000000000019"
DISKPULSE_ALERT_EVIDENCE_REPAIR_REVISION = "000000000020"
INCIDENT_AI_AGENT_REVISION = "000000000021"
HEAD_REVISION = "000000000022"


def _alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


def _migration_module():
    spec = importlib.util.spec_from_file_location(MIGRATION_PATH.stem, MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_vendor_event_association_revision_precedes_the_compatibility_head():
    scripts = ScriptDirectory.from_config(_alembic_config())

    # Subsequent migrations are allowed to extend this linear chain.  The
    # compatibility sequence itself must remain reachable below one head.
    assert len(scripts.get_heads()) == 1
    assert HEAD_REVISION in {revision.revision for revision in scripts.walk_revisions()}
    assert scripts.get_revision(REVISION).down_revision == PREVIOUS_REVISION
    assert scripts.get_revision(COMPATIBILITY_REVISION).down_revision == REVISION
    assert (
        scripts.get_revision(QUESTDB_TIME_REPAIR_REVISION).down_revision
        == COMPATIBILITY_REVISION
    )
    assert (
        scripts.get_revision(DISKPULSE_ALERT_EVIDENCE_REPAIR_REVISION).down_revision
        == QUESTDB_TIME_REPAIR_REVISION
    )
    assert (
        scripts.get_revision(INCIDENT_AI_AGENT_REVISION).down_revision
        == DISKPULSE_ALERT_EVIDENCE_REPAIR_REVISION
    )
    assert scripts.get_revision(HEAD_REVISION).down_revision == INCIDENT_AI_AGENT_REVISION


@pytest.mark.parametrize("dialect_name", ("sqlite", "postgresql", "mysql"))
def test_vendor_event_association_migration_compiles_for_supported_dialects(
    dialect_name,
):
    migration = _migration_module()
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
    assert "insert into vendor_event_definitions" not in sql
    assert "update vendor_event_definitions" not in sql


def test_sqlite_upgrade_changes_only_structure_and_replays_from_016(
    monkeypatch, tmp_path
):
    database_url = f"sqlite:///{(tmp_path / 'vendor-event-definitions.sqlite').as_posix()}"
    alembic_config = _alembic_config()
    monkeypatch.setattr(base_config, "get_sqlalchemy_database_url", lambda: database_url)

    command.stamp(alembic_config, BASE_REVISION)
    command.upgrade(alembic_config, REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            inspector = sa.inspect(connection)
            assert "vendor_event_definitions" in inspector.get_table_names()
            columns = {
                column["name"]
                for column in inspector.get_columns("vendor_event_definitions")
            }
            assert "recommended_solution_zh" in columns
            assert connection.execute(
                sa.text("SELECT COUNT(*) FROM vendor_event_definitions")
            ).scalar_one() == 0

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
            assert connection.execute(
                sa.text("SELECT COUNT(*) FROM vendor_event_definitions")
            ).scalar_one() == 0
    finally:
        engine.dispose()

    command.upgrade(alembic_config, REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                sa.text("SELECT COUNT(*) FROM vendor_event_definitions")
            ).scalar_one() == 0
    finally:
        engine.dispose()

    command.downgrade(alembic_config, BASE_REVISION)
    engine = sa.create_engine(database_url)
    try:
        assert "vendor_event_definitions" not in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()
