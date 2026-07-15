# -*- coding: utf-8 -*-
from collections import defaultdict
from types import MappingProxyType

from sqlalchemy import select, update

from dependencies import DBSession
from database import SessionLocal
from celery_worker import diskpulse_app
from celery_tasks.manager.storageMonitor import SynchronousPathState
from celery_tasks.manager.remoteFileManager import RemoteFileManager
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from celery_tasks.manager.storageAlert import StorageAlert
from celery_tasks.tasks.redis_lock import redis_lock
from celery.exceptions import SoftTimeLimitExceeded
from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from models import Group, Project, Qtree, StorageCluster, Volume
logger = get_task_logger(__name__)


def load_collection_snapshot(db, storage_cluster_id=None):
    """Load one scalar, session-independent configuration snapshot."""
    filters = [StorageCluster.is_active.is_(True)]
    if storage_cluster_id is not None:
        filters.append(StorageCluster.id == storage_cluster_id)
    statement = (
        select(
            StorageCluster.id.label("storage_cluster_id"),
            StorageCluster.name.label("storage_cluster_name"),
            StorageCluster.storage_type.label("storage_type"),
            StorageCluster.storage_host.label("storage_host"),
            StorageCluster.storage_port.label("storage_port"),
            StorageCluster.protocol.label("protocol"),
            StorageCluster.tls_verify.label("tls_verify"),
            StorageCluster.storage_user.label("storage_user"),
            StorageCluster.storage_password.label("storage_password"),
            StorageCluster.isilon_session_cache_mode.label(
                "isilon_session_cache_mode"
            ),
            StorageCluster.isilon_session_cache_path.label(
                "isilon_session_cache_path"
            ),
            StorageCluster.is_active.label("cluster_active"),
            Group.project_id.label("project_id"),
            Group.group_tag_id.label("group_tag_id"),
            Group.id.label("group_id"),
            Group.enable_monitoring.label("group_enable_monitoring"),
            Group.volume_id.label("volume_id"),
            Group.qtree_id.label("qtree_id"),
            Volume.name.label("volume_name"),
            Qtree.name.label("qtree_name"),
        )
        .outerjoin(
            Group,
            (Group.storage_cluster_id == StorageCluster.id)
            & Group.enable_monitoring.is_(True),
        )
        .outerjoin(Volume, Volume.id == Group.volume_id)
        .outerjoin(Qtree, Qtree.id == Group.qtree_id)
        .where(*filters)
        .order_by(StorageCluster.id, Group.id)
    )
    return tuple(
        MappingProxyType(dict(row)) for row in db.execute(statement).mappings().all()
    )


def apply_group_snapshot_update(db, snapshot, values):
    result = db.execute(
        update(Group)
        .where(
            Group.id == snapshot["group_id"],
            Group.project_id == snapshot["project_id"],
            Group.storage_cluster_id == snapshot["storage_cluster_id"],
            Group.group_tag_id == snapshot["group_tag_id"],
            Group.enable_monitoring.is_(True),
        )
        .values(**values)
    )
    return result.rowcount > 0


def finalize_project_totals(db, cluster_results, collected_at):
    groups = db.execute(
        select(
            Group.project_id,
            Group.storage_cluster_id,
            Group.volume_id,
            Group.qtree_id,
            Group.associate_multiple_groups,
            Group.limit,
            Group.soft_limit,
            Group.used,
        ).where(Group.enable_monitoring.is_(True))
    ).all()
    by_project = defaultdict(list)
    for group in groups:
        by_project[group.project_id].append(group)

    refreshed = set()
    for project_id, project_groups in by_project.items():
        cluster_ids = {item.storage_cluster_id for item in project_groups}
        if not all(cluster_results.get(cluster_id) is True for cluster_id in cluster_ids):
            continue
        unique_groups = []
        seen_targets = set()
        for item in project_groups:
            if not item.associate_multiple_groups:
                target = (
                    item.storage_cluster_id,
                    'qtree' if item.qtree_id is not None else 'volume',
                    item.qtree_id if item.qtree_id is not None else item.volume_id,
                )
                if target in seen_targets:
                    continue
                seen_targets.add(target)
            unique_groups.append(item)
        limit = sum(item.limit or 0 for item in unique_groups)
        used = sum(item.used or 0 for item in unique_groups)
        soft_values = [
            item.soft_limit for item in unique_groups if item.soft_limit is not None
        ]
        soft_limit = sum(soft_values) if soft_values else None
        db.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(
                limit=limit,
                soft_limit=soft_limit,
                used=used,
                use_ratio=round(used * 100 / limit, 2) if limit else None,
                soft_use_ratio=(
                    round(used * 100 / soft_limit, 2) if soft_limit else None
                ),
                updated_at=collected_at,
            )
        )
        refreshed.add(project_id)
    return refreshed


def _cluster_snapshots(snapshot):
    grouped = defaultdict(list)
    for row in snapshot:
        grouped[row["storage_cluster_id"]].append(row)
    for rows in grouped.values():
        cluster = dict(rows[0])
        cluster["rows"] = tuple(rows)
        yield MappingProxyType(cluster)


