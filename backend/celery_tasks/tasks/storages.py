# -*- coding: utf-8 -*-
from collections import defaultdict
import time
from types import MappingProxyType
from uuid import uuid4

from sqlalchemy import func, select, update

from dependencies import DBSession
from database import SessionLocal
from questdb.database import QuestDBSessionLocal
from questdb.models import ProjectStorageUsage, UserStorageUsage
from celery_worker import diskpulse_app
from celery_tasks.manager.remoteFileManager import RemoteFileManager
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from celery_tasks.manager.storageAlert import StorageAlert
from celery_tasks.tasks.redis_lock import redis_lock
from celery.exceptions import SoftTimeLimitExceeded
from celery_tasks.manager.storagePulseMonitor import StoragePulseMonitor
from models import Group, Project, Qtree, StorageCluster, StorageUsage, Volume
from crud import usersCrud
from services import telemetryObservabilityService
from services.audit_service import AuditContext, append_audit_event
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


def write_project_usage_metrics(db, project_ids, *, collected_at, session_factory=QuestDBSessionLocal):
    """Write refreshed project totals to QuestDB only after PostgreSQL commits."""
    if not project_ids:
        return 0
    projects = db.execute(
        select(Project).where(Project.id.in_(project_ids)).order_by(Project.id)
    ).scalars().all()
    if not projects:
        return 0
    samples = [
        ProjectStorageUsage(
            project_id=str(project.id),
            used=project.used or 0,
            used_ratio=project.use_ratio or 0,
            soft_limit=project.soft_limit,
            soft_use_ratio=project.soft_use_ratio,
            updated_at=collected_at,
        )
        for project in projects
    ]
    quest_db = None
    try:
        quest_db = session_factory()
        quest_db.add_all(samples)
        quest_db.commit()
    except Exception:
        logger.exception("Project storage trend QuestDB write failed: count=%s", len(samples))
        if quest_db is not None:
            try:
                quest_db.rollback()
            except Exception:
                logger.exception("Project storage trend QuestDB rollback failed")
        return 0
    finally:
        if quest_db is not None:
            quest_db.close()
    return len(samples)


def _cluster_snapshots(snapshot):
    grouped = defaultdict(list)
    for row in snapshot:
        grouped[row["storage_cluster_id"]].append(row)
    for rows in grouped.values():
        cluster = dict(rows[0])
        cluster["rows"] = tuple(rows)
        yield MappingProxyType(cluster)


def _collection_audit_context(audit_context_payload=None) -> AuditContext:
    if audit_context_payload is not None:
        return AuditContext(
            request_id=audit_context_payload["request_id"],
            trace_id=audit_context_payload["trace_id"],
            operation_id=audit_context_payload["operation_id"],
            actor_type=audit_context_payload.get("actor_type", "service"),
            actor_user_id=audit_context_payload.get("actor_user_id"),
        )
    return AuditContext(
        request_id=uuid4(),
        trace_id=uuid4(),
        operation_id=uuid4(),
        actor_type="service",
    )


def _append_collection_audit_result(
    db,
    *,
    context: AuditContext,
    storage_cluster_id: int,
    outcome: str,
    reason_code: str | None = None,
    metrics=None,
):
    summary = None
    if isinstance(metrics, dict):
        summary = {
            "storage_usage_count": len(metrics.get("storage_usage_ids", ())),
            "group_count": len(metrics.get("group_ids", ())),
        }
    append_audit_event(
        db,
        context=context,
        phase="result",
        action="storage.collection.run",
        resource_type="storage_cluster",
        resource_id=storage_cluster_id,
        outcome=outcome,
        reason_code=reason_code,
        after_summary=summary,
    )


def _record_collection_failure_audit(session_factory, *, context: AuditContext, storage_cluster_id: int):
    audit_db = None
    try:
        audit_db = session_factory()
        with audit_db.begin():
            _append_collection_audit_result(
                audit_db,
                context=context,
                storage_cluster_id=storage_cluster_id,
                outcome="failure",
                reason_code="collection_failed",
            )
    finally:
        if audit_db is not None:
            audit_db.close()


def _record_collection_attempt_audit(session_factory, *, context: AuditContext, storage_cluster_id: int):
    audit_db = None
    try:
        audit_db = session_factory()
        with audit_db.begin():
            append_audit_event(
                audit_db,
                context=context,
                phase="attempt",
                action="storage.collection.run",
                resource_type="storage_cluster",
                resource_id=storage_cluster_id,
                outcome="success",
            )
    finally:
        if audit_db is not None:
            audit_db.close()


