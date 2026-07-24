# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

import models


def test_every_legacy_business_instant_uses_the_utc_datetime_type():
    instant_columns = (
        (models.User, "updated_at"),
        (models.Project, "updated_at"),
        (models.ProjectMembership, "created_at"),
        (models.ProjectMembership, "updated_at"),
        (models.AuditEvent, "occurred_at"),
        (models.StorageCluster, "created_at"),
        (models.StorageCluster, "updated_at"),
        (models.StorageUsage, "access_time"),
        (models.StorageAlertEvent, "next_attempt_at"),
        (models.StorageBackUpRecord, "start_time"),
        (models.AiConversation, "created_at"),
        (models.AiAuditLog, "finished_at"),
    )

    for model, column_name in instant_columns:
        assert isinstance(model.__table__.c[column_name].type, models.UTCDateTime)


def test_postgresql_model_round_trip_normalizes_an_aware_instant_to_utc(session_factory):
    session = session_factory()
    value = datetime(2026, 7, 23, 10, 30, tzinfo=timezone(timedelta(hours=8)))
    user = models.User(rd_username="utc-contract", updated_at=value)
    session.add(user)
    session.commit()
    session.expire_all()

    restored = session.get(models.User, user.id)
    session.close()

    assert restored.updated_at == datetime(2026, 7, 23, 2, 30, tzinfo=timezone.utc)
