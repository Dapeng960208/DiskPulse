# -*- coding: utf-8 -*-
from datetime import timedelta

from celery.utils.log import get_task_logger

from appConfig import base_config
from celery_worker import diskpulse_app
from celery_tasks.tasks.redis_lock import redis_lock
from database import SessionLocal
from services.feishuNotificationService import FeishuNotificationService
from services.telemetryObservabilityService import purge_expired_collection_runs, utc_now


logger = get_task_logger(__name__)
RETENTION_DAYS = 90
PURGE_BATCH_SIZE = 1000


def _notify_cleanup_failure() -> None:
    config = base_config.get("feishu_notification", {}) or {}
    recipients = tuple(config.get("cc_usernames", ()) or ())
    if config.get("enabled") and recipients:
        FeishuNotificationService(config).send(
            usernames=recipients,
            title="遥测运行账本清理失败",
            paragraphs=[[{"tag": "text", "text": "遥测运行账本清理任务失败，将在下次计划周期重试。"}]],
        )


@diskpulse_app.task(bind=True, soft_time_limit=120, time_limit=180, expires=1800)
def telemetry_collection_runs_cleanup_task(self):
    with redis_lock("telemetry_collection_runs_cleanup_lock", expires=1800) as have_lock:
        if not have_lock:
            logger.info("Telemetry collection run cleanup is already running")
            return {"deleted": 0, "status": "skipped"}
        try:
            deleted = purge_expired_collection_runs(
                SessionLocal,
                cutoff=utc_now() - timedelta(days=RETENTION_DAYS),
                batch_size=PURGE_BATCH_SIZE,
            )
        except Exception:
            logger.exception("Telemetry collection run cleanup failed")
            try:
                _notify_cleanup_failure()
            except Exception:
                logger.exception("Telemetry collection run cleanup notification failed")
            raise
        return {"deleted": deleted}
