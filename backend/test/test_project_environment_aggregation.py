# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import dataclasses
from datetime import datetime
from pathlib import Path
import sys
import types
from typing import Any, Mapping

import pytest


if "redis" not in sys.modules:
    redis_stub = types.ModuleType("redis")

    class StrictRedis:
        def __init__(self, *_args, **_kwargs):
            pass

    redis_stub.StrictRedis = StrictRedis
    redis_stub.Redis = StrictRedis
    redis_stub.exceptions = types.SimpleNamespace(LockNotOwnedError=RuntimeError)
    sys.modules["redis"] = redis_stub

from celery_tasks.tasks import storages
import models


STORAGES_PATH = Path(storages.__file__)
MONITOR_PATH = STORAGES_PATH.parents[1] / "manager" / "storagePulseMonitor.py"


def _require(name: str):
    value = getattr(storages, name, None)
    assert callable(value), f"C2 requires storages.{name}()"
    return value


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: getattr(value, field.name) for field in dataclasses.fields(value)}
    return None


def _group_rows(value: Any):
    mapping = _as_mapping(value)
    if mapping is not None:
        if "group_id" in mapping:
            yield value, mapping
        for child in mapping.values():
            yield from _group_rows(child)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for child in value:
            yield from _group_rows(child)


class SnapshotResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return [dict(row) for row in self._rows]


class SnapshotSession:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []
        self.closed = False

    def execute(self, statement):
        self.statements.append(statement)
        active_rows = [
            row
            for row in self.rows
            if row["cluster_active"]
            and row["environment_active"]
            and row["group_enable_monitoring"]
        ]
        return SnapshotResult(active_rows)

    def close(self):
        self.closed = True


def test_collection_snapshot_is_one_scalar_query_detached_and_fresh_next_round():
    load_snapshot = _require("load_collection_snapshot")
    database_rows = [
        {
            "storage_cluster_id": 1,
            "cluster_active": True,
            "project_environment_id": 10,
            "environment_active": True,
            "group_id": 100,
            "group_enable_monitoring": True,
            "volume_id": 1000,
            "qtree_id": None,
        }
    ]

    first_session = SnapshotSession(database_rows)
    first_snapshot = load_snapshot(first_session)
    assert len(first_session.statements) == 1
    sql = str(first_session.statements[0]).lower()
    assert "storage_clusters" in sql
    assert "project_storage_environments" in sql
    assert "groups" in sql
    assert "join" in sql
    first_session.close()

    first_rows = list(_group_rows(first_snapshot))
    assert len(first_rows) == 1
    assert first_rows[0][1]["project_environment_id"] == 10
    assert first_rows[0][1]["group_id"] == 100
    assert first_session.closed

    database_rows[0]["project_environment_id"] = 20
    database_rows.extend(
        {
            **database_rows[0],
            "group_id": group_id,
        }
        for group_id in range(101, 111)
    )
    second_session = SnapshotSession(database_rows)
    second_snapshot = load_snapshot(second_session)

    assert len(second_session.statements) == 1
    assert first_rows[0][1]["project_environment_id"] == 10
    assert {row[1]["project_environment_id"] for row in _group_rows(second_snapshot)} == {20}
    assert len(list(_group_rows(second_snapshot))) == 11


def _literal_keyword(call: ast.Call, name: str) -> int:
    keyword = next((item for item in call.keywords if item.arg == name), None)
    assert keyword is not None, f"missing {name}=..."
    value = ast.literal_eval(keyword.value)
    assert isinstance(value, int)
    return value


def test_storage_collection_lock_outlives_celery_hard_limit():
    module = ast.parse(STORAGES_PATH.read_text(encoding="utf-8"))
    task = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "storages_schedule_fetching_task"
    )
    task_decorator = next(
        decorator
        for decorator in task.decorator_list
        if isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and decorator.func.attr == "task"
    )
    lock_call = next(
        node
        for node in ast.walk(task)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "redis_lock"
    )

    assert _literal_keyword(lock_call, "expires") > _literal_keyword(
        task_decorator, "time_limit"
    )


