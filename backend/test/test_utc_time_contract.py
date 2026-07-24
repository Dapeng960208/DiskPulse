# -*- coding: utf-8 -*-
import ast
from datetime import datetime, timedelta, timezone
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

import models
from schemas.dashboardSchema import DashboardScope


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = BACKEND_ROOT / "migrate" / "versions" / "000000000025_utc_time_contract.py"


def _utc_time_contract_migration():
    spec = importlib.util.spec_from_file_location(MIGRATION_PATH.stem, MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_every_legacy_business_instant_uses_the_utc_datetime_type():
    instant_columns = (
        (models.User, "updated_at"),
        (models.Project, "updated_at"),
        (models.ProjectMembership, "created_at"),
        (models.ProjectMembership, "updated_at"),
        (models.AuditEvent, "occurred_at"),
        (models.StorageCluster, "created_at"),
        (models.StorageCluster, "updated_at"),
        (models.StorageUsage, "access_time"),
        (models.StorageAlerts, "next_attempt_at"),
        (models.StorageBackUpRecord, "start_time"),
        (models.AIConversation, "created_at"),
        (models.AIAuditLog, "finished_at"),
    )

    for model, column_name in instant_columns:
        assert isinstance(model.__table__.c[column_name].type, models.UTCDateTime)


def test_models_cannot_reintroduce_plain_datetime_columns_or_a_bare_clock():
    source = Path(models.__file__).read_text(encoding="utf-8")

    assert "Column(DateTime" not in source
    assert "datetime.now" not in source


def test_persistence_paths_cannot_reintroduce_a_bare_datetime_clock():
    persistence_paths = (
        BACKEND_ROOT / "models.py",
        BACKEND_ROOT / "crud",
        BACKEND_ROOT / "services",
        BACKEND_ROOT / "routers",
        BACKEND_ROOT / "celery_tasks",
    )
    violations: list[str] = []

    for path in persistence_paths:
        source_paths = (path,) if path.is_file() else path.rglob("*.py")
        for source_path in source_paths:
            tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "datetime"
                    and node.func.attr in {"now", "utcnow"}
                ):
                    violations.append(f"{source_path.relative_to(BACKEND_ROOT)}:{node.lineno}")

    assert violations == []


def test_schema_datetime_serialization_uses_utc_z_for_unhandled_response_models():
    scope = DashboardScope(
        mode="global",
        start_time=datetime(2026, 7, 23, 2, 30, tzinfo=timezone.utc),
        end_time=datetime(2026, 7, 23, 3, 30, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 23, 4, 30, tzinfo=timezone.utc),
    )

    assert scope.model_dump(mode="json") == {
        "mode": "global",
        "project_id": None,
        "project_name": None,
        "start_time": "2026-07-23T02:30:00Z",
        "end_time": "2026-07-23T03:30:00Z",
        "updated_at": "2026-07-23T04:30:00Z",
    }


def test_utc_time_migration_covers_every_utc_model_column_once():
    migration = _utc_time_contract_migration()
    model_columns = {
        (table.name, column.name)
        for table in models.Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, models.UTCDateTime)
    }

    assert len(migration.LEGACY_INSTANT_COLUMNS) == len(set(migration.LEGACY_INSTANT_COLUMNS))
    assert set(migration.LEGACY_INSTANT_COLUMNS) == model_columns


def test_utc_time_migration_refuses_nonempty_postgresql_before_any_ddl():
    migration = _utc_time_contract_migration()
    statements: list[str] = []

    class ExistingRows:
        def scalar(self):
            return True

    class PostgreSQLBind:
        dialect = SimpleNamespace(name="postgresql")

        def execute(self, statement):
            statements.append(str(statement))
            return ExistingRows()

    class MigrationOp:
        def get_bind(self):
            return PostgreSQLBind()

        def get_context(self):
            return SimpleNamespace(as_sql=False)

        def execute(self, statement):
            statements.append(str(statement))

        def add_column(self, *_args, **_kwargs):
            raise AssertionError("the migration must validate data before DDL")

    migration.op = MigrationOp()

    with pytest.raises(RuntimeError, match="empty development database"):
        migration.upgrade()

    assert statements
    assert not any("ALTER TABLE" in statement for statement in statements)


@pytest.mark.parametrize("dialect_name", ("sqlite", "postgresql", "mysql"))
def test_utc_time_migration_compiles_for_supported_dialects(dialect_name):
    migration = _utc_time_contract_migration()
    output = io.StringIO()
    migration.op = Operations(
        MigrationContext.configure(
            dialect_name=dialect_name,
            opts={"as_sql": True, "output_buffer": output},
        )
    )

    migration.upgrade()
    migration.downgrade()

    assert "time_zone" in output.getvalue().lower()
    if dialect_name == "postgresql":
        assert "SET LOCAL lock_timeout" in output.getvalue()


def test_postgresql_model_round_trip_normalizes_an_aware_instant_to_utc(session_factory):
    session = session_factory()
    value = datetime(2026, 7, 23, 10, 30, tzinfo=timezone(timedelta(hours=8)))
    user = models.User(rd_username="utc-contract", updated_at=value)
    session.add(user)
    session.commit()
    session.expire_all()

    restored = session.get(models.User, user.id)
    session.close()

    assert restored.updated_at == datetime(2026, 7, 23, 2, 30, tzinfo=timezone.utc)
