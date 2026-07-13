# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

import models


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "backfill_project_storage_environments.py"
)


def _backfill_module():
    assert SCRIPT_PATH.exists(), "M0/M2 requires the standalone backfill script"
    spec = importlib.util.spec_from_file_location("project_environment_backfill", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_resources(db_session):
    db_session.add_all(
        [
            models.Project(id=1, name="project-a"),
            models.Project(id=2, name="project-b"),
            models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"),
            models.StorageCluster(id=2, name="cluster-b", storage_type="netapp"),
            models.Volume(id=1, storage_cluster_id=1, name="volume-a"),
            models.Volume(id=2, storage_cluster_id=2, name="volume-b"),
            models.Qtree(id=1, storage_cluster_id=1, volume_id=1, name="qtree-a"),
            models.Qtree(id=2, storage_cluster_id=2, volume_id=2, name="qtree-b"),
            models.Qtree(id=3, storage_cluster_id=1, volume_id=1, name="null"),
            models.User(id=1, rd_username="alice"),
        ]
    )
    db_session.commit()


def test_audit_reports_all_legacy_binding_issue_counts_and_ids(db_session):
    module = _backfill_module()
    _seed_resources(db_session)
    groups = [
        models.Group(id=1, project_id=None, storage_cluster_id=1, qtree_id=1, name="missing-project"),
        models.Group(id=2, project_id=1, storage_cluster_id=None, qtree_id=1, name="missing-cluster"),
        models.Group(id=3, project_id=1, storage_cluster_id=1, name="missing-target"),
        models.Group(id=4, project_id=1, storage_cluster_id=1, qtree_id=2, name="cross-cluster"),
        models.Group(id=5, project_id=1, storage_cluster_id=1, qtree_id=3, name="null-qtree"),
        models.Group(id=6, project_id=1, storage_cluster_id=1, qtree_id=1, name="duplicate-pair"),
        models.Group(id=7, project_id=2, storage_cluster_id=1, qtree_id=1, name="shared-resource"),
    ]
    db_session.add_all(groups)
    db_session.add_all(
        [
            models.StorageUsage(id=1, group_id=6, user_id=1),
            models.StorageUsage(id=2, group_id=6, user_id=1),
        ]
    )
    db_session.commit()

    audit = module.audit_legacy_storage_bindings(db_session)

    assert audit["missing_project"] == {"count": 1, "group_ids": (1,)}
    assert audit["missing_cluster"] == {"count": 1, "group_ids": (2,)}
    assert audit["missing_target"] == {"count": 1, "group_ids": (3,)}
    assert audit["cross_cluster_qtree"] == {"count": 1, "group_ids": (4,)}
    assert audit["null_qtree"] == {"count": 1, "group_ids": (5,)}
    assert audit["repeated_project_cluster"] == {
        "count": 1,
        "keys": ((1, 1),),
    }
    assert audit["shared_resource"] == {
        "count": 1,
        "keys": (("qtree", 1),),
    }
    assert audit["duplicate_storage_usage"] == {
        "count": 1,
        "keys": ((6, 1),),
    }
    assert audit["has_blockers"] is True


def test_backfill_defaults_to_dry_run_and_blocked_apply_has_no_partial_writes(db_session):
    module = _backfill_module()
    _seed_resources(db_session)
    db_session.add_all(
        [
            models.Group(id=1, project_id=1, storage_cluster_id=1, qtree_id=1, name="valid"),
            models.Group(id=2, project_id=None, storage_cluster_id=2, qtree_id=2, name="blocked"),
        ]
    )
    db_session.commit()

    dry_run = module.backfill_project_storage_environments(db_session)

    assert dry_run["applied"] is False
    assert dry_run["planned_environments"] == 1
    assert dry_run["planned_groups"] == 1
    assert db_session.query(models.ProjectStorageEnvironment).count() == 0
    assert all(group.project_environment_id is None for group in db_session.query(models.Group))

    with pytest.raises(ValueError, match="blocking legacy storage bindings"):
        module.backfill_project_storage_environments(db_session, apply=True)

    assert db_session.query(models.ProjectStorageEnvironment).count() == 0
    assert all(group.project_environment_id is None for group in db_session.query(models.Group))


def test_clean_apply_converts_targets_preserves_null_metrics_and_is_idempotent(db_session):
    module = _backfill_module()
    _seed_resources(db_session)
    db_session.add(
        models.Qtree(id=4, storage_cluster_id=1, volume_id=1, name="qtree-c")
    )
    db_session.add_all(
        [
            models.Group(id=1, project_id=1, storage_cluster_id=1, qtree_id=1, name="group-a"),
            models.Group(id=2, project_id=1, storage_cluster_id=1, qtree_id=4, name="group-b"),
            models.Group(id=3, project_id=1, storage_cluster_id=2, qtree_id=2, name="group-c"),
        ]
    )
    db_session.query(models.Qtree).filter_by(id=2).update({"name": "null"})
    db_session.commit()

    result = module.backfill_project_storage_environments(db_session, apply=True)

    assert result == {
        "applied": True,
        "created_environments": 2,
        "updated_groups": 3,
    }
    environments = db_session.query(models.ProjectStorageEnvironment).order_by(
        models.ProjectStorageEnvironment.storage_cluster_id
    ).all()
    assert [(item.project_id, item.storage_cluster_id, item.name) for item in environments] == [
        (1, 1, "cluster-a"),
        (1, 2, "cluster-b"),
    ]
    assert all(
        (
            item.limit,
            item.soft_limit,
            item.used,
            item.use_ratio,
            item.soft_use_ratio,
            item.collection_status,
            item.last_collected_at,
        )
        == (None, None, None, None, None, "pending", None)
        for item in environments
    )
    groups = {group.id: group for group in db_session.query(models.Group)}
    assert groups[1].project_environment_id == environments[0].id
    assert groups[1].qtree_id == 1 and groups[1].volume_id is None
    assert groups[2].project_environment_id == environments[0].id
    assert groups[2].qtree_id == 4 and groups[2].volume_id is None
    assert groups[3].project_environment_id == environments[1].id
    assert groups[3].qtree_id is None and groups[3].volume_id == 2

    second = module.backfill_project_storage_environments(db_session, apply=True)

    assert second == {
        "applied": True,
        "created_environments": 0,
        "updated_groups": 0,
    }
    assert db_session.query(models.ProjectStorageEnvironment).count() == 2