class Transaction:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self

    def __exit__(self, exc_type, _exc, _tb):
        if exc_type is None:
            self.session.commits += 1
        else:
            self.session.rollbacks += 1
        return False


class WriteSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def begin(self):
        return Transaction(self)

    def close(self):
        self.closed = True


class FakeClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_collection_round_isolates_cluster_failures_and_closes_clients():
    run_round = _require("run_collection_round")
    sessions = []
    monitors = []
    collected = []

    def session_factory():
        session = WriteSession()
        sessions.append(session)
        return session

    class Monitor:
        def __init__(self, db, _logger, cluster):
            self.db = db
            self.cluster_id = cluster["storage_cluster_id"]
            self.client = FakeClient()
            monitors.append(self)

        def collect_postgres(self):
            collected.append(self.cluster_id)
            if self.cluster_id == 1:
                raise RuntimeError("cluster unavailable")
            return {"storage_cluster_id": self.cluster_id}

        def close(self):
            self.client.close()

    def questdb_writer(_cluster, metrics):
        if metrics["storage_cluster_id"] == 2:
            raise RuntimeError("questdb unavailable")

    run_round(
        tuple({"storage_cluster_id": cluster_id} for cluster_id in (1, 2, 3)),
        session_factory=session_factory,
        monitor_factory=Monitor,
        questdb_writer=questdb_writer,
        logger=storages.logger,
    )

    assert collected == [1, 2, 3]
    assert len({id(monitor.db) for monitor in monitors}) == 3
    assert [session.rollbacks for session in sessions] == [1, 0, 0]
    assert [session.commits for session in sessions] == [0, 1, 1]
    assert all(session.closed for session in sessions)
    assert all(monitor.client.closed for monitor in monitors)


class RowcountSession:
    def __init__(self, rowcount):
        self.rowcount = rowcount
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return types.SimpleNamespace(rowcount=self.rowcount)


def test_stale_snapshot_group_update_is_guarded_by_environment_and_enabled_state():
    apply_update = _require("apply_group_snapshot_update")
    snapshot = {
        "group_id": 100,
        "project_environment_id": 10,
        "group_enable_monitoring": True,
    }
    stale_session = RowcountSession(rowcount=0)

    applied = apply_update(stale_session, snapshot, {"used": 99.0})

    sql = str(stale_session.statement).lower()
    assert "groups" in sql
    assert "id" in sql
    assert "project_environment_id" in sql
    assert "enable_monitoring" in sql
    assert applied is False


def test_project_totals_refresh_only_for_complete_successful_projects(db_session):
    finalize = _require("finalize_project_totals")
    environment_model = getattr(models, "ProjectStorageEnvironment", None)
    assert environment_model is not None, "C1 requires ProjectStorageEnvironment"

    previous = datetime(2026, 7, 12, 10, 0, 0)
    collected_at = datetime(2026, 7, 13, 10, 0, 0)
    projects = [
        models.Project(
            id=1,
            name="partial-project",
            limit=999,
            soft_limit=888,
            used=777,
            use_ratio=77.78,
            soft_use_ratio=87.5,
            updated_at=previous,
        ),
        models.Project(
            id=2,
            name="complete-project",
            limit=9,
            soft_limit=8,
            used=7,
            use_ratio=6,
            soft_use_ratio=5,
            updated_at=previous,
        ),
    ]
    clusters = [
        models.StorageCluster(id=cluster_id, name=f"cluster-{cluster_id}", storage_type="netapp")
        for cluster_id in (1, 2, 3)
    ]
    environments = [
        environment_model(
            id=11,
            project_id=1,
            storage_cluster_id=1,
            name="partial-a",
            is_active=True,
            limit=100,
            soft_limit=80,
            used=20,
            use_ratio=20,
            soft_use_ratio=25,
            collection_status="success",
        ),
        environment_model(
            id=12,
            project_id=1,
            storage_cluster_id=2,
            name="partial-b",
            is_active=True,
            limit=200,
            soft_limit=160,
            used=40,
            use_ratio=20,
            soft_use_ratio=25,
            collection_status="failed",
        ),
        environment_model(
            id=21,
            project_id=2,
            storage_cluster_id=3,
            name="complete",
            is_active=True,
            limit=60,
            soft_limit=50,
            used=30,
            use_ratio=50,
            soft_use_ratio=60,
            collection_status="success",
        ),
    ]
    db_session.add_all([*projects, *clusters, *environments])
    db_session.commit()

    finalize(
        db_session,
        environment_results={11: True, 12: False, 21: True},
        collected_at=collected_at,
    )
    db_session.commit()
    db_session.expire_all()

    partial = db_session.query(models.Project).filter_by(id=1).one()
    assert (
        partial.limit,
        partial.soft_limit,
        partial.used,
        partial.use_ratio,
        partial.soft_use_ratio,
        partial.updated_at,
    ) == (999, 888, 777, 77.78, 87.5, previous)

    complete = db_session.query(models.Project).filter_by(id=2).one()
    assert (
        complete.limit,
        complete.soft_limit,
        complete.used,
        complete.use_ratio,
        complete.soft_use_ratio,
        complete.updated_at,
    ) == (60, 50, 30, 50, 60, collected_at)


