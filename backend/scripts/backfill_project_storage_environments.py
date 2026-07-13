# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from sqlalchemy import func


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import SessionLocal
from models import (
    Group,
    ProjectStorageEnvironment,
    Qtree,
    StorageCluster,
    StorageUsage,
)


BLOCKING_ISSUES = (
    "missing_project",
    "missing_cluster",
    "missing_target",
    "cross_cluster_qtree",
    "shared_resource",
    "duplicate_storage_usage",
)


def _group_issue(ids):
    ids = tuple(sorted(ids))
    return {"count": len(ids), "group_ids": ids}


def _key_issue(keys):
    keys = tuple(sorted(keys))
    return {"count": len(keys), "keys": keys}


def _scalars(query):
    return (row[0] for row in query.all())


def audit_legacy_storage_bindings(db):
    missing_project = _scalars(db.query(Group.id).filter(Group.project_id.is_(None)))
    missing_cluster = _scalars(db.query(Group.id).filter(Group.storage_cluster_id.is_(None)))
    missing_target = db.query(Group.id).filter(
        Group.qtree_id.is_(None), Group.volume_id.is_(None)
    )
    missing_target = _scalars(missing_target)
    cross_cluster_qtree = _scalars(db.query(Group.id).join(Qtree, Group.qtree_id == Qtree.id).filter(
        Group.storage_cluster_id.isnot(None),
        Qtree.storage_cluster_id.isnot(None),
        Group.storage_cluster_id != Qtree.storage_cluster_id,
    ))
    null_qtree = _scalars(db.query(Group.id).join(Qtree, Group.qtree_id == Qtree.id).filter(
        Qtree.name == "null"
    ))
    repeated_project_cluster = db.query(Group.project_id, Group.storage_cluster_id).filter(
        Group.project_id.isnot(None), Group.storage_cluster_id.isnot(None)
    ).group_by(Group.project_id, Group.storage_cluster_id).having(func.count(Group.id) > 1).all()

    shared_qtrees = _scalars(db.query(Group.qtree_id).filter(Group.qtree_id.isnot(None)).group_by(
        Group.qtree_id
    ).having(func.count(Group.id) > 1))
    shared_volumes = _scalars(db.query(Group.volume_id).filter(Group.volume_id.isnot(None)).group_by(
        Group.volume_id
    ).having(func.count(Group.id) > 1))
    shared_resource = [*(('qtree', item) for item in shared_qtrees)]
    shared_resource.extend(('volume', item) for item in shared_volumes)

    duplicate_storage_usage = db.query(
        StorageUsage.group_id, StorageUsage.user_id
    ).filter(
        StorageUsage.group_id.isnot(None), StorageUsage.user_id.isnot(None)
    ).group_by(StorageUsage.group_id, StorageUsage.user_id).having(
        func.count(StorageUsage.id) > 1
    ).all()

    report = {
        "missing_project": _group_issue(missing_project),
        "missing_cluster": _group_issue(missing_cluster),
        "missing_target": _group_issue(missing_target),
        "cross_cluster_qtree": _group_issue(cross_cluster_qtree),
        "null_qtree": _group_issue(null_qtree),
        "repeated_project_cluster": _key_issue(repeated_project_cluster),
        "shared_resource": _key_issue(shared_resource),
        "duplicate_storage_usage": _key_issue(duplicate_storage_usage),
    }
    report["has_blockers"] = any(report[name]["count"] for name in BLOCKING_ISSUES)
    return report


def _eligible_groups(db):
    return db.query(Group).outerjoin(Qtree, Group.qtree_id == Qtree.id).filter(
        Group.project_id.isnot(None),
        Group.storage_cluster_id.isnot(None),
        (Group.qtree_id.isnot(None) | Group.volume_id.isnot(None)),
        (
            Group.qtree_id.is_(None)
            | Qtree.storage_cluster_id.is_(None)
            | (Qtree.storage_cluster_id == Group.storage_cluster_id)
        ),
    ).order_by(Group.id).all()


def _available_environment_name(base_name, cluster_id, used_names):
    if base_name not in used_names:
        return base_name
    suffix = f"-{cluster_id}"
    candidate = f"{base_name[:128 - len(suffix)]}{suffix}"
    counter = 2
    while candidate in used_names:
        suffix = f"-{cluster_id}-{counter}"
        candidate = f"{base_name[:128 - len(suffix)]}{suffix}"
        counter += 1
    return candidate


def backfill_project_storage_environments(db, apply=False):
    audit = audit_legacy_storage_bindings(db)
    groups = _eligible_groups(db)
    planned_groups = [group for group in groups if group.project_environment_id is None]
    planned_pairs = {
        (group.project_id, group.storage_cluster_id) for group in planned_groups
    }
    existing_pairs = {
        (project_id, cluster_id)
        for project_id, cluster_id in db.query(
            ProjectStorageEnvironment.project_id,
            ProjectStorageEnvironment.storage_cluster_id,
        ).all()
    }
    planned_environments = len(planned_pairs - existing_pairs)

    if not apply:
        return {
            "applied": False,
            "planned_environments": planned_environments,
            "planned_groups": len(planned_groups),
            "audit": audit,
        }
    if audit["has_blockers"]:
        db.rollback()
        raise ValueError("blocking legacy storage bindings; resolve the audit report first")

    db.rollback()
    try:
        with db.begin():
            environments = {
                (item.project_id, item.storage_cluster_id): item
                for item in db.query(ProjectStorageEnvironment).all()
            }
            clusters = {
                item.id: item
                for item in db.query(StorageCluster).filter(
                    StorageCluster.id.in_({group.storage_cluster_id for group in groups})
                )
            }
            used_names = {}
            for environment in environments.values():
                used_names.setdefault(environment.project_id, set()).add(environment.name)

            created_environments = 0
            updated_groups = 0
            for group in groups:
                pair = (group.project_id, group.storage_cluster_id)
                environment = environments.get(pair)
                if environment is None:
                    cluster = clusters[group.storage_cluster_id]
                    project_names = used_names.setdefault(group.project_id, set())
                    name = _available_environment_name(
                        cluster.name, group.storage_cluster_id, project_names
                    )
                    environment = ProjectStorageEnvironment(
                        project_id=group.project_id,
                        storage_cluster_id=group.storage_cluster_id,
                        name=name,
                        is_active=True,
                        limit=None,
                        soft_limit=None,
                        used=None,
                        use_ratio=None,
                        soft_use_ratio=None,
                        collection_status="pending",
                        last_collected_at=None,
                    )
                    db.add(environment)
                    db.flush()
                    environments[pair] = environment
                    project_names.add(name)
                    created_environments += 1

                changed = group.project_environment_id != environment.id
                group.project_environment_id = environment.id
                if group.qtree_id is not None and group.qtree.name == "null":
                    changed = changed or group.volume_id != group.qtree.volume_id
                    group.volume_id = group.qtree.volume_id
                    group.qtree_id = None
                    changed = True
                if changed:
                    updated_groups += 1
            db.flush()
    except Exception:
        db.rollback()
        raise

    return {
        "applied": True,
        "created_environments": created_environments,
        "updated_groups": updated_groups,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Audit and backfill project storage environments"
    )
    parser.add_argument("--apply", action="store_true", help="apply the audited backfill")
    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        result = backfill_project_storage_environments(db, apply=args.apply)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        db.rollback()
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
