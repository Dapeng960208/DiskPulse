# -*- coding: utf-8 -*-
import importlib.util
import io
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from alembic.config import Config


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = BACKEND_ROOT / "migrate" / "versions" / "000000000012_capacity_prediction_governance.py"


def _migration():
    spec = importlib.util.spec_from_file_location(MIGRATION_PATH.stem, MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capacity_prediction_governance_is_the_alembic_head():
    scripts = ScriptDirectory.from_config(Config(str(BACKEND_ROOT / "alembic.ini")))

    assert scripts.get_heads() == ["000000000012"]


@pytest.mark.parametrize("dialect_name", ("sqlite", "postgresql", "mysql"))
def test_capacity_prediction_governance_migration_compiles_for_supported_dialects(dialect_name):
    migration = _migration()
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
    assert "capacity_prediction_settings" in sql
    assert "capacity_prediction_candidate_forecasts" in sql
    assert "uq_capacity_prediction_evaluation_window" in sql