def _outcome_monitor_factory(failing_clusters):
    class OutcomeMonitor:
        def __init__(self, _db, _logger, cluster):
            self.cluster_id = cluster["storage_cluster_id"]
            self.client = FakeClient()

        def collect_postgres(self):
            if self.cluster_id in failing_clusters:
                raise RuntimeError(f"cluster {self.cluster_id} failed")
            return {"storage_cluster_id": self.cluster_id}

        def close(self):
            self.client.close()

    return OutcomeMonitor


def test_collection_round_raises_when_all_cluster_postgres_collections_fail():
    run_round = _require("run_collection_round")
    sessions = []

    def session_factory():
        session = WriteSession()
        sessions.append(session)
        return session

    snapshot = tuple(
        {
            "storage_cluster_id": cluster_id,
            "project_environment_id": cluster_id * 10,
        }
        for cluster_id in (1, 2)
    )

    with pytest.raises(RuntimeError, match="all storage clusters failed"):
        run_round(
            snapshot,
            session_factory=session_factory,
            monitor_factory=_outcome_monitor_factory({1, 2}),
            questdb_writer=lambda *_args: None,
            logger=storages.logger,
        )

    assert [session.rollbacks for session in sessions] == [1, 1]


def test_collection_round_partial_failure_returns_success_failure_summary():
    run_round = _require("run_collection_round")
    snapshot = tuple(
        {
            "storage_cluster_id": cluster_id,
            "project_environment_id": cluster_id * 10,
        }
        for cluster_id in (1, 2, 3)
    )

    summary = run_round(
        snapshot,
        session_factory=WriteSession,
        monitor_factory=_outcome_monitor_factory({1}),
        questdb_writer=lambda *_args: None,
        logger=storages.logger,
    )

    assert summary["succeeded_clusters"] == (2, 3)
    assert summary["failed_clusters"] == (1,)
    assert summary["environment_results"] == {10: False, 20: True, 30: True}


