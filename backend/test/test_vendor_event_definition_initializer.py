# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
from collections import Counter
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from appConfig import base_config
BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
ALEMBIC_CONFIG = Config(str(BACKEND_ROOT / "alembic.ini"))


def _initializer():
    return importlib.import_module("scripts.initialize_vendor_event_definitions")


def _create_definition_table(engine: sa.Engine) -> sa.Table:
    metadata = sa.MetaData()
    table = sa.Table(
        "vendor_event_definitions",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("storage_type", sa.String(32), nullable=False),
        sa.Column("event_code", sa.String(255), nullable=False),
        sa.Column("association_type", sa.String(32), nullable=False),
        sa.Column("title_zh", sa.String(255), nullable=False),
        sa.Column("description_zh", sa.Text(), nullable=False),
        sa.Column("official_reference_url", sa.String(1000)),
        sa.Column("default_severity", sa.String(16)),
        sa.Column("version_scope", sa.String(255)),
        sa.Column("review_status", sa.String(16), nullable=False),
        sa.Column("recommended_solution_zh", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "review_status <> 'reviewed' OR recommended_solution_zh IS NOT NULL"
        ),
        sa.UniqueConstraint("storage_type", "event_code"),
    )
    metadata.create_all(engine)
    return table


def test_catalog_is_unique_complete_and_reviewed_rows_have_evidence():
    initializer = _initializer()
    rows = initializer.CATALOG_DEFINITIONS
    keys = [(row["storage_type"], row["event_code"]) for row in rows]

    assert len(rows) == 730
    assert len(set(keys)) == 730
    assert Counter((row["storage_type"], row["review_status"]) for row in rows) == {
        ("netapp", "reviewed"): 189,
        ("netapp", "pending"): 10,
        ("isilon", "reviewed"): 499,
        ("isilon", "pending"): 32,
    }
    reviewed = [row for row in rows if row["review_status"] == "reviewed"]
    assert all(
        row["association_type"] != "unknown"
        and row["official_reference_url"]
        and row["version_scope"]
        and row["recommended_solution_zh"]
        for row in reviewed
    )


def test_initializer_inserts_missing_rows_and_is_idempotent(tmp_path):
    initializer = _initializer()
    engine = sa.create_engine(
        f"sqlite:///{(tmp_path / 'initializer.sqlite').as_posix()}"
    )
    _create_definition_table(engine)
    try:
        with engine.begin() as connection:
            first = initializer.initialize_vendor_event_definitions(connection)
        with engine.begin() as connection:
            second = initializer.initialize_vendor_event_definitions(connection)

        assert first.catalog_size == 730
        assert first.matched_existing == 0
        assert first.inserted == 730
        assert first.unmanaged == 0
        assert second.catalog_size == 730
        assert second.matched_existing == 730
        assert second.inserted == 0
        assert second.unmanaged == 0
        with engine.connect() as connection:
            assert connection.execute(
                sa.text("SELECT COUNT(*) FROM vendor_event_definitions")
            ).scalar_one() == 730
    finally:
        engine.dispose()


def test_initializer_preserves_existing_and_unmanaged_rows(tmp_path):
    initializer = _initializer()
    engine = sa.create_engine(
        f"sqlite:///{(tmp_path / 'preserve-existing.sqlite').as_posix()}"
    )
    table = _create_definition_table(engine)
    first = initializer.CATALOG_DEFINITIONS[0]
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.insert(table), {**first, "title_zh": "管理员保留标题"}
            )
            connection.execute(
                sa.insert(table),
                {
                    "storage_type": "netapp",
                    "event_code": "administrator.custom.event",
                    "association_type": "unknown",
                    "title_zh": "管理员自定义事件",
                    "description_zh": "不属于内置目录。",
                    "review_status": "pending",
                    "is_active": True,
                },
            )
            result = initializer.initialize_vendor_event_definitions(connection)

        assert result.matched_existing == 1
        assert result.inserted == 729
        assert result.unmanaged == 1
        with engine.connect() as connection:
            title = connection.execute(
                sa.text(
                    "SELECT title_zh FROM vendor_event_definitions "
                    "WHERE storage_type=:storage_type AND event_code=:event_code"
                ),
                {"storage_type": first["storage_type"], "event_code": first["event_code"]},
            ).scalar_one()
            assert title == "管理员保留标题"
            assert connection.execute(
                sa.text("SELECT COUNT(*) FROM vendor_event_definitions")
            ).scalar_one() == 731
    finally:
        engine.dispose()


