# -*- coding: utf-8 -*-
"""Bounded background assessment for derived Incidents."""
from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from celery_worker import diskpulse_app
from celery_tasks.tasks.redis_lock import redis_lock
from crud import forecastIncidentCrud, incidentAiAgentCrud
from database import SessionLocal
from services import incidentAiAgentService


logger = get_task_logger(__name__)
REVIEW_INTERVAL = timedelta(minutes=30)


def _scheduled_key(incident_id: int, now: datetime) -> str:
    return f"scheduled:{incident_id}:{int(now.timestamp() // int(REVIEW_INTERVAL.total_seconds()))}"


@diskpulse_app.task(soft_time_limit=90, time_limit=120, expires=180)
def review_incident_ai_task(incident_id: int, trigger: str = "lifecycle") -> int:
    with redis_lock(f"incident_ai_review:{incident_id}", expires=180) as have_lock:
        if not have_lock:
            return 0
        with SessionLocal() as db:
            incident = forecastIncidentCrud.get_incident(db, incident_id)
            if incident is None:
                return 0
            key = (
                f"lifecycle:{incident.id}:{incident.status}:{incident.last_evidence_at.isoformat()}"
                if trigger == "lifecycle"
                else _scheduled_key(incident.id, datetime.now(timezone.utc))
            )
            try:
                return int(incidentAiAgentService.review_incident(
                    db,
                    incident_id=incident.id,
                    trigger=trigger,
                    idempotency_key=key,
                ) is not None)
            except Exception:
                db.rollback()
                logger.exception("Incident AI review failed: incident=%s", incident_id)
                return 0


@diskpulse_app.task(soft_time_limit=300, time_limit=360, expires=480)
def review_due_incidents_ai_task() -> int:
    now = datetime.now(timezone.utc)
    with redis_lock("incident_ai_due_review_lock", expires=480) as have_lock:
        if not have_lock:
            return 0
        with SessionLocal() as db:
            settings = incidentAiAgentService.get_settings(db)
            if not settings.enabled:
                return 0
            due = incidentAiAgentCrud.list_due_incidents(db, before=now - REVIEW_INTERVAL)
            count = 0
            for incident in due:
                try:
                    result = incidentAiAgentService.review_incident(
                        db,
                        incident_id=incident.id,
                        trigger="scheduled",
                        idempotency_key=_scheduled_key(incident.id, now),
                    )
                    count += int(result is not None)
                except Exception:
                    db.rollback()
                    logger.exception("Scheduled Incident AI review failed: incident=%s", incident.id)
            return count
