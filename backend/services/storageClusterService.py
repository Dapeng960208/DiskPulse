# -*- coding: utf-8 -*-
import logging


logger = logging.getLogger("app:storage-clusters")


def schedule_storage_collection(storage_cluster_id: int) -> None:
    try:
        from celery_tasks.tasks.storages import storages_schedule_fetching_task

        storages_schedule_fetching_task.delay(storage_cluster_id)
    except Exception:
        logger.exception("Failed to schedule storage collection for cluster %s", storage_cluster_id)
