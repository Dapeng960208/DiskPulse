# -*- coding: utf-8 -*-
from contextlib import contextmanager
import redis
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@contextmanager
def redis_lock(lock_name, expires=60):
    # Task modules are imported while celery_worker registers tasks.  Resolve
    # the worker-owned client only at use time to keep that import graph acyclic.
    from celery_worker import redis_client

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