def run_collection_round(
    snapshot,
    *,
    session_factory,
    monitor_factory=StoragePulseMonitor,
    questdb_writer=None,
    logger=logger,
):
    cluster_results = {}
    succeeded_clusters = []
    failed_clusters = []
    for cluster in _cluster_snapshots(snapshot):
        cluster_id = cluster["storage_cluster_id"]
        db = None
        monitor = None
        try:
            db = session_factory()
            with db.begin():
                if monitor_factory is StoragePulseMonitor:
                    monitor = monitor_factory(
                        db,
                        logger,
                        storage_cluster_id=cluster["storage_cluster_id"],
                        snapshot=cluster,
                    )
                else:
                    monitor = monitor_factory(db, logger, cluster)
                metrics = monitor.collect_postgres()
            cluster_results[cluster_id] = True
            succeeded_clusters.append(cluster_id)
            try:
                if questdb_writer is None:
                    monitor.write_questdb(metrics)
                else:
                    questdb_writer(cluster, metrics)
            except Exception as exc:
                logger.error(
                    "QuestDB write failed for cluster %s: %s",
                    cluster["storage_cluster_id"],
                    exc,
                )
        except Exception as exc:
            cluster_results[cluster_id] = False
            failed_clusters.append(cluster_id)
            logger.error(
                "Error monitoring cluster %s: %s",
                cluster["storage_cluster_id"],
                exc,
            )
        finally:
            if monitor is not None:
                close = getattr(monitor, "close", None) or getattr(monitor, "cleanup", None)
                if close is not None:
                    try:
                        close()
                    except Exception as exc:
                        logger.error(
                            "Failed to close monitor for cluster %s: %s",
                            cluster["storage_cluster_id"],
                            exc,
                        )
            if db is not None:
                try:
                    db.close()
                except Exception as exc:
                    logger.error(
                        "Failed to close session for cluster %s: %s",
                        cluster["storage_cluster_id"],
                        exc,
                    )
    if failed_clusters and not succeeded_clusters:
        raise RuntimeError(
            f"all storage clusters failed: {', '.join(map(str, failed_clusters))}"
        )
    return {
        "succeeded_clusters": tuple(succeeded_clusters),
        "failed_clusters": tuple(failed_clusters),
        "cluster_results": cluster_results,
    }


@diskpulse_app.task(soft_time_limit=120, time_limit=180, expires=60)
def storages_schedule_fetching_task(storage_cluster_id=None):
    try:
        logger.info(
            "Storage collection task started: cluster=%s",
            "all" if storage_cluster_id is None else storage_cluster_id,
        )
        with redis_lock('storages_schedule_fetching_task_lock', expires=240) as have_lock:
            if have_lock:
                with DBSession() as db:
                    snapshot = load_collection_snapshot(db, storage_cluster_id)
                collected_at = datetime.now()
                summary = run_collection_round(
                    snapshot,
                    session_factory=SessionLocal,
                )
                logger.info(
                    "Storage collection round completed: succeeded=%s failed=%s",
                    summary["succeeded_clusters"],
                    summary["failed_clusters"],
                )
                with SessionLocal() as db:
                    with db.begin():
                        finalize_project_totals(
                            db,
                            cluster_results=summary["cluster_results"],
                            collected_at=collected_at,
                        )
            else:
                logger.info("Storages schedule fetching task is already running.")
    except Exception as e:
        logger.error(f"Error in storages fetching task: {e}")
        raise


@diskpulse_app.task(soft_time_limit=3000, time_limit=3000, expires=600)
def check_user_path_status_hourly():
    try:
        with DBSession() as db:
            sync_path = SynchronousPathState(db=db, logger=logger)
            sync_path.start()
    except Exception as e:
        logger.error(f"Error in Check user path status :{e}")


@diskpulse_app.task(soft_time_limit=120, time_limit=150, expires=1800)
def user_storage_usage_alert_hourly():
    with DBSession() as db:
        now = datetime.now()
        hour = int(now.hour)
        storage_alert = StorageAlert(db, logger)
        if hour == 8:
            storage_alert.user_alarm_hourly(threshold=80)
        else:
            storage_alert.user_alarm_hourly(threshold=95, end_time=datetime.now() - timedelta(minutes=3))


@diskpulse_app.task(soft_time_limit=300, time_limit=330, expires=1800)
def group_storage_usage_alert_hourly():
    with DBSession() as db:
        now = datetime.now()
        hour = int(now.hour)
        if hour == 8:
            storage_alert = StorageAlert(db, logger)
            storage_alert.group_alarm_daily(threshold=80)
            storage_alert.system_alarm_daily(threshold=80)
        else:
            storage_alert = StorageAlert(db, logger)
            storage_alert.group_alarm_daily(threshold=95, end_time=datetime.now() - timedelta(minutes=3))


@diskpulse_app.task(soft_time_limit=300, time_limit=330)
def project_storage_usage_report_weekly():
    with DBSession() as db:
        storage_alert = StorageAlert(db, logger)
        storage_alert.project_alarm_weekly()


@diskpulse_app.task(soft_time_limit=300, time_limit=330)
def group_quit_user_storage_usage_alert_weekly():
    with DBSession() as db:
        storage_alert = StorageAlert(db, logger)
        storage_alert.group_quit_user_alarm_weekly()


@diskpulse_app.task()
def quit_user_back_up_daily():
    with DBSession() as db:
        remote_file_manager = RemoteFileManager(db=db, logger=logger)
        remote_file_manager.initiating_quit_users_bpm_process()
        # remote_file_manager.back_up_quit_users_storage_usages()
        remote_file_manager.bacK_up_delete_alarm()
        remote_file_manager.delete_back_up()
        remote_file_manager.close_ssh_connection()
