# -*- coding: utf-8 -*-
import importlib
import json
import sys
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from models import StorageUsage
from schemas.usersSchema import UserSyncResult


def _task(module, name):
    return getattr(module, name).run


def _lock(granted, exits):
    @contextmanager
    def lock(name, *, expires):
        exits.append(("entered", name, expires))
        try:
            yield granted
        finally:
            exits.append(("exited", name, expires))

    return lock


def _log_text(logger, level):
    return " ".join(
        " ".join(str(argument) for argument in call.args)
        for call in getattr(logger, level).call_args_list
    )


def test_celery_beat_registers_scheduled_user_tasks_and_preserves_storage_collection():
    celery_worker = importlib.import_module("celery_worker")
    schedule = celery_worker.diskpulse_app.conf.beat_schedule

    assert schedule["ldap_users_sync_schedule_task"] == {
        "task": "celery_tasks.tasks.users.ldap_users_sync_schedule_task",
        "schedule": 28800.0,
        "options": {"expires": 28800},
    }
    hourly = schedule["user_storage_statistics_schedule_task"]
    assert hourly["task"] == (
        "celery_tasks.tasks.storages.user_storage_statistics_schedule_task"
    )
    assert hourly["schedule"].minute == {0}
    assert hourly["options"] == {"expires": 3600}
    assert schedule["storages_schedule_fetching_task"] == {
        "task": "celery_tasks.tasks.storages.storages_schedule_fetching_task",
        "schedule": 60.0,
        "options": {"expires": 120},
    }
    assert "celery_tasks.tasks.users" in sys.modules


def test_ldap_task_skips_without_lock_and_does_not_open_session(monkeypatch):
    users = importlib.import_module("celery_tasks.tasks.users")
    exits = []
    session_factory = Mock()
    sync = Mock()
    task_logger = Mock()
    monkeypatch.setattr(users, "redis_lock", _lock(False, exits))
    monkeypatch.setattr(users, "SessionLocal", session_factory)
    monkeypatch.setattr(users.usersService, "sync_ldap_users", sync)
    monkeypatch.setattr(users, "logger", task_logger)

    assert _task(users, "ldap_users_sync_schedule_task")() == {"status": "skipped"}
    session_factory.assert_not_called()
    sync.assert_not_called()
    assert exits == [
        ("entered", "ldap_users_sync_schedule_task_lock", 28800),
        ("exited", "ldap_users_sync_schedule_task_lock", 28800),
    ]
    assert "already running" in _log_text(task_logger, "info").lower()


def test_ldap_task_serializes_result_and_closes_its_session(monkeypatch):
    users = importlib.import_module("celery_tasks.tasks.users")
    exits = []
    db = Mock()
    result = UserSyncResult(
        ldap_total=7,
        created=2,
        updated=3,
        reactivated=1,
        marked_inactive=1,
    )
    monkeypatch.setattr(users, "redis_lock", _lock(True, exits))
    monkeypatch.setattr(users, "SessionLocal", Mock(return_value=db))
    sync = Mock(return_value=result)
    monkeypatch.setattr(users.usersService, "sync_ldap_users", sync)
    task_logger = Mock()
    monkeypatch.setattr(users, "logger", task_logger)

    actual = _task(users, "ldap_users_sync_schedule_task")()

    assert actual == result.model_dump()
    json.dumps(actual)
    sync.assert_called_once_with(db)
    db.close.assert_called_once_with()
    db.commit.assert_not_called()
    assert exits[-1] == ("exited", "ldap_users_sync_schedule_task_lock", 28800)
    info = _log_text(task_logger, "info").lower()
    assert "started" in info
    assert "completed" in info
    assert "created" in info and "marked_inactive" in info
    assert "duration_seconds" in info


def test_ldap_task_logs_and_reraises_session_creation_failure(monkeypatch):
    users = importlib.import_module("celery_tasks.tasks.users")
    failure = RuntimeError("PostgreSQL session unavailable")
    task_logger = Mock()
    sync = Mock()
    monkeypatch.setattr(users, "redis_lock", _lock(True, []))
    monkeypatch.setattr(users, "SessionLocal", Mock(side_effect=failure))
    monkeypatch.setattr(users.usersService, "sync_ldap_users", sync)
    monkeypatch.setattr(users, "logger", task_logger)

    with pytest.raises(RuntimeError, match="PostgreSQL session unavailable"):
        _task(users, "ldap_users_sync_schedule_task")()

    sync.assert_not_called()
    assert "ldap" in _log_text(task_logger, "exception").lower()
    assert "failed" in _log_text(task_logger, "exception").lower()


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("LDAP snapshot unavailable"),
        ValueError("LDAP username conflict"),
        OSError("database unavailable"),
    ],
)
def test_ldap_task_propagates_errors_and_closes_session(monkeypatch, error):
    users = importlib.import_module("celery_tasks.tasks.users")
    exits = []
    db = Mock()
    monkeypatch.setattr(users, "redis_lock", _lock(True, exits))
    monkeypatch.setattr(users, "SessionLocal", Mock(return_value=db))
    monkeypatch.setattr(
        users.usersService, "sync_ldap_users", Mock(side_effect=error)
    )

    with pytest.raises(type(error), match=str(error)):
        _task(users, "ldap_users_sync_schedule_task")()

    db.close.assert_called_once_with()
    assert exits[-1] == ("exited", "ldap_users_sync_schedule_task_lock", 28800)


