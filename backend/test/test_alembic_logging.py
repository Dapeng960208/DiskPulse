# -*- coding: utf-8 -*-
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from appConfig import base_config


def test_alembic_upgrade_preserves_existing_log_capture(monkeypatch, tmp_path, caplog):
    """Running migrations must not remove the host application's log handlers."""
    database_url = f"sqlite:///{(tmp_path / 'alembic-logging.sqlite').as_posix()}"
    alembic_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    monkeypatch.setattr(base_config, "get_sqlalchemy_database_url", lambda: database_url)

    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    capture_logger = logging.getLogger("alembic-log-capture-regression")

    try:
        command.upgrade(alembic_config, "000000000001")
        caplog.clear()
        with caplog.at_level("INFO", logger=capture_logger.name):
            capture_logger.info("migration kept existing log capture")

        assert any(
            record.name == capture_logger.name
            and record.getMessage() == "migration kept existing log capture"
            for record in caplog.records
        )
    finally:
        root_logger.handlers[:] = original_handlers
        root_logger.setLevel(original_level)
