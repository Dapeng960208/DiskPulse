# -*- coding: utf-8 -*-
import time

from celery.utils.log import get_task_logger

from celery_tasks.tasks.redis_lock import redis_lock
from celery_worker import diskpulse_app
from database import SessionLocal
from services import usersService


logger = get_task_logger(__name__)


@diskpulse_app.task(soft_time_limit=28500, time_limit=28800, expires=28800)
def ldap_users_sync_schedule_task():
    with redis_lock(
        "ldap_users_sync_schedule_task_lock", expires=28800
    ) as have_lock:
        if not have_lock:
            logger.info("LDAP user synchronization task is already running")
            return {"status": "skipped"}

        started_at = time.monotonic()
        logger.info("LDAP user synchronization task started")
        db = None
        try:
            db = SessionLocal()
            result = usersService.sync_ldap_users(db)
            serialized = result.model_dump()
            logger.info(
                "LDAP user synchronization task completed: "
                "ldap_total=%s created=%s updated=%s reactivated=%s "
                "marked_inactive=%s duration_seconds=%.3f",
                serialized["ldap_total"],
                serialized["created"],
                serialized["updated"],
                serialized["reactivated"],
                serialized["marked_inactive"],
                time.monotonic() - started_at,
            )
            return serialized
        except Exception:
            logger.exception(
                "LDAP user synchronization task failed: duration_seconds=%.3f",
                time.monotonic() - started_at,
            )
            raise
        finally:
            if db is not None:
                db.close()
