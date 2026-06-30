# -*- coding: utf-8 -*-
from celery_worker import redis_client
from contextlib import contextmanager
import redis
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@contextmanager
def redis_lock(lock_name, expires=60):
    lock = redis_client.lock(lock_name, timeout=expires)
    have_lock = lock.acquire(blocking=False)
    try:
        yield have_lock
    finally:
        if have_lock:
            try:
                lock.release()
            except redis.exceptions.LockNotOwnedError:
                logger.warning("Lock was not owned, cannot release")
