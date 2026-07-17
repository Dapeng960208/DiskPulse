# -*- coding: utf-8 -*-
import importlib.util
import io
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError


VERSIONS = Path(__file__).resolve().parents[1] / "migrate" / "versions"
MIGRATION_PATH = VERSIONS / "000000000008_project_rbac_unified_audit.py"


def _migration():
    assert MIGRATION_PATH.exists(), "branch migrations must be consolidated before merge"
    spec = importlib.util.spec_from_file_location(MIGRATION_PATH.stem, MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_branch_rbac_audit_migrations_are_a_single_revision_from_main_head():
    migration = _migration()

    assert migration.revision == "000000000008"
    assert migration.down_revision == "000000000007"
    assert not (VERSIONS / "000000000009_unified_audit.py").exists()

    for dialect_name in ("sqlite", "postgresql", "mysql"):
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


def test_immutable_audit_rows_keep_logical_actor_and_project_ids_when_subjects_are_deleted():
    migration = _migration()
    metadata = sa.MetaData()
    users = sa.Table("users", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    projects = sa.Table(
        "projects",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("in_charge_user_id", sa.Integer()),
        sa.Column("pt_user_id", sa.Integer()),
    )
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        metadata.create_all(connection)
        connection.execute(users.insert(), [{"id": 1}, {"id": 2}])
        connection.execute(projects.insert(), {"id": 1, "in_charge_user_id": 1, "pt_user_id": 2})
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        connection.execute(
            sa.text(
                """
                INSERT INTO audit_events (
                    id, operation_id, phase, occurred_at, actor_type, actor_user_id,
                    action, resource_type, project_id, outcome, request_id, trace_id
                ) VALUES (
                    '32d85a48-2667-4ee7-b369-5c4d670eb610',
                    '54248ded-a2cb-45b5-b464-b5c12a2dc90d',
                    'result', CURRENT_TIMESTAMP, 'user', 1,
                    'project.membership.create', 'project_membership', 1, 'success',
                    'c57c77c9-46ed-4c3f-92fc-bfd6d9e7eae6',
                    'ee874b8d-e657-45eb-b6f2-c0a7c4cefb39'
                )
                """
            )
        )

        connection.execute(users.delete().where(users.c.id == 1))
        connection.execute(projects.delete().where(projects.c.id == 1))

        actor_user_id, project_id = connection.execute(
            sa.text("SELECT actor_user_id, project_id FROM audit_events")
        ).one()
        assert (actor_user_id, project_id) == (1, 1)
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(sa.text("UPDATE audit_events SET action = 'changed'"))
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(sa.text("DELETE FROM audit_events"))