def run_collection_round(
    snapshot,
    *,
    session_factory,
    monitor_factory=StoragePulseMonitor,
    questdb_writer=None,
    logger=logger,
    collected_at=None,
    telemetry_context=None,
    audit_context: AuditContext | None = None,
):
    cluster_results = {}
    succeeded_clusters = []
    failed_clusters = []
    refreshed_storage_usage_ids = []
    refreshed_group_ids = []
    for cluster in _cluster_snapshots(snapshot):
        cluster_id = cluster["storage_cluster_id"]
        cluster_audit_context = audit_context or _collection_audit_context()
        db = None
        monitor = None
        run = None
        if telemetry_context is not None:
            run = telemetryObservabilityService.safe_start_collection_run(
                session_factory,
                logger,
                task_id=telemetry_context["task_id"],
                attempt=telemetry_context["attempt"],
                scope_type="cluster",
                scope_key=str(cluster_id),
                storage_cluster_id=cluster_id,
                component="capacity",
                trace_id=telemetry_context["trace_id"],
            )
        try:
            _record_collection_attempt_audit(
                session_factory,
                context=cluster_audit_context,
                storage_cluster_id=cluster_id,
            )
            db = session_factory()
            with db.begin():
                if monitor_factory is StoragePulseMonitor:
                    monitor = monitor_factory(
                        db,
                        logger,
                        storage_cluster_id=cluster["storage_cluster_id"],
                        snapshot=cluster,
                        collected_at=collected_at,
                    )
                else:
                    monitor = monitor_factory(db, logger, cluster)
                metrics = monitor.collect_postgres()
                if isinstance(metrics, dict):
                    refreshed_storage_usage_ids.extend(metrics.get("storage_usage_ids", ()))
                    refreshed_group_ids.extend(metrics.get("group_ids", ()))
                _append_collection_audit_result(
                    db,
                    context=cluster_audit_context,
                    storage_cluster_id=cluster_id,
                    outcome="success",
                    metrics=metrics,
                )
            cluster_results[cluster_id] = True
            succeeded_clusters.append(cluster_id)
            records_written = (
                len(metrics.get("storage_usage_ids", ()))
                + len(metrics.get("group_ids", ()))
                if isinstance(metrics, dict)
                else 0
            )
            if run is not None:
                telemetryObservabilityService.safe_complete_collection_run(
                    session_factory,
                    logger,
                    run.id,
                    outcome="success",
                    data_state=telemetryObservabilityService.successful_data_state(records_written),
                    records_written=records_written,
                )
            try:
                if questdb_writer is None:
                    monitor.write_questdb(metrics)
                else:
                    questdb_writer(cluster, metrics)
            except Exception:
                logger.error(
                    "QuestDB write failed for cluster %s: error_code=questdb",
                    cluster["storage_cluster_id"],
                )
        except Exception as exc:
            if telemetryObservabilityService.is_explicitly_unsupported(exc):
                cluster_results[cluster_id] = True
                succeeded_clusters.append(cluster_id)
                if run is not None:
                    telemetryObservabilityService.safe_complete_collection_run(
                        session_factory,
                        logger,
                        run.id,
                        outcome="success",
                        data_state="unsupported",
                        records_written=0,
                    )
                logger.info("Storage collection is unsupported for cluster %s", cluster_id)
                continue
            cluster_results[cluster_id] = False
            failed_clusters.append(cluster_id)
            error_code = telemetryObservabilityService.classify_error_code(
                exc,
                phase="vendor",
            )
            if run is not None:
                telemetryObservabilityService.safe_complete_collection_run(
                    session_factory,
                    logger,
                    run.id,
                    outcome="failed",
                    error_code=error_code,
                )
            logger.error(
                "Storage collection failed for cluster %s: error_code=%s",
                cluster["storage_cluster_id"],
                error_code,
            )
            try:
                _record_collection_failure_audit(
                    session_factory,
                    context=cluster_audit_context,
                    storage_cluster_id=cluster_id,
                )
            except Exception as audit_error:
                logger.error(
                    "Failed to record collection audit for cluster %s: %s",
                    cluster_id,
                    audit_error,
                )
        finally:
            if monitor is not None:
                close = getattr(monitor, "close", None) or getattr(monitor, "cleanup", None)
                if close is not None:
                    try:
                        close()
                    except Exception:
                        logger.error(
                            "Failed to close monitor for cluster %s",
                            cluster["storage_cluster_id"],
                        )
            if db is not None:
                try:
                    db.close()
                except Exception:
                    logger.error(
                        "Failed to close session for cluster %s",
                        cluster["storage_cluster_id"],
                    )
    if failed_clusters and not succeeded_clusters:
        raise RuntimeError(
            f"all storage clusters failed: {', '.join(map(str, failed_clusters))}"
        )
    return {
        "succeeded_clusters": tuple(succeeded_clusters),
        "failed_clusters": tuple(failed_clusters),
        "cluster_results": cluster_results,
        "refreshed_storage_usage_ids": tuple(refreshed_storage_usage_ids),
        "refreshed_group_ids": tuple(refreshed_group_ids),
    }


