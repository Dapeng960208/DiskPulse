# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from celery_tasks.tasks import storage_alerts
from models import AuditEvent, StorageAlerts


@pytest.mark.parametrize("send_fails", [False, True], ids=["success", "failure"])
def test_notification_task_commits_attempt_before_external_delivery_and_keeps_correlation(
    db_session, session_factory, monkeypatch, send_fails
):
    request_id = str(uuid4())
    trace_id = str(uuid4())
    operation_id = str(uuid4())
    db_session.add(
        StorageAlerts(
            source="diskpulse",
            severity="important",
            alert_level="important",
            alert_type="alert",
            description="storage alert",
            threshold=80,
            avg_use_ratio=88,
            related_id=1,
            related_type="StorageUsage",
            related_info={"title": "存储容量告警", "paragraphs": []},
            recipient_usernames=["alice"],
            delivery_status="pending",
            next_attempt_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    event_id = db_session.query(StorageAlerts.id).scalar()
    monkeypatch.setattr(storage_alerts, "SessionLocal", session_factory)
    monkeypatch.setattr(
        storage_alerts.base_config,
        "get",
        lambda key, default=None: {
            "feishu_notification": {"enabled": True},
        }.get(key, default),
    )

    def send(*_args, **_kwargs):
        with session_factory() as db:
            attempt = db.query(AuditEvent).filter_by(
                operation_id=operation_id,
                phase="attempt",
            ).one()
            event = db.get(StorageAlerts, event_id)
            assert (attempt.request_id, attempt.trace_id, attempt.actor_user_id) == (
                request_id,
                trace_id,
                7,
            )
            assert event.delivery_attempts == 1
        if send_fails:
            raise RuntimeError("delivery transport failed")

    with patch.object(storage_alerts, "FeishuNotificationService") as client:
        client.return_value.send.side_effect = send
        storage_alerts.deliver_storage_alert_task(
            event_id,
            audit_context_payload={
                "request_id": request_id,
                "trace_id": trace_id,
                "operation_id": operation_id,
                "actor_type": "user",
                "actor_user_id": 7,
            },
        )

    with session_factory() as db:
        events = (
            db.query(AuditEvent)
            .filter_by(operation_id=operation_id)
            .order_by(AuditEvent.occurred_at, AuditEvent.id)
            .all()
        )
        event = db.get(StorageAlerts, event_id)
    assert [(item.phase, item.outcome) for item in events] == [
        ("attempt", "success"),
        ("result", "failure" if send_fails else "success"),
    ]
    assert {(item.request_id, item.trace_id, item.actor_user_id) for item in events} == {
        (request_id, trace_id, 7)
    }
    assert event.delivery_status == ("retrying" if send_fails else "sent")
