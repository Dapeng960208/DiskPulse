# -*- coding: utf-8 -*-
import logging


logger = logging.getLogger("uvicorn.error")


def schedule_storage_collection(storage_cluster_id: int) -> None:
    try:
        from celery_tasks.tasks.storages import storages_schedule_fetching_task

        logger.info("Scheduling storage collection for cluster %s", storage_cluster_id)
        storages_schedule_fetching_task.delay(storage_cluster_id)
        logger.info("Storage collection scheduled for cluster %s", storage_cluster_id)
    except Exception:
        logger.exception("Failed to schedule storage collection for cluster %s", storage_cluster_id)
