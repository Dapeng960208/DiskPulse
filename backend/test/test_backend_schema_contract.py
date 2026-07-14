# -*- coding: utf-8 -*-
import ast
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_ROOT = BACKEND_ROOT / "migrate" / "versions"
LEGACY_PROJECT_RESOURCE_FIELDS = {
    "master",
    "max_swp",
    "resources",
    "rsv",
    "r15s",
    "r1m",
    "r15m",
    "ut",
    "pg",
    "ls",
    "it",
    "tmp",
    "swp",
    "sut",
    "mut",
}
REMOVED_MODEL_FIELDS = {
    "Host": {"status", "updated_at"},
    "Project": {
        "ncpus",
        "max_jobs",
        "cpuf",
        "max_mem",
        "mem",
        "mem_reserved",
        "slot",
        "slot_reserved",
        "run_jobs",
        "ssusp_jobs",
        "ususp_jobs",
        "pend_jobs",
    },
    "StorageBackUpRecord": {"is_deleted"},
    "StorageConf": {
        "questdb_host",
        "questdb_port",
        "questdb_user",
        "questdb_password",
    },
    "User": {"run_jobs", "ssusp_jobs", "pend_jobs", "done_jobs", "exit_jobs"},
}
REMOVED_DATABASE_FIELDS = {
    "hosts": REMOVED_MODEL_FIELDS["Host"],
    "projects": REMOVED_MODEL_FIELDS["Project"],
    "storage_back_up_records": REMOVED_MODEL_FIELDS["StorageBackUpRecord"],
    "storage_conf": REMOVED_MODEL_FIELDS["StorageConf"],
    "users": REMOVED_MODEL_FIELDS["User"],
}
REMOVED_SCHEMA_FIELDS = {
    ("schemas/configSchemas.py", "StorageConf"): REMOVED_MODEL_FIELDS["StorageConf"],
    ("schemas/configSchemas.py", "StorageConfPublic"): {
        "questdb_host",
        "questdb_port",
        "questdb_user",
    },
    ("schemas/projectsSchema.py", "ProjectBaseInfo"): {
        "ncpus",
        "max_jobs",
        "cpuf",
        "max_mem",
    },
    ("schemas/projectsSchema.py", "ProjectBase"): {
        "mem",
        "mem_reserved",
        "slot",
        "slot_reserved",
        "run_jobs",
        "ssusp_jobs",
        "ususp_jobs",
        "pend_jobs",
    },
    ("schemas/storageBackUpRecordSchema.py", "StorageBackUpRecordBase"): {
        "is_deleted"
    },
    ("schemas/usersSchema.py", "UserBase"): REMOVED_MODEL_FIELDS["User"],
}
FINAL_TABLES = {
    "aggregates",
    "groups",
    "hosts",
    "large_files",
    "group_tags",
    "projects",
    "qtrees",
    "storage_alerts",
    "storage_back_up_records",
    "storage_clusters",
    "storage_conf",
    "storage_usages",
    "users",
    "volumes",
}
KEY_COLUMNS = {
    "aggregates": {"id", "storage_cluster_id", "limit", "used"},
    "groups": {"id", "project_id", "storage_cluster_id", "group_tag_id", "volume_id", "qtree_id"},
    "hosts": {"id", "name", "ip"},
    "large_files": {"id", "user_id", "group_id", "linux_path"},
    "group_tags": {"id", "name"},
    "projects": {"id", "name", "soft_limit", "soft_use_ratio"},
    "qtrees": {"id", "storage_cluster_id", "volume_id", "soft_limit"},
    "storage_alerts": {"id", "alert_level", "related_id", "related_type"},
    "storage_back_up_records": {"id", "user_id", "source_path", "status"},
    "storage_clusters": {"id", "name", "storage_type", "storage_host"},
    "storage_conf": {"id", "name", "back_up_enabled"},
    "storage_usages": {
        "id",
        "storage_cluster_id",
        "user_id",
        "group_id",
        "soft_limit",
        "soft_use_ratio",
    },
    "users": {"id", "rd_username", "is_alert"},
    "volumes": {"id", "storage_cluster_id", "soft_limit", "soft_use_ratio"},
}


def _parse_backend_file(relative_path: str) -> ast.Module:
    return ast.parse((BACKEND_ROOT / relative_path).read_text(encoding="utf-8"))


def _class_node(module: ast.Module, class_name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"{class_name} class was not found")


def _annotated_fields(class_node: ast.ClassDef) -> set[str]:
    fields = set()
    for node in class_node.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            fields.add(node.target.id)
    return fields


def _assigned_fields(class_node: ast.ClassDef) -> set[str]:
    return {
        node.targets[0].id
        for node in class_node.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }


def _class_names(module: ast.Module) -> set[str]:
    return {node.name for node in module.body if isinstance(node, ast.ClassDef)}


def _baseline_migration():
    migrations = sorted(MIGRATION_ROOT.glob("*.py"))
    assert len(migrations) == 1, (
        f"expected one initial migration, found {[path.name for path in migrations]}"
    )
    spec = importlib.util.spec_from_file_location("initial_schema", migrations[0])
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_unused_storage_records_model_is_removed():
    module = _parse_backend_file("models.py")

    assert "StorageRecords" not in _class_names(module)


def test_project_schema_exposes_only_persisted_or_computed_fields():
    module = _parse_backend_file("schemas/projectsSchema.py")
    project_base = _class_node(module, "ProjectBase")

    project_fields = _annotated_fields(project_base)

    assert project_fields.isdisjoint(LEGACY_PROJECT_RESOURCE_FIELDS)


def test_confirmed_unused_fields_are_removed_from_models_and_schemas():
    models_module = _parse_backend_file("models.py")

    for class_name, removed_fields in REMOVED_MODEL_FIELDS.items():
        assert _assigned_fields(_class_node(models_module, class_name)).isdisjoint(
            removed_fields
        )

    for (relative_path, class_name), removed_fields in REMOVED_SCHEMA_FIELDS.items():
        module = _parse_backend_file(relative_path)
        assert _annotated_fields(_class_node(module, class_name)).isdisjoint(
            removed_fields
        )


def test_database_migrations_are_one_root_baseline():
    migration = _baseline_migration()

    assert migration.down_revision is None
    assert isinstance(migration.revision, str)
    assert 0 < len(migration.revision) <= 32


def test_initial_schema_upgrade_and_downgrade_on_empty_sqlite():
    migration = _baseline_migration()
    with sa.create_engine("sqlite://").begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = sa.inspect(connection)

        assert set(inspector.get_table_names()) == FINAL_TABLES
        for table_name, expected_columns in KEY_COLUMNS.items():
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            assert expected_columns <= columns
        for table_name, field_names in REMOVED_DATABASE_FIELDS.items():
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            assert columns.isdisjoint(field_names)

        group_columns = {
            column["name"]: column for column in inspector.get_columns("groups")
        }
        assert group_columns["project_id"]["nullable"] is False
        assert group_columns["storage_cluster_id"]["nullable"] is False
        assert group_columns["group_tag_id"]["nullable"] is False

        migration.downgrade()
        inspector.clear_cache()
        assert inspector.get_table_names() == []
