# -*- coding: utf-8 -*-
import importlib.util
from collections import Counter
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from appConfig import base_config


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    BACKEND_ROOT
    / "migrate"
    / "versions"
    / "000000000018_add_official_vendor_fault_events.py"
)
BASE_REVISION = "000000000015"
PREVIOUS_REVISION = "000000000017"
REVISION = "000000000018"
EXPECTED_ADDITIONAL_CODES = {
    ("netapp", "raid.disk.illegalAttach"),
    ("netapp", "raid.disk.io.toFailedDisk"),
    ("netapp", "raid.disk.mcc.mismatch"),
    ("netapp", "raid.disk.owner.change.fail"),
    ("netapp", "raid.disk.predictiveFailure"),
    ("netapp", "raid.disk.replace.job.failed"),
    ("netapp", "disk.partition.exceeded"),
    ("netapp", "disk.min.OS.error"),
    ("netapp", "disk.max.partitions"),
    ("netapp", "callhome.raid.no.recover"),
    ("netapp", "raid.assim.disk.badlabelversion"),
    ("isilon", "100010023"),
    ("isilon", "400120001"),
}


def _alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


def _migration_module():
    spec = importlib.util.spec_from_file_location(MIGRATION_PATH.stem, MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_official_fault_expansion_is_the_current_alembic_head():
    scripts = ScriptDirectory.from_config(_alembic_config())

    assert scripts.get_heads() == [REVISION]
    assert scripts.get_revision(REVISION).down_revision == PREVIOUS_REVISION


def test_official_fault_expansion_upserts_only_evidence_backed_codes(monkeypatch, tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'vendor-event-expansion.sqlite').as_posix()}"
    alembic_config = _alembic_config()
    monkeypatch.setattr(base_config, "get_sqlalchemy_database_url", lambda: database_url)
    migration = _migration_module()

    command.stamp(alembic_config, BASE_REVISION)
    command.upgrade(alembic_config, PREVIOUS_REVISION)
    command.upgrade(alembic_config, REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                sa.text(
                    "SELECT storage_type, event_code, association_type, "
                    "official_reference_url, version_scope, review_status, "
                    "recommended_solution_zh FROM vendor_event_definitions"
                )
            ).mappings().all()
            added = [
                row
                for row in rows
                if (row["storage_type"], row["event_code"])
                in EXPECTED_ADDITIONAL_CODES
            ]
            assert len(rows) == 81
            assert {
                (row["storage_type"], row["event_code"])
                for row in added
            } == EXPECTED_ADDITIONAL_CODES
            assert all(
                row["review_status"] == "reviewed"
                and row["association_type"] == "fault_log"
                and row["official_reference_url"]
                and row["version_scope"]
                and row["recommended_solution_zh"]
                for row in added
            )
            assert Counter(
                (row["storage_type"], row["review_status"]) for row in rows
            ) == {
                ("netapp", "reviewed"): 44,
                ("netapp", "pending"): 10,
                ("isilon", "reviewed"): 2,
                ("isilon", "pending"): 25,
            }
    finally:
        engine.dispose()

    command.downgrade(alembic_config, PREVIOUS_REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                sa.text("SELECT storage_type, event_code FROM vendor_event_definitions")
            ).all()
            assert len(rows) == 68
            assert not (set(rows) & EXPECTED_ADDITIONAL_CODES)
    finally:
        engine.dispose()
