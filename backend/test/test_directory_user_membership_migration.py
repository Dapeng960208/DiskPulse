# -*- coding: utf-8 -*-
import importlib.util
import io
from pathlib import Path

import sqlalchemy as sa
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = BACKEND_ROOT / "migrate" / "versions" / "000000000014_directory_user_memberships.py"


def _migration():
    spec = importlib.util.spec_from_file_location(MIGRATION_PATH.stem, MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_backfills_distinct_directory_users_without_downgrading_existing_roles():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    groups = sa.Table(
        "groups",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, nullable=False),
    )
    storage_usages = sa.Table(
        "storage_usages",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("group_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
    )
    memberships = sa.Table(
        "project_memberships",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.UniqueConstraint("project_id", "user_id"),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(groups.insert(), [{"id": 1, "project_id": 7}])
        connection.execute(
            storage_usages.insert(),
            [
                {"id": 1, "group_id": 1, "user_id": 10},
                {"id": 2, "group_id": 1, "user_id": 10},
                {"id": 3, "group_id": 1, "user_id": 11},
            ],
        )
        connection.execute(
            memberships.insert(),
            {"id": 1, "project_id": 7, "user_id": 11, "role": "editor"},
        )
        migration = _migration()
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        rows = connection.execute(
            sa.select(memberships.c.user_id, memberships.c.role).order_by(memberships.c.user_id)
        ).all()

    assert rows == [(10, "reader"), (11, "editor")]


@pytest.mark.parametrize("dialect_name", ("sqlite", "postgresql", "mysql"))
def test_directory_membership_migration_compiles_for_supported_dialects(dialect_name):
    output = io.StringIO()
    migration = _migration()
    migration.op = Operations(
        MigrationContext.configure(
            dialect_name=dialect_name,
            opts={"as_sql": True, "output_buffer": output},
        )
    )

    migration.upgrade()

    sql = output.getvalue().lower()
    assert "insert into project_memberships" in sql
    assert "storage_usages" in sql
    assert "reader" in sql
