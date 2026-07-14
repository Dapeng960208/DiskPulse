# -*- coding: utf-8 -*-
import ast
import importlib.util
from pathlib import Path

import models
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
    create_engine,
    inspect,
)
from sqlalchemy.dialects import mysql, postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_ROOT = BACKEND_ROOT / "migrate" / "versions"
ENVIRONMENT_TABLE = "project_storage_environments"

ENVIRONMENT_COLUMNS = {
    "id",
    "project_id",
    "storage_cluster_id",
    "name",
    "description",
    "is_active",
    "limit",
    "soft_limit",
    "used",
    "use_ratio",
    "soft_use_ratio",
    "collection_status",
    "last_collected_at",
    "created_at",
    "updated_at",
}
ENVIRONMENT_INDEXES = {
    "ix_project_storage_environment_project_active_id": (
        "project_id",
        "is_active",
        "id",
    ),
    "ix_project_storage_environment_cluster_project": (
        "storage_cluster_id",
        "project_id",
    ),
    "ix_project_storage_environment_project_collection_active": (
        "project_id",
        "collection_status",
        "is_active",
    ),
}


def _environment_model():
    assert hasattr(models, "ProjectStorageEnvironment"), (
        "M1 requires models.ProjectStorageEnvironment"
    )
    return models.ProjectStorageEnvironment


def _default_text(column) -> str | None:
    default = column.default if column.default is not None else column.server_default
    if default is None:
        return None
    return str(default.arg).strip("'\"").lower()


def _relationship_targets(model) -> set[type]:
    return {relationship.mapper.class_ for relationship in inspect(model).relationships}


def _foreign_key_targets(column) -> set[str]:
    return {foreign_key.target_fullname for foreign_key in column.foreign_keys}


def _migration_path() -> Path:
    migrations = list(MIGRATION_ROOT.glob("*.py"))
    assert len(migrations) == 1, "initial development requires one baseline revision"
    return migrations[0]