class _QuestSession:
    def __init__(self, commit_error=None):
        self.samples = []
        self.commit_error = commit_error
        self.commit_count = 0
        self.rollback_count = 0
        self.close_count = 0

    def add_all(self, samples):
        self.samples.extend(samples)

    def commit(self):
        self.commit_count += 1
        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        self.close_count += 1


def _seed_usage_rows(session_factory):
    with session_factory() as db:
        db.add_all(
            [
                StorageUsage(
                    id=1,
                    user_id=10,
                    limit=100,
                    soft_limit=80,
                    used=30,
                    file_used=3,
                ),
                StorageUsage(
                    id=2,
                    user_id=10,
                    limit=50,
                    soft_limit=None,
                    used=15,
                    file_used=None,
                ),
                StorageUsage(
                    id=3,
                    user_id=20,
                    limit=None,
                    soft_limit=0,
                    used=None,
                    file_used=7,
                ),
                StorageUsage(
                    id=4,
                    user_id=None,
                    limit=999,
                    soft_limit=999,
                    used=999,
                    file_used=999,
                ),
            ]
        )
        db.commit()


def test_user_storage_task_aggregates_rows_with_one_consistent_sample_time(
    monkeypatch, session_factory
):
    storages = importlib.import_module("celery_tasks.tasks.storages")
    _seed_usage_rows(session_factory)
    quest = _QuestSession()
    sampled_at = datetime(2026, 7, 17, 9, 0, 0)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return sampled_at

    monkeypatch.setattr(storages, "redis_lock", _lock(True, []))
    monkeypatch.setattr(storages, "SessionLocal", session_factory)
    monkeypatch.setattr(storages, "QuestDBSessionLocal", Mock(return_value=quest))
    monkeypatch.setattr(storages, "datetime", FixedDatetime)
    task_logger = Mock()
    monkeypatch.setattr(storages, "logger", task_logger)

    result = _task(storages, "user_storage_statistics_schedule_task")()

    assert result == {"count": 2, "updated_at": sampled_at.isoformat()}
    assert quest.commit_count == 1
    assert quest.rollback_count == 0
    assert quest.close_count == 1
    samples = {int(sample.user_id): sample for sample in quest.samples}
    assert set(samples) == {10, 20}
    assert samples[10].limit == 150
    assert samples[10].soft_limit == 80
    assert samples[10].used == 45
    assert samples[10].file_used == 3
    assert samples[10].use_ratio == 30.0
    assert samples[10].soft_use_ratio == 56.25
    assert samples[20].limit == 0
    assert samples[20].soft_limit == 0
    assert samples[20].used == 0
    assert samples[20].file_used == 7
    assert samples[20].use_ratio == 0
    assert samples[20].soft_use_ratio == 0
    assert {sample.updated_at for sample in samples.values()} == {sampled_at}
    info = _log_text(task_logger, "info").lower()
    assert "started" in info
    assert "completed" in info
    assert "count" in info and "2" in info
    assert "duration_seconds" in info


def test_user_storage_task_empty_data_does_not_open_questdb(monkeypatch, session_factory):
    storages = importlib.import_module("celery_tasks.tasks.storages")
    with session_factory() as db:
        db.add(StorageUsage(id=1, user_id=None, limit=10, used=5))
        db.commit()
    quest_factory = Mock()
    monkeypatch.setattr(storages, "redis_lock", _lock(True, []))
    monkeypatch.setattr(storages, "SessionLocal", session_factory)
    monkeypatch.setattr(storages, "QuestDBSessionLocal", quest_factory)

    result = _task(storages, "user_storage_statistics_schedule_task")()

    assert result["count"] == 0
    quest_factory.assert_not_called()


