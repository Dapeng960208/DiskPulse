# -*- coding: utf-8 -*-
import ast
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
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


def _class_names(module: ast.Module) -> set[str]:
    return {node.name for node in module.body if isinstance(node, ast.ClassDef)}


class BackendSchemaContractTest(unittest.TestCase):
    def test_unused_storage_records_model_is_removed(self):
        module = _parse_backend_file("models.py")

        self.assertNotIn("StorageRecords", _class_names(module))

    def test_project_schema_exposes_only_persisted_or_computed_fields(self):
        module = _parse_backend_file("schemas/projectsSchema.py")
        project_base = _class_node(module, "ProjectBase")

        project_fields = _annotated_fields(project_base)

        self.assertTrue(project_fields.isdisjoint(LEGACY_PROJECT_RESOURCE_FIELDS))


if __name__ == "__main__":
    unittest.main()
