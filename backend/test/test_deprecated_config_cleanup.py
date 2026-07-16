# -*- coding: utf-8 -*-
import importlib.util
import io
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REMOVED_CONFIG_FIELDS = {
    "storage_host",
    "storage_port",
    "storage_user",
    "storage_password",
    "iam_url",
    "iam_account",
    "iam_password",
    "bpm_api_url",
    "bpm_process_id",
}


def _cleanup_migration():
    path = BACKEND_ROOT / "migrate" / "versions" / "000000000007_deprecated_config_cleanup.py"
    assert path.is_file(), "deprecated config cleanup requires migration 000000000007"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_deprecated_global_config_fields_are_absent_but_cluster_credentials_remain():
    import models
    from schemas import configSchemas

    assert REMOVED_CONFIG_FIELDS.isdisjoint(models.StorageConf.__table__.columns.keys())
    assert REMOVED_CONFIG_FIELDS.isdisjoint(configSchemas.StorageConf.model_fields)
    assert REMOVED_CONFIG_FIELDS.isdisjoint(configSchemas.StorageConfPublic.model_fields)
    assert {
        "storage_host",
        "storage_port",
        "storage_user",
        "storage_password",
    } <= set(models.StorageCluster.__table__.columns.keys())


def test_deprecated_expansion_and_iam_bpm_entry_points_are_removed():
    from celery_tasks.manager.remoteFileManager import RemoteFileManager
    from routers import storage_usage
    from schemas import storageUsageSchema

    assert not hasattr(RemoteFileManager, "initiating_quit_users_bpm_process")
    assert not hasattr(storageUsageSchema, "StorageUsageExpand")
    assert "/storage-usages/expand" not in {route.path for route in storage_usage.router.routes}


def test_cleanup_migration_drops_and_restores_columns_on_sqlite():
    migration = _cleanup_migration()
    assert migration.revision == "000000000007"
    assert migration.down_revision == "000000000006"

    metadata = sa.MetaData()
    sa.Table(
        "storage_conf",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String()),
        *(
            sa.Column(
                name,
                sa.Integer() if name in {"storage_port", "bpm_process_id"} else sa.String(),
            )
            for name in sorted(REMOVED_CONFIG_FIELDS)
        ),
    )
    with sa.create_engine("sqlite://").begin() as connection:
        metadata.create_all(connection)
        connection.execute(sa.text("INSERT INTO storage_conf (id, name) VALUES (1, 'test')"))
        migration.op = Operations(MigrationContext.configure(connection))

        migration.upgrade()
        table_columns = {column["name"] for column in sa.inspect(connection).get_columns("storage_conf")}
        assert table_columns == {"id", "name"}

        migration.downgrade()
        restored_columns = {column["name"] for column in sa.inspect(connection).get_columns("storage_conf")}
        assert REMOVED_CONFIG_FIELDS <= restored_columns
        restored = connection.execute(
            sa.text(
                "SELECT " + ", ".join(sorted(REMOVED_CONFIG_FIELDS)) + " FROM storage_conf WHERE id = 1"
            )
        ).one()
        assert all(value is None for value in restored)


def test_cleanup_migration_compiles_for_postgresql_and_mysql():
    migration = _cleanup_migration()

    for dialect in ("postgresql", "mysql"):
        output = io.StringIO()
        context = MigrationContext.configure(
            dialect_name=dialect,
            opts={"as_sql": True, "output_buffer": output},
        )
        migration.op = Operations(context)
        migration.upgrade()
        migration.downgrade()
        sql = output.getvalue()
        for field in REMOVED_CONFIG_FIELDS:
            assert field in sql