def test_user_storage_task_skips_without_opening_databases(monkeypatch):
    storages = importlib.import_module("celery_tasks.tasks.storages")
    postgres_factory = Mock()
    quest_factory = Mock()
    task_logger = Mock()
    monkeypatch.setattr(storages, "redis_lock", _lock(False, []))
    monkeypatch.setattr(storages, "SessionLocal", postgres_factory)
    monkeypatch.setattr(storages, "QuestDBSessionLocal", quest_factory)
    monkeypatch.setattr(storages, "logger", task_logger)

    assert _task(storages, "user_storage_statistics_schedule_task")() == {
        "status": "skipped"
    }
    postgres_factory.assert_not_called()
    quest_factory.assert_not_called()
    assert "already running" in _log_text(task_logger, "info").lower()


def test_user_storage_task_logs_postgres_session_creation_failure(monkeypatch):
    storages = importlib.import_module("celery_tasks.tasks.storages")
    failure = RuntimeError("PostgreSQL session unavailable")
    quest_factory = Mock()
    task_logger = Mock()
    monkeypatch.setattr(storages, "redis_lock", _lock(True, []))
    monkeypatch.setattr(storages, "SessionLocal", Mock(side_effect=failure))
    monkeypatch.setattr(storages, "QuestDBSessionLocal", quest_factory)
    monkeypatch.setattr(storages, "logger", task_logger)

    with pytest.raises(RuntimeError, match="PostgreSQL session unavailable"):
        _task(storages, "user_storage_statistics_schedule_task")()

    quest_factory.assert_not_called()
    exception_log = _log_text(task_logger, "exception").lower()
    assert "postgresql" in exception_log
    assert "failed" in exception_log


def test_user_storage_task_logs_questdb_session_creation_failure(
    monkeypatch, session_factory
):
    storages = importlib.import_module("celery_tasks.tasks.storages")
    with session_factory() as db:
        db.add(StorageUsage(id=1, user_id=10, limit=100, used=50))
        db.commit()
    failure = RuntimeError("QuestDB session unavailable")
    task_logger = Mock()
    monkeypatch.setattr(storages, "redis_lock", _lock(True, []))
    monkeypatch.setattr(storages, "SessionLocal", session_factory)
    monkeypatch.setattr(storages, "QuestDBSessionLocal", Mock(side_effect=failure))
    monkeypatch.setattr(storages, "logger", task_logger)

    with pytest.raises(RuntimeError, match="QuestDB session unavailable"):
        _task(storages, "user_storage_statistics_schedule_task")()

    exception_log = _log_text(task_logger, "exception").lower()
    assert "questdb" in exception_log
    assert "failed" in exception_log


def test_user_storage_task_rolls_back_closes_and_reraises_add_all_failure(
    monkeypatch, session_factory
):
    storages = importlib.import_module("celery_tasks.tasks.storages")
    with session_factory() as db:
        db.add(StorageUsage(id=1, user_id=10, limit=100, used=50))
        db.commit()
    failure = RuntimeError("QuestDB add failed")
    quest = Mock()
    quest.add_all.side_effect = failure
    monkeypatch.setattr(storages, "redis_lock", _lock(True, []))
    monkeypatch.setattr(storages, "SessionLocal", session_factory)
    monkeypatch.setattr(storages, "QuestDBSessionLocal", Mock(return_value=quest))

    with pytest.raises(RuntimeError, match="QuestDB add failed"):
        _task(storages, "user_storage_statistics_schedule_task")()

    quest.rollback.assert_called_once_with()
    quest.close.assert_called_once_with()
    quest.commit.assert_not_called()


def test_user_storage_task_rolls_back_closes_and_reraises_questdb_commit_failure(
    monkeypatch, session_factory
):
    storages = importlib.import_module("celery_tasks.tasks.storages")
    with session_factory() as db:
        db.add(StorageUsage(id=1, user_id=10, limit=100, used=50))
        db.commit()
    failure = RuntimeError("QuestDB commit failed")
    quest = _QuestSession(commit_error=failure)
    postgres_sessions = []

    def postgres_factory():
        db = session_factory()
        postgres_sessions.append(db)
        original_close = db.close
        db.close = Mock(wraps=original_close)
        return db

    monkeypatch.setattr(storages, "redis_lock", _lock(True, []))
    monkeypatch.setattr(storages, "SessionLocal", postgres_factory)
    monkeypatch.setattr(storages, "QuestDBSessionLocal", Mock(return_value=quest))

    with pytest.raises(RuntimeError, match="QuestDB commit failed"):
        _task(storages, "user_storage_statistics_schedule_task")()

    assert len(postgres_sessions) == 1
    postgres_sessions[0].close.assert_called_once_with()
    assert quest.commit_count == 1
    assert quest.rollback_count == 1
    assert quest.close_count == 1
