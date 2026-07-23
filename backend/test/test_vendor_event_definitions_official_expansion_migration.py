# -*- coding: utf-8 -*-
import importlib
from collections import Counter
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from appConfig import base_config


BACKEND_ROOT = Path(__file__).resolve().parents[1]
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
EXPECTED_SRS_CODES = {
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


def _catalog():
    return importlib.import_module(
        "scripts.initialize_vendor_event_definitions"
    ).CATALOG_DEFINITIONS


def test_official_fault_expansion_is_the_current_compatibility_head():
    scripts = ScriptDirectory.from_config(_alembic_config())

    assert scripts.get_heads() == [REVISION]
    assert scripts.get_revision(REVISION).down_revision == PREVIOUS_REVISION


def test_official_catalog_evidence_is_preserved_in_the_initializer():
    rows = _catalog()
    by_key = {(row["storage_type"], row["event_code"]): row for row in rows}
    assert EXPECTED_ADDITIONAL_CODES <= by_key.keys()
    assert EXPECTED_SRS_CODES <= by_key.keys()

    powerscale_rows = [
        row
        for row in rows
        if row["official_reference_url"] == "https://dl.dell.com/content/docu96961"
    ]
    netapp_raid_rows = [
        row
        for row in rows
        if row["official_reference_url"]
        == "https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html"
    ]
    assert len(powerscale_rows) == 499
    assert len(netapp_raid_rows) == 152
    assert Counter(row["default_severity"] for row in netapp_raid_rows) == {
        "error": 104,
        "critical": 48,
    }
    assert all(
        row["storage_type"] == "isilon"
        and row["review_status"] == "reviewed"
        and row["association_type"] != "unknown"
        and row["version_scope"]
        == "PowerScale OneFS Event Reference Guide, October 2021"
        and row["recommended_solution_zh"]
        for row in powerscale_rows
    )
    assert all(
        row["storage_type"] == "netapp"
        and row["review_status"] == "reviewed"
        and row["association_type"] != "unknown"
        and row["version_scope"] == "ONTAP 9.14.1 RAID EMS reference"
        and row["recommended_solution_zh"]
        for row in netapp_raid_rows
    )


def test_018_keeps_the_revision_chain_without_writing_catalog_data(
    monkeypatch, tmp_path
):
    database_url = f"sqlite:///{(tmp_path / 'compatibility-head.sqlite').as_posix()}"
    alembic_config = _alembic_config()
    monkeypatch.setattr(base_config, "get_sqlalchemy_database_url", lambda: database_url)

    command.stamp(alembic_config, BASE_REVISION)
    command.upgrade(alembic_config, REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                sa.text("SELECT COUNT(*) FROM vendor_event_definitions")
            ).scalar_one() == 0
    finally:
        engine.dispose()

    command.downgrade(alembic_config, PREVIOUS_REVISION)
    command.upgrade(alembic_config, REVISION)
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                sa.text("SELECT COUNT(*) FROM vendor_event_definitions")
            ).scalar_one() == 0
    finally:
        engine.dispose()
