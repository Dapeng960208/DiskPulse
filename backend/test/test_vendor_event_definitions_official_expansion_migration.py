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
EXPECTED_SRS_BREVITY_PENDING_CODES = {
    ("isilon", "100010005"),
    ("isilon", "100010011"),
    ("isilon", "100010012"),
    ("isilon", "100010013"),
    ("isilon", "100010025"),
    ("isilon", "100010032"),
    ("isilon", "100010033"),
    ("isilon", "100010034"),
    ("isilon", "100010038"),
    ("isilon", "100010041"),
    ("isilon", "100010045"),
    ("isilon", "100010050"),
    ("isilon", "100010056"),
    ("isilon", "100020062"),
    ("isilon", "200020012"),
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
                    "title_zh, description_zh, official_reference_url, "
                    "version_scope, review_status, recommended_solution_zh "
                    "FROM vendor_event_definitions"
                )
            ).mappings().all()
            added = [
                row
                for row in rows
                if (row["storage_type"], row["event_code"])
                in EXPECTED_ADDITIONAL_CODES
            ]
            knowledge_rows = [
                row
                for row in rows
                if (row["storage_type"], row["event_code"])
                in {
                    (definition["storage_type"], definition["event_code"])
                    for definition in migration.SRS_BREVITY_KNOWLEDGE_DEFINITIONS
                }
            ]
            pdf_reviewed_codes = {
                (definition["storage_type"], definition["event_code"])
                for definition in migration.PDF_REVIEWED_DEFINITIONS
            }
            pdf_reviewed_rows = [
                row
                for row in rows
                if (row["storage_type"], row["event_code"])
                in pdf_reviewed_codes
            ]
            assert len(rows) == 585
            assert len(pdf_reviewed_rows) == 499
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
            srs_catalog_rows = [
                row
                for row in rows
                if (row["storage_type"], row["event_code"])
                in EXPECTED_SRS_BREVITY_PENDING_CODES
            ]
            assert {
                (row["storage_type"], row["event_code"])
                for row in srs_catalog_rows
            } == EXPECTED_SRS_BREVITY_PENDING_CODES
            assert all(
                row["review_status"] == "reviewed"
                and row["association_type"] != "unknown"
                and row["official_reference_url"]
                == "https://dl.dell.com/content/docu96961"
                and row["title_zh"]
                and row["description_zh"]
                and row["version_scope"]
                == "PowerScale OneFS Event Reference Guide, October 2021"
                and row["recommended_solution_zh"]
                for row in srs_catalog_rows
            )
            assert len(knowledge_rows) == len(
                migration.SRS_BREVITY_KNOWLEDGE_DEFINITIONS
            )
            assert all(
                row["review_status"] == "reviewed"
                and row["association_type"] != "unknown"
                and row["official_reference_url"]
                == "https://dl.dell.com/content/docu96961"
                and row["recommended_solution_zh"]
                for row in pdf_reviewed_rows
            )
            assert Counter(
                (row["storage_type"], row["review_status"]) for row in rows
            ) == {
                ("netapp", "reviewed"): 44,
                ("netapp", "pending"): 10,
                ("isilon", "reviewed"): 499,
                ("isilon", "pending"): 32,
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
            assert not (
                set(rows)
                & (EXPECTED_ADDITIONAL_CODES | EXPECTED_SRS_BREVITY_PENDING_CODES)
            )
    finally:
        engine.dispose()