def test_unused_storage_config_is_not_loaded_or_carried_in_collection_snapshot():
    monitor_module = ast.parse(MONITOR_PATH.read_text(encoding="utf-8"))
    config_consumers = [
        node
        for node in ast.walk(monitor_module)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
        and node.attr == "config"
        and isinstance(node.ctx, ast.Load)
    ]
    assert config_consumers == []

    storages_module = ast.parse(STORAGES_PATH.read_text(encoding="utf-8"))
    task = next(
        node
        for node in storages_module.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "storages_schedule_fetching_task"
    )
    task_calls = {
        node.func.id
        for node in ast.walk(task)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "load_storage_config_snapshot" not in task_calls

    run_round = next(
        node
        for node in storages_module.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_collection_round"
    )
    parameters = {
        argument.arg
        for argument in (*run_round.args.args, *run_round.args.kwonlyargs)
    }
    assert "storage_config" not in parameters


class DummyLogger:
    def info(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass


def test_isilon_collection_uses_volume_target_without_creating_null_qtree():
    monitor = object.__new__(storages.StoragePulseMonitor)
    monitor.storage_type = "isilon"
    monitor.fetch_aggregates = lambda: []
    monitor.fetch_user_quotas = lambda: ([object()], [])
    synced_models = []

    def sync(_data, model, *_args, **_kwargs):
        synced_models.append(model)

    monitor.sync_data_to_postgres = sync
    monitor._create_null_qtrees_for_volumes = lambda: pytest.fail(
        "Isilon must not create name='null' qtrees"
    )
    monitor.fetch_qtrees = lambda: pytest.fail("Isilon must not fetch qtrees")
    monitor.update_null_qtree_from_volume = lambda: None
    monitor.calculate_volume_allocation = lambda: None
    monitor.aggregate_group_usage = lambda: None
    monitor.aggregate_environment_usage = lambda: None
    monitor.aggregate_cluster_usage = lambda **_kwargs: None

    monitor.execute_data_collection(include_questdb=False)

    assert models.Volume in synced_models
    assert models.Qtree not in synced_models


def test_environment_aggregation_counts_shared_volume_once(db_session):
    cluster = models.StorageCluster(
        id=1, name="isilon-a", storage_type="isilon", is_active=True
    )
    project = models.Project(id=1, name="project-volume")
    environment = models.ProjectStorageEnvironment(
        id=1,
        project_id=1,
        storage_cluster_id=1,
        name="isilon-a",
        is_active=True,
    )
    volume = models.Volume(
        id=1,
        storage_cluster_id=1,
        name="/ifs/project",
        limit=100,
        soft_limit=80,
        used=50,
        use_ratio=50,
        soft_use_ratio=62.5,
    )
    groups = [
        models.Group(
            id=group_id,
            project_id=1,
            project_environment_id=1,
            storage_cluster_id=1,
            volume_id=1,
            name=f"group-{group_id}",
            enable_monitoring=True,
            associate_multiple_groups=False,
            limit=100,
            soft_limit=80,
            used=50,
            use_ratio=50,
            soft_use_ratio=62.5,
        )
        for group_id in (1, 2)
    ]
    db_session.add_all([cluster, project, environment, volume, *groups])
    db_session.commit()
    monitor = object.__new__(storages.StoragePulseMonitor)
    monitor.db = db_session
    monitor.storage_cluster_id = 1

    monitor.aggregate_environment_usage()
    db_session.expire(environment)

    assert (
        environment.limit,
        environment.soft_limit,
        environment.used,
        environment.use_ratio,
        environment.soft_use_ratio,
    ) == (100, 80, 50, 50, 62.5)


def test_netapp_regular_qtree_remains_the_group_storage_target(db_session):
    cluster = models.StorageCluster(
        id=1, name="netapp-a", storage_type="netapp", is_active=True
    )
    project = models.Project(id=1, name="project-qtree")
    environment = models.ProjectStorageEnvironment(
        id=1,
        project_id=1,
        storage_cluster_id=1,
        name="netapp-a",
        is_active=True,
    )
    volume = models.Volume(id=1, storage_cluster_id=1, name="volume-a")
    qtree = models.Qtree(
        id=1,
        storage_cluster_id=1,
        volume_id=1,
        name="qtree-a",
        limit=100,
        soft_limit=80,
        used=25,
        use_ratio=25,
        soft_use_ratio=31.25,
    )
    group = models.Group(
        id=1,
        project_id=1,
        project_environment_id=1,
        storage_cluster_id=1,
        qtree_id=1,
        name="group-qtree",
        enable_monitoring=True,
        associate_multiple_groups=False,
    )
    db_session.add_all([cluster, project, environment, volume, qtree, group])
    db_session.commit()
    snapshot = {
        "storage_type": "netapp",
        "storage_cluster_name": "netapp-a",
        "rows": ({"group_id": 1, "project_environment_id": 1},),
    }
    monitor = storages.StoragePulseMonitor(
        db_session,
        DummyLogger(),
        storage_cluster_id=1,
        snapshot=snapshot,
    )

    monitor._aggregate_group_usage_netapp()
    db_session.expire(group)

    assert group.qtree_id == 1
    assert group.volume_id is None
    assert (
        group.limit,
        group.soft_limit,
        group.used,
        group.use_ratio,
        group.soft_use_ratio,
    ) == (100, 80, 25, 25, 31.25)
