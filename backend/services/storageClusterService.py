# -*- coding: utf-8 -*-
import logging

from services.audit_service import AuditContext


logger = logging.getLogger(__name__)


def schedule_storage_collection(
    storage_cluster_id: int,
    *,
    audit_context: AuditContext | None = None,
) -> None:
    try:
        from celery_tasks.tasks.storages import storages_schedule_fetching_task

        logger.info("Scheduling storage collection for cluster %s", storage_cluster_id)
        if audit_context is None:
            storages_schedule_fetching_task.delay(storage_cluster_id)
        else:
            storages_schedule_fetching_task.delay(
                storage_cluster_id,
                audit_context_payload={
                    "request_id": audit_context.request_id,
                    "trace_id": audit_context.trace_id,
                    "operation_id": audit_context.operation_id,
                    "actor_type": audit_context.actor_type,
                    "actor_user_id": audit_context.actor_user_id,
                },
            )
        logger.info("Storage collection scheduled for cluster %s", storage_cluster_id)
    except Exception:
        logger.exception("Failed to schedule storage collection for cluster %s", storage_cluster_id)
