# -*- coding: utf-8 -*-
import ast
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.ddl.base import DropColumn
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import mysql, postgresql, sqlite


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


def _migration_columns(function: ast.FunctionDef, operation: str) -> dict[str, set[str]]:
    columns = {}
    for node in function.body:
        if not isinstance(node, ast.With) or len(node.items) != 1:
            continue
        context = node.items[0].context_expr
        if (
            not isinstance(context, ast.Call)
            or not isinstance(context.func, ast.Attribute)
            or context.func.attr != "batch_alter_table"
            or not context.args
            or not isinstance(context.args[0], ast.Constant)
        ):
            continue
        table_name = context.args[0].value
        table_columns = set()
        for call in ast.walk(node):
            if (
                not isinstance(call, ast.Call)
                or not isinstance(call.func, ast.Attribute)
                or call.func.attr != operation
                or not call.args
            ):
                continue
            argument = call.args[0]
            if operation == "add_column" and isinstance(argument, ast.Call):
                argument = argument.args[0]
            if isinstance(argument, ast.Constant):
                table_columns.add(argument.value)
        columns[table_name] = table_columns
    return columns


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


def test_unused_field_cleanup_migration_covers_all_removed_database_columns():
    migrations = list(MIGRATION_ROOT.glob("*_remove_unused_fields.py"))

    assert len(migrations) == 1
    module = ast.parse(migrations[0].read_text(encoding="utf-8"))
    upgrade = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
    )
    downgrade = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade"
    )
    assert _migration_columns(upgrade, "drop_column") == REMOVED_DATABASE_FIELDS
    assert _migration_columns(downgrade, "add_column") == REMOVED_DATABASE_FIELDS


def test_unused_field_cleanup_migration_applies_and_rolls_back_on_sqlite():
    migration_path = next(MIGRATION_ROOT.glob("*_remove_unused_fields.py"))
    spec = importlib.util.spec_from_file_location("unused_field_cleanup", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    metadata = sa.MetaData()
    for table_name, field_names in REMOVED_DATABASE_FIELDS.items():
        sa.Table(
            table_name,
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            *(sa.Column(name, sa.String()) for name in field_names),
        )

    with sa.create_engine("sqlite://").begin() as connection:
        metadata.create_all(connection)
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = sa.inspect(connection)
        for table_name, field_names in REMOVED_DATABASE_FIELDS.items():
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            assert columns.isdisjoint(field_names)

        migration.downgrade()
        inspector.clear_cache()
        for table_name, field_names in REMOVED_DATABASE_FIELDS.items():
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            assert field_names <= columns


def test_drop_column_ddl_compiles_for_supported_dialects():
    metadata = sa.MetaData()
    table = sa.Table(
        "cleanup_target",
        metadata,
        sa.Column("unused_field", sa.String(64)),
    )

    for dialect in (sqlite.dialect(), postgresql.dialect(), mysql.dialect()):
        sql = str(
            DropColumn(table.name, table.c.unused_field).compile(dialect=dialect)
        )
        assert "DROP COLUMN unused_field" in sql
