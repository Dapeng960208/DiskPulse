# -*- coding: utf-8 -*-
import ast
from pathlib import Path


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
    expected_fields = set().union(*REMOVED_MODEL_FIELDS.values())
    dropped_fields = {
        call.args[0].value
        for call in ast.walk(upgrade)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "drop_column"
        and call.args
        and isinstance(call.args[0], ast.Constant)
    }
    restored_fields = {
        call.args[0].args[0].value
        for call in ast.walk(downgrade)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "add_column"
        and call.args
        and isinstance(call.args[0], ast.Call)
        and call.args[0].args
        and isinstance(call.args[0].args[0], ast.Constant)
    }

    assert dropped_fields == expected_fields
    assert restored_fields == expected_fields