def _load_migration(path: Path):
    spec = importlib.util.spec_from_file_location("diskpulse_initial_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _module_assignments(module: ast.Module) -> dict[str, ast.expr]:
    assignments = {}
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assignments[node.target.id] = node.value
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = node.value
    return assignments


def _function(module: ast.Module, name: str) -> ast.FunctionDef:
    functions = {
        node.name: node for node in module.body if isinstance(node, ast.FunctionDef)
    }
    assert name in functions, f"migration requires {name}()"
    return functions[name]


def _calls(node: ast.AST, attribute: str) -> list[ast.Call]:
    return [
        child
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and child.func.attr == attribute
    ]


def _literal_string(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _column_name(node: ast.AST | None) -> str | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr != "Column" or not node.args:
        return None
    return _literal_string(node.args[0])


def test_m1_environment_model_columns_and_nullable_defaults():
    table = _environment_model().__table__

    assert table.name == ENVIRONMENT_TABLE
    assert {column.name for column in table.c} == ENVIRONMENT_COLUMNS
    assert table.c.name.type.length == 128
    assert table.c.collection_status.type.length == 16
    assert table.c.name.nullable is False
    assert table.c.is_active.nullable is False
    assert table.c.collection_status.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False
    assert _default_text(table.c.is_active) in {"true", "1"}
    assert _default_text(table.c.collection_status) == "pending"

    for column_name in (
        "limit",
        "soft_limit",
        "used",
        "use_ratio",
        "soft_use_ratio",
        "last_collected_at",
    ):
        assert table.c[column_name].nullable is True
        assert _default_text(table.c[column_name]) is None


def test_m1_environment_relationships_constraints_and_indexes():
    environment = _environment_model()
    table = environment.__table__
    group_table = models.Group.__table__

    assert environment in _relationship_targets(models.Project)
    assert environment in _relationship_targets(models.StorageCluster)
    assert models.Group in _relationship_targets(environment)
    assert environment in _relationship_targets(models.Group)
    assert models.Volume in _relationship_targets(models.Group)

    assert {"project_environment_id", "volume_id"} <= {
        column.name for column in group_table.c
    }
    assert group_table.c.volume_id.nullable is True
    assert _foreign_key_targets(group_table.c.project_environment_id) == {
        "project_storage_environments.id"
    }
    assert _foreign_key_targets(group_table.c.volume_id) == {"volumes.id"}
    assert "qtree_id" in group_table.c

    foreign_keys = {
        constraint.name: (
            tuple(column.name for column in constraint.columns),
            tuple(element.target_fullname for element in constraint.elements),
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys["fk_project_storage_environment_project"] == (
        ("project_id",),
        ("projects.id",),
    )
    assert foreign_keys["fk_project_storage_environment_cluster"] == (
        ("storage_cluster_id",),
        ("storage_clusters.id",),
    )

    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints["uq_project_storage_environment_project_name"] == (
        "project_id",
        "name",
    )
    assert unique_constraints["uq_project_storage_environment_project_cluster"] == (
        "project_id",
        "storage_cluster_id",
    )

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    status_check = checks["ck_project_storage_environment_collection_status"]
    assert all(value in status_check for value in ("pending", "success", "failed"))

    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in table.indexes
    }
    assert ENVIRONMENT_INDEXES.items() <= indexes.items()
    assert ("project_id", "name") not in indexes.values()


def test_group_model_removes_derived_project_and_cluster_columns():
    assert {"project_id", "storage_cluster_id"}.isdisjoint(
        models.Group.__table__.c.keys()
    )


def test_group_model_requires_environment_binding():
    assert models.Group.__table__.c.project_environment_id.nullable is False


def test_group_model_enforces_environment_name_and_target_constraints():
    table = models.Group.__table__
    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    checks = {
        constraint.name: " ".join(str(constraint.sqltext).lower().split())
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert unique_constraints["uq_group_environment_name"] == (
        "project_environment_id",
        "name",
    )
    assert checks["ck_group_single_storage_target"] == (
        "volume_id is null or qtree_id is null"
    )
    monitored_target = checks["ck_group_monitored_has_storage_target"]
    assert all(
        clause in monitored_target
        for clause in (
            "enable_monitoring = false",
            "volume_id is not null",
            "qtree_id is not null",
        )
    )


def test_m1_environment_table_ddl_compiles_for_supported_dialects():
    table = _environment_model().__table__

    for dialect in (sqlite.dialect(), postgresql.dialect(), mysql.dialect()):
        assert ENVIRONMENT_TABLE in str(CreateTable(table).compile(dialect=dialect))
        for index in table.indexes:
            assert index.name in str(CreateIndex(index).compile(dialect=dialect))


def test_initial_migration_is_single_root_revision():
    path = _migration_path()
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    module = ast.parse(source)
    assignments = _module_assignments(module)

    assert "revision" in assignments
    revision = ast.literal_eval(assignments["revision"])
    assert isinstance(revision, str) and revision
    assert len(revision) <= 32
    assert "down_revision" in assignments
    assert ast.literal_eval(assignments["down_revision"]) is None

    upgrade = _function(module, "upgrade")
    downgrade = _function(module, "downgrade")
    expected_tables = set(models.Base.metadata.tables)
    created_tables = {
        _literal_string(call.args[0])
        for call in _calls(upgrade, "create_table")
        if call.args
    }
    dropped_tables = {
        _literal_string(call.args[0])
        for call in _calls(downgrade, "drop_table")
        if call.args
    }
    assert created_tables == expected_tables
    assert dropped_tables == expected_tables


def test_initial_migration_upgrades_empty_database_and_downgrades(tmp_path):
    migration = _load_migration(_migration_path())
    database_path = (tmp_path / "diskpulse-baseline.db").as_posix()
    engine = create_engine(f"sqlite:///{database_path}")

    try:
        with engine.begin() as connection:
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()

            database = inspect(connection)
            assert set(database.get_table_names()) == set(models.Base.metadata.tables)
            for table_name, table in models.Base.metadata.tables.items():
                assert {column["name"] for column in database.get_columns(table_name)} == {
                    column.name for column in table.c
                }

            migration.downgrade()
            assert inspect(connection).get_table_names() == []
    finally:
        engine.dispose()