def test_initializer_rolls_back_the_batch_when_a_row_is_invalid(monkeypatch, tmp_path):
    initializer = _initializer()
    engine = sa.create_engine(
        f"sqlite:///{(tmp_path / 'rollback.sqlite').as_posix()}"
    )
    _create_definition_table(engine)
    invalid = {
        **initializer.CATALOG_DEFINITIONS[0],
        "event_code": "invalid.reviewed.event",
        "recommended_solution_zh": None,
    }
    monkeypatch.setattr(
        initializer,
        "CATALOG_DEFINITIONS",
        (initializer.CATALOG_DEFINITIONS[0], invalid),
    )
    try:
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                initializer.initialize_vendor_event_definitions(connection)
        with engine.connect() as connection:
            assert connection.execute(
                sa.text("SELECT COUNT(*) FROM vendor_event_definitions")
            ).scalar_one() == 0
    finally:
        engine.dispose()


def test_unified_entrypoint_runs_migrations_before_initialization(monkeypatch):
    initializer = _initializer()
    calls = []

    class BeginContext:
        def __enter__(self):
            calls.append("begin")
            return object()

        def __exit__(self, exc_type, exc, traceback):
            calls.append("commit")

    class Engine:
        def begin(self):
            return BeginContext()

        def dispose(self):
            calls.append("dispose")

    monkeypatch.setattr(
        initializer.command,
        "upgrade",
        lambda config, revision: calls.append(("upgrade", revision)),
    )
    monkeypatch.setattr(initializer, "create_engine", lambda *args, **kwargs: Engine())
    monkeypatch.setattr(
        initializer,
        "initialize_vendor_event_definitions",
        lambda connection: calls.append("initialize") or initializer.InitializationResult(
            catalog_size=730,
            matched_existing=0,
            inserted=730,
            unmanaged=0,
        ),
    )

    result = initializer.run_database_initialization()

    assert result.inserted == 730
    assert calls == [
        ("upgrade", "head"),
        "begin",
        "initialize",
        "commit",
        "dispose",
    ]


def test_markdown_renderer_rejects_unsupported_storage_type():
    initializer = _initializer()

    with pytest.raises(ValueError, match="Unsupported storage type"):
        initializer.render_event_association_markdown("unsupported")


def test_main_reports_initialization_summary(monkeypatch, capsys):
    initializer = _initializer()
    monkeypatch.setattr(
        initializer,
        "run_database_initialization",
        lambda: initializer.InitializationResult(
            catalog_size=730,
            matched_existing=725,
            inserted=5,
            unmanaged=2,
        ),
    )

    assert initializer.main() == 0
    assert capsys.readouterr().out.strip() == (
        "Vendor event definitions initialized: catalog=730, "
        "matched_existing=725, inserted=5, unmanaged=2"
    )


def test_main_returns_nonzero_and_reports_failure(monkeypatch, capsys):
    initializer = _initializer()

    def fail():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(initializer, "run_database_initialization", fail)

    assert initializer.main() == 1
    assert capsys.readouterr().err.strip() == (
        "Vendor event definition initialization failed: "
        "RuntimeError: database unavailable"
    )


@pytest.mark.parametrize(
    ("storage_type", "filename", "expected_count"),
    (
        ("netapp", "netapp-event-association-list.md", 199),
        ("isilon", "isilon-event-association-list.md", 531),
    ),
)
def test_markdown_catalogs_match_the_initializer(storage_type, filename, expected_count):
    initializer = _initializer()
    path = (
        REPOSITORY_ROOT
        / "docs"
        / "features"
        / "storage"
        / "event-association"
        / filename
    )
    expected = initializer.render_event_association_markdown(storage_type)

    assert path.read_text(encoding="utf-8") == expected
    assert expected.count("\n| `") == expected_count


def test_migrations_create_structure_without_seeding_catalog(monkeypatch, tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'structure-only.sqlite').as_posix()}"
    monkeypatch.setattr(base_config, "get_sqlalchemy_database_url", lambda: database_url)

    command.stamp(ALEMBIC_CONFIG, "000000000015")
    # This test starts from the vendor-catalog baseline rather than a full
    # application schema.  Stop at its compatibility revision so unrelated
    # later migrations do not require tables absent from this fixture.
    command.upgrade(ALEMBIC_CONFIG, "000000000018")

    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert "vendor_event_definitions" in sa.inspect(connection).get_table_names()
            assert connection.execute(
                sa.text("SELECT COUNT(*) FROM vendor_event_definitions")
            ).scalar_one() == 0
    finally:
        engine.dispose()