@diskpulse_app.task(bind=True, soft_time_limit=120, time_limit=180, expires=60)
def storages_schedule_fetching_task(self, storage_cluster_id=None, audit_context_payload=None):
    try:
        telemetry_context = telemetryObservabilityService.task_execution_context(self)
        logger.info(
            "Storage collection task started: cluster=%s trace_id=%s",
            "all" if storage_cluster_id is None else storage_cluster_id,
            telemetry_context["trace_id"],
        )
        with redis_lock('storages_schedule_fetching_task_lock', expires=240) as have_lock:
            if have_lock:
                with DBSession() as db:
                    snapshot = load_collection_snapshot(db, storage_cluster_id)
                collected_at = datetime.now()
                summary = run_collection_round(
                    snapshot,
                    session_factory=SessionLocal,
                    collected_at=collected_at,
                    telemetry_context=telemetry_context,
                    audit_context=_collection_audit_context(audit_context_payload),
                )
                logger.info(
                    "Storage collection round completed: succeeded=%s failed=%s",
                    summary["succeeded_clusters"],
                    summary["failed_clusters"],
                )
                with SessionLocal() as db:
                    with db.begin():
                        refreshed_project_ids = finalize_project_totals(
                            db,
                            cluster_results=summary["cluster_results"],
                            collected_at=collected_at,
                        )
                    project_metric_count = write_project_usage_metrics(
                        db,
                        refreshed_project_ids,
                        collected_at=collected_at,
                    )
                logger.info(
                    "Project storage trends written: count=%s",
                    project_metric_count,
                )
                try:
                    from celery_tasks.tasks import forecast_incidents

                    # Raw PostgreSQL/QuestDB collection has completed; derived work is async.
                    forecast_incidents.telemetry_quality_snapshot_task.delay()
                except Exception:
                    logger.warning("Unable to enqueue telemetry quality snapshot after capacity collection")
            else:
                telemetryObservabilityService.safe_record_scheduler_skip(
                    SessionLocal,
                    logger,
                    component="capacity",
                    **telemetry_context,
                )
                logger.info("Storages schedule fetching task is already running.")
    except Exception as error:
        logger.error(
            "Storage collection task failed: error_code=%s",
            telemetryObservabilityService.classify_error_code(error, phase="vendor"),
        )
        raise


@diskpulse_app.task(soft_time_limit=3300, time_limit=3600, expires=3600)
def user_storage_statistics_schedule_task():
    with redis_lock(
        "user_storage_statistics_schedule_task_lock", expires=3600
    ) as have_lock:
        if not have_lock:
            logger.info("User storage statistics task is already running")
            return {"status": "skipped"}

        started_at = time.monotonic()
        sampled_at = datetime.now()
        logger.info(
            "User storage statistics task started: sampled_at=%s",
            sampled_at.isoformat(),
        )
        db = None
        try:
            db = SessionLocal()
            rows = db.execute(
                select(
                    StorageUsage.user_id,
                    func.coalesce(func.sum(StorageUsage.limit), 0).label("limit"),
                    func.coalesce(func.sum(StorageUsage.soft_limit), 0).label(
                        "soft_limit"
                    ),
                    func.coalesce(func.sum(StorageUsage.used), 0).label("used"),
                    func.coalesce(func.sum(StorageUsage.file_used), 0).label(
                        "file_used"
                    ),
                )
                .where(StorageUsage.user_id.is_not(None))
                .group_by(StorageUsage.user_id)
                .order_by(StorageUsage.user_id)
            ).all()
            usersCrud.refresh_storage_used_from_directories(db)
            db.commit()
        except Exception:
            if db is not None:
                db.rollback()
            logger.exception(
                "User storage statistics PostgreSQL aggregation failed: "
                "duration_seconds=%.3f",
                time.monotonic() - started_at,
            )
            raise
        finally:
            if db is not None:
                db.close()

        if not rows:
            logger.info(
                "User storage statistics task completed: count=0 "
                "duration_seconds=%.3f",
                time.monotonic() - started_at,
            )
            return {"count": 0, "updated_at": sampled_at.isoformat()}

        samples = []
        for row in rows:
            limit = float(row.limit or 0)
            soft_limit = float(row.soft_limit or 0)
            used = float(row.used or 0)
            samples.append(
                UserStorageUsage(
                    user_id=str(row.user_id),
                    limit=limit,
                    soft_limit=soft_limit,
                    used=used,
                    use_ratio=round(used * 100 / limit, 2) if limit > 0 else 0,
                    soft_use_ratio=(
                        round(used * 100 / soft_limit, 2)
                        if soft_limit > 0
                        else 0
                    ),
                    file_used=float(row.file_used or 0),
                    updated_at=sampled_at,
                )
            )

        quest_db = None
        try:
            quest_db = QuestDBSessionLocal()
            quest_db.add_all(samples)
            quest_db.commit()
        except Exception:
            logger.exception(
                "User storage statistics QuestDB write failed: "
                "duration_seconds=%.3f",
                time.monotonic() - started_at,
            )
            if quest_db is not None:
                try:
                    quest_db.rollback()
                except Exception:
                    logger.exception("User storage statistics QuestDB rollback failed")
            raise
        finally:
            if quest_db is not None:
                quest_db.close()

        result = {"count": len(samples), "updated_at": sampled_at.isoformat()}
        logger.info(
            "User storage statistics task completed: count=%s sampled_at=%s "
            "duration_seconds=%.3f",
            result["count"],
            result["updated_at"],
            time.monotonic() - started_at,
        )
        return result


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
        # remote_file_manager.back_up_quit_users_storage_usages()
        remote_file_manager.bacK_up_delete_alarm()
        remote_file_manager.delete_back_up()
        remote_file_manager.close_ssh_connection()
