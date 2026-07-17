# -*- coding: utf-8 -*-
import importlib.util
import io
import json
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
VERSIONS_ROOT = BACKEND_ROOT / "migrate" / "versions"
UNIFIED_REVISION = "000000000009"
UNIFIED_MIGRATION = VERSIONS_ROOT / "000000000009_project_rbac_unified_audit.py"
TELEMETRY_MIGRATION = VERSIONS_ROOT / "000000000008_telemetry_collection_runs.py"
RELEASE_TRACKING = BACKEND_ROOT.parent / "docs" / "tracking" / "current-release.md"


def _alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


def _migration_module():
    spec = importlib.util.spec_from_file_location(UNIFIED_MIGRATION.stem, UNIFIED_MIGRATION)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_unified_rbac_audit_revision_is_the_only_head_and_replaces_old_split_file():
    scripts = ScriptDirectory.from_config(_alembic_config())

    assert scripts.get_heads() == [UNIFIED_REVISION]
    assert not (VERSIONS_ROOT / "000000000008_project_memberships.py").exists()
    assert TELEMETRY_MIGRATION.exists()


@pytest.mark.parametrize("dialect_name", ("sqlite", "postgresql", "mysql"))
def test_unified_rbac_audit_migration_compiles_for_all_supported_dialects(dialect_name):
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
    assert "project_memberships" in sql
    assert "audit_events" in sql
    if dialect_name == "sqlite":
        assert "storage_alert_rule" in sql


def test_sqlite_upgrade_and_downgrade_preserve_storage_alert_rule(monkeypatch, tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'project-rbac-audit.sqlite').as_posix()}"
    alembic_config = _alembic_config()
    monkeypatch.setattr(base_config, "get_sqlalchemy_database_url", lambda: database_url)

    command.upgrade(alembic_config, "000000000007")
    engine = sa.create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(sa.text("INSERT INTO users (id) VALUES (:id)"), [{"id": 1}, {"id": 2}])
            connection.execute(
                sa.text(
                    "INSERT INTO projects "
                    "(id, name, in_charge_user_id, pt_user_id, storage_alert_rule) "
                    "VALUES (:id, :name, :owner_id, :pt_user_id, :storage_alert_rule)"
                ),
                {
                    "id": 1,
                    "name": "project-a",
                    "owner_id": 1,
                    "pt_user_id": 2,
                    "storage_alert_rule": json.dumps({"threshold": 85}),
                },
            )

        command.upgrade(alembic_config, UNIFIED_REVISION)
        with engine.connect() as connection:
            columns = {column["name"] for column in sa.inspect(connection).get_columns("projects")}
            assert "pt_user_id" not in columns
            assert "storage_alert_rule" in columns
            rule = connection.execute(
                sa.text("SELECT storage_alert_rule FROM projects WHERE id = :id"), {"id": 1}
            ).scalar_one()
            assert json.loads(rule) == {"threshold": 85}
            membership = connection.execute(
                sa.text("SELECT project_id, user_id, role FROM project_memberships")
            ).one()
            assert membership == (1, 1, "project_admin")
            telemetry_columns = {
                column["name"]
                for column in sa.inspect(connection).get_columns("telemetry_collection_runs")
            }
            assert {"task_id", "trace_id", "outcome"}.issubset(telemetry_columns)

        command.downgrade(alembic_config, "000000000007")
        with engine.connect() as connection:
            columns = {column["name"] for column in sa.inspect(connection).get_columns("projects")}
            assert "pt_user_id" in columns
            assert "storage_alert_rule" in columns
            rule = connection.execute(
                sa.text("SELECT storage_alert_rule FROM projects WHERE id = :id"), {"id": 1}
            ).scalar_one()
            assert json.loads(rule) == {"threshold": 85}
            assert "telemetry_collection_runs" not in sa.inspect(connection).get_table_names()
    finally:
        engine.dispose()


def test_release_tracking_names_unified_migration_and_pt_data_restore_risk():
    release = RELEASE_TRACKING.read_text(encoding="utf-8")

    assert "000000000009_project_rbac_unified_audit.py" in release
    assert "pt_user_id" in release
    assert "不可恢复" in release
