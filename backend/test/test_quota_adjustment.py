# -*- coding: utf-8 -*-
import json
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock

import pytest
import requests
from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from urllib3.exceptions import InsecureRequestWarning

import models
from appConfig import base_config
from schemas.quotaSchema import QuotaAdjustmentRequest
from services import quotaService
from services.audit_service import AuditContext
from utils.isilonClient import IsilonClient
from utils.netAppClient import NetAppClient
from utils.security import issue_token


GiB = 1024 ** 3
API_PREFIX = "/storage-pulse/api"


class FakeQuotaClient:
    def __init__(self):
        self.calls = []
        self.closed = False

    def update_quota(self, **kwargs):
        self.calls.append(("quota", kwargs))
        return {
            "hard_limit": kwargs["hard_limit"],
            "soft_limit": kwargs["soft_limit"],
            "soft_grace": kwargs.get("soft_grace"),
        }

    def update_volume_capacity(self, **kwargs):
        self.calls.append(("volume", kwargs))
        return {"hard_limit": kwargs["hard_limit"], "soft_limit": None}

    def close(self):
        self.closed = True


class FailingQuotaClient(FakeQuotaClient):
    def __init__(self, error):
        super().__init__()
        self.error = error

    def update_quota(self, **kwargs):
        raise self.error


class TimeoutThenReadbackQuotaClient(FakeQuotaClient):
    def __init__(self, result):
        super().__init__()
        self.result = result

    def update_quota(self, **kwargs):
        self.calls.append(("quota", kwargs))
        raise requests.Timeout("device response was interrupted")

    def read_quota(self, **_kwargs):
        return self.result


def seed_quota_target(db, *, storage_type="netapp", volume_target=False):
    base_config.set("super_admin_usernames", ["alice"])
    db.add_all(
        [
            models.User(id=1, username="alice", rd_username="alice"),
            models.Project(id=1, name="project-1", in_charge_user_id=1),
            models.StorageCluster(
                id=1,
                name="cluster-1",
                storage_type=storage_type,
                storage_host="storage.internal",
                storage_port=443,
                storage_user="collector",
                storage_password="secret",
            ),
            models.GroupTag(id=1, name="production"),
            models.Volume(
                id=1,
                storage_cluster_id=1,
                name="volume-1" if storage_type == "netapp" else "/ifs/project-1",
                limit=100,
                used=20,
                use_ratio=20,
            ),
        ]
    )
    db.flush()
    if not volume_target:
        db.add(
            models.Qtree(
                id=1,
                storage_cluster_id=1,
                volume_id=1,
                name="qtree-1",
                limit=100,
                used=20,
                use_ratio=20,
            )
        )
        db.flush()
    db.add(
        models.Group(
            id=1,
            project_id=1,
            storage_cluster_id=1,
            group_tag_id=1,
            volume_id=1 if volume_target else None,
            qtree_id=None if volume_target else 1,
            name="group-1",
            in_charge_user_id=1,
            linux_path="/data/group-1",
            limit=100,
            used=20,
            use_ratio=20,
        )
    )
    db.flush()
    db.add(
        models.StorageUsage(
            id=1,
            storage_cluster_id=1,
            user_id=1,
            group_id=1,
            linux_path="/data/group-1/alice",
            limit=50,
            used=10,
            use_ratio=20,
            updated_at=datetime.now(),
        )
    )
    db.commit()


def quota_owner(db):
    return db.get(models.User, 1)


@pytest.fixture(autouse=True)
def disable_external_quota_notification_enqueue(monkeypatch):
    """Keep quota service tests deterministic without contacting a Celery broker."""
    monkeypatch.setattr(
        quotaService,
        "_enqueue_adjustment_feishu",
        lambda *_args, **_kwargs: None,
    )


def test_quota_request_validates_limits_and_grace_pair():
    request = QuotaAdjustmentRequest(
        hard_limit=2,
        soft_limit=1.5,
        unit="TiB",
        soft_grace=2,
        soft_grace_unit="hours",
    )
    assert request.hard_limit_bytes == 2 * 1024 ** 4
    assert request.soft_limit_bytes == 1.5 * 1024 ** 4
    assert request.soft_grace_seconds == 7200

    with pytest.raises(ValidationError):
        QuotaAdjustmentRequest(hard_limit=100, soft_limit=100, unit="GiB")
    with pytest.raises(ValidationError):
        QuotaAdjustmentRequest(
            hard_limit=100,
            unit="GiB",
            soft_grace=1,
            soft_grace_unit="hours",
        )
    with pytest.raises(ValidationError):
        QuotaAdjustmentRequest(hard_limit=float("inf"), unit="GiB")


def test_quota_request_accepts_force_fields_only_with_a_bounded_reason():
    request = QuotaAdjustmentRequest(
        hard_limit=10,
        unit="GiB",
        force_below_usage=True,
        change_reason="释放未使用的项目容量",
    )
    assert request.force_below_usage is True
    assert request.change_reason == "释放未使用的项目容量"

    with pytest.raises(ValidationError):
        QuotaAdjustmentRequest(
            hard_limit=10,
            unit="GiB",
            force_below_usage=True,
            change_reason="x" * 257,
        )


def test_quota_adjustment_requires_force_before_lowering_below_used_capacity(db_session, monkeypatch):
    seed_quota_target(db_session)
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: FakeQuotaClient())

    with pytest.raises(HTTPException) as error:
        quotaService.adjust_group_quota(
            db_session,
            group_id=1,
            request=QuotaAdjustmentRequest(hard_limit=10, unit="GiB"),
            current_user=quota_owner(db_session),
        )

    assert error.value.status_code == 422
    assert error.value.detail["code"] == "quota_below_usage_requires_force"


def test_only_super_admin_can_force_a_quota_below_used_capacity(db_session, monkeypatch):
    seed_quota_target(db_session)
    db_session.add(models.User(id=2, username="admin", rd_username="admin"))
    db_session.commit()
    base_config.set("super_admin_usernames", ["admin"])
    client = FakeQuotaClient()
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    request = QuotaAdjustmentRequest(
        hard_limit=10,
        unit="GiB",
        force_below_usage=True,
        change_reason="释放未使用的项目容量",
    )

    with pytest.raises(HTTPException) as error:
        quotaService.adjust_group_quota(
            db_session,
            group_id=1,
            request=request,
            current_user=quota_owner(db_session),
        )
    assert error.value.status_code == 403
    assert error.value.detail == "quota adjustment permission required"

    result = quotaService.adjust_group_quota(
        db_session,
        group_id=1,
        request=request,
        current_user=db_session.get(models.User, 2),
    )
    assert result.hard_limit == 10
    assert client.calls


def test_quota_adjustment_rejects_a_busy_target_before_device_write(db_session, monkeypatch):
    seed_quota_target(db_session)
    build_client = MagicMock(return_value=FakeQuotaClient())
    monkeypatch.setattr(quotaService, "_build_client", build_client)

    @contextmanager
    def blocked_lock(**_kwargs):
        yield False

    monkeypatch.setattr(quotaService, "_quota_target_lock", blocked_lock, raising=False)

    with pytest.raises(HTTPException) as error:
        quotaService.adjust_group_quota(
            db_session,
            group_id=1,
            request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
            current_user=quota_owner(db_session),
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "quota_adjustment_in_progress"
    build_client.assert_not_called()


def test_timeout_verifies_by_reading_device_without_repeating_the_write(db_session, monkeypatch):
    seed_quota_target(db_session)
    client = TimeoutThenReadbackQuotaClient(
        {"hard_limit": 120 * GiB, "soft_limit": 108 * GiB, "soft_grace": None}
    )
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)

    result = quotaService.adjust_group_quota(
        db_session,
        group_id=1,
        request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
        current_user=quota_owner(db_session),
    )

    assert result.hard_limit == 120
    assert result.verification_source == "post_timeout_readback"
    assert [call[0] for call in client.calls] == ["quota"]


def test_manual_reconciliation_syncs_local_quota_without_writing_device(db_session, monkeypatch):
    seed_quota_target(db_session)
    client = FakeQuotaClient()
    client.read_quota = MagicMock(
        return_value={"hard_limit": 140 * GiB, "soft_limit": None, "soft_grace": None}
    )
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)

    result = quotaService.reconcile_group_quota(
        db_session,
        group_id=1,
        current_user=quota_owner(db_session),
    )

    assert result.hard_limit == 140
    assert result.verification_source == "manual_reconciliation"
    assert client.calls == []
    assert db_session.get(models.Group, 1).limit == 140


def test_group_adjustment_rejects_shared_target_before_device_call(db_session, monkeypatch):
    seed_quota_target(db_session)
    db_session.add(
        models.Group(
            id=2,
            project_id=1,
            storage_cluster_id=1,
            group_tag_id=1,
            qtree_id=1,
            name="group-2",
        )
    )
    db_session.commit()
    build_client = MagicMock()
    monkeypatch.setattr(quotaService, "_build_client", build_client)

    with pytest.raises(HTTPException) as error:
        quotaService.adjust_group_quota(
            db_session,
            group_id=1,
            request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
            current_user=quota_owner(db_session),
        )

    assert error.value.status_code == 409
    build_client.assert_not_called()


def test_quota_adjustment_requires_authenticated_user(db_session, monkeypatch):
    """Direct service callers cannot bypass the quota authorization boundary."""
    seed_quota_target(db_session)
    client = FakeQuotaClient()
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)

    with pytest.raises(HTTPException) as error:
        quotaService.adjust_group_quota(
            db_session,
            group_id=1,
            request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
            current_user=None,
        )

    assert error.value.status_code == 401
    assert client.calls == []


def test_group_quota_is_super_admin_only_and_project_owner_adjusts_project_users(
    db_session,
    monkeypatch,
):
    seed_quota_target(db_session)
    project_owner = models.User(id=2, username="project-owner", rd_username="project-owner")
    group_owner = models.User(id=3, username="group-owner", rd_username="group-owner")
    db_session.add_all([project_owner, group_owner])
    project = db_session.get(models.Project, 1)
    group = db_session.get(models.Group, 1)
    project.in_charge_user_id = project_owner.id
    group.in_charge_user_id = group_owner.id
    base_config.set("super_admin_usernames", ["super-admin"])
    db_session.commit()

    client = FakeQuotaClient()
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    request = QuotaAdjustmentRequest(hard_limit=120, unit="GiB")

    with pytest.raises(HTTPException) as group_error:
        quotaService.adjust_group_quota(
            db_session,
            group_id=1,
            request=request,
            current_user=group_owner,
        )
    assert group_error.value.status_code == 403

    with pytest.raises(HTTPException) as non_owner_error:
        quotaService.adjust_storage_usage_quota(
            db_session,
            storage_usage_id=1,
            request=request,
            current_user=group_owner,
        )
    assert non_owner_error.value.status_code == 403

    result = quotaService.adjust_storage_usage_quota(
        db_session,
        storage_usage_id=1,
        request=request,
        current_user=project_owner,
    )
    assert result.hard_limit == 120
    assert len(client.calls) == 1


def test_netapp_qtree_group_adjustment_updates_device_and_local_state(db_session, monkeypatch):
    seed_quota_target(db_session)
    client = FakeQuotaClient()
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    monkeypatch.setattr(quotaService, "_send_adjustment_email", lambda *args, **kwargs: None)

    result = quotaService.adjust_group_quota(
        db_session,
        group_id=1,
        request=QuotaAdjustmentRequest(
            hard_limit=120,
            soft_limit=100,
            unit="GiB",
        ),
        current_user=quota_owner(db_session),
    )

    assert client.calls == [
        (
            "quota",
            {
                "quota_type": "tree",
                "volume_name": "volume-1",
                "qtree_name": "qtree-1",
                "path": "/data/group-1",
                "username": None,
                "hard_limit": 120 * GiB,
                "soft_limit": 100 * GiB,
                "soft_grace": None,
            },
        )
    ]
    assert result.hard_limit == 120
    assert result.soft_limit == 100
    assert db_session.get(models.Group, 1).limit == 120
    assert db_session.get(models.Qtree, 1).soft_limit == 100
    alert = db_session.query(models.StorageAlerts).filter_by(alert_type="quota_adjustment").one()
    assert alert.related_info["old_hard_limit"] == 100
    assert client.closed is True


@pytest.mark.parametrize(
    ("resource_type", "adjust"),
    [
        (
            "group",
            lambda db, context: quotaService.adjust_group_quota(
                db,
                group_id=1,
                request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
                current_user=quota_owner(db),
                audit_context=context,
            ),
        ),
        (
            "storage_usage",
            lambda db, context: quotaService.adjust_storage_usage_quota(
                db,
                storage_usage_id=1,
                request=QuotaAdjustmentRequest(hard_limit=80, unit="GiB"),
                current_user=quota_owner(db),
                audit_context=context,
            ),
        ),
    ],
)
def test_quota_adjustment_writes_correlated_attempt_and_result_events(
    db_session,
    monkeypatch,
    resource_type,
    adjust,
):
    seed_quota_target(db_session)
    client = FakeQuotaClient()
    context = AuditContext(
        request_id="3efc3f58-4342-4c4d-97ee-c498087cb655",
        trace_id="70e1b4cd-e97a-4725-a750-fbd6f0e91f5f",
        operation_id="10a021fb-c3cd-4299-8947-93c9f52fd540",
    )
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    monkeypatch.setattr(quotaService, "_send_adjustment_email", lambda *args, **kwargs: None)
    monkeypatch.setattr(quotaService, "_enqueue_adjustment_feishu", lambda _event_id, **_kwargs: None)

    adjust(db_session, context)

    events = db_session.query(models.AuditEvent).order_by(models.AuditEvent.occurred_at, models.AuditEvent.id).all()
    assert [(event.phase, event.outcome) for event in events] == [("attempt", "success"), ("result", "success")]
    assert all(event.action == "quota.adjust" and event.resource_type == resource_type for event in events)
    assert {event.operation_id for event in events} == {context.operation_id}
    assert all(event.project_id == 1 for event in events)
    assert "/data/group-1" not in json.dumps(
        [(event.before_summary, event.after_summary, event.event_metadata) for event in events],
        ensure_ascii=False,
    )


def test_quota_adjustment_propagates_correlation_to_notification_task(db_session, monkeypatch):
    seed_quota_target(db_session)
    group = db_session.get(models.Group, 1)
    group.in_charge_user_id = 1
    db_session.commit()
    client = FakeQuotaClient()
    enqueue = MagicMock()
    context = AuditContext(
        request_id="3efc3f58-4342-4c4d-97ee-c498087cb655",
        trace_id="70e1b4cd-e97a-4725-a750-fbd6f0e91f5f",
        operation_id="10a021fb-c3cd-4299-8947-93c9f52fd540",
        actor_user_id=1,
    )
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    monkeypatch.setattr(quotaService, "_send_adjustment_email", lambda *args, **kwargs: None)
    monkeypatch.setattr(quotaService, "_enqueue_adjustment_feishu", enqueue, raising=False)
    monkeypatch.setattr(
        quotaService.base_config,
        "get",
        lambda key, default=None: {
            "feishu_notification": {"enabled": True, "debug": False, "cc_usernames": ["auditor"]},
            "super_admin_usernames": ["alice"],
        }.get(key, default),
    )

    quotaService.adjust_group_quota(
        db_session,
        group_id=1,
        request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
        current_user=quota_owner(db_session),
        audit_context=context,
    )

    alert = db_session.query(models.StorageAlerts).filter_by(alert_type="quota_adjustment").one()
    enqueue.assert_called_once_with(alert.id, audit_context=context)


def test_quota_adjustments_queue_feishu_for_group_owner_and_directory_user(db_session, monkeypatch):
    seed_quota_target(db_session)
    group = db_session.get(models.Group, 1)
    group.in_charge_user_id = 1
    db_session.commit()
    db_session.expire_all()
    client = FakeQuotaClient()
    enqueue = MagicMock()
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    monkeypatch.setattr(quotaService, "_send_adjustment_email", lambda *args, **kwargs: None)
    monkeypatch.setattr(quotaService, "_enqueue_adjustment_feishu", enqueue, raising=False)
    monkeypatch.setattr(
        quotaService.base_config,
        "get",
        lambda key, default=None: {
            "feishu_notification": {"enabled": True, "debug": False, "cc_usernames": ["auditor"]},
            "super_admin_usernames": ["alice"],
        }.get(key, default),
    )

    quotaService.adjust_group_quota(
        db_session,
        group_id=1,
        request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
        current_user=quota_owner(db_session),
    )
    quotaService.adjust_storage_usage_quota(
        db_session,
        storage_usage_id=1,
        request=QuotaAdjustmentRequest(hard_limit=80, unit="GiB"),
        current_user=quota_owner(db_session),
    )

    alerts = db_session.query(models.StorageAlerts).order_by(models.StorageAlerts.id).all()
    assert [alert.recipient_usernames for alert in alerts] == [
        ["alice", "auditor"],
        ["alice", "auditor"],
    ]
    assert [alert.delivery_status for alert in alerts] == ["pending", "pending"]
    assert [call.args[0] for call in enqueue.call_args_list] == [alerts[0].id, alerts[1].id]
    group_text = "".join(
        item["text"] for paragraph in alerts[0].related_info["paragraphs"] for item in paragraph
    )
    usage_text = "".join(
        item["text"] for paragraph in alerts[1].related_info["paragraphs"] for item in paragraph
    )
    assert alerts[0].related_info["title"] == "存储配额调整"
    assert "项目组：group-1" in group_text
    assert "硬限额：100.00 GiB → 120.00 GiB" in group_text
    assert "用户目录：/data/group-1/alice" in usage_text


def test_quota_adjustment_succeeds_when_feishu_enqueue_fails(db_session, monkeypatch):
    seed_quota_target(db_session)
    group = db_session.get(models.Group, 1)
    group.in_charge_user_id = 1
    db_session.commit()
    client = FakeQuotaClient()
    enqueue = MagicMock(side_effect=RuntimeError("broker unavailable"))
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    monkeypatch.setattr(quotaService, "_send_adjustment_email", lambda *args, **kwargs: None)
    monkeypatch.setattr(quotaService, "_enqueue_adjustment_feishu", enqueue, raising=False)
    monkeypatch.setattr(
        quotaService.base_config,
        "get",
        lambda key, default=None: {
            "feishu_notification": {"enabled": True, "debug": False, "cc_usernames": []},
            "super_admin_usernames": ["alice"],
        }.get(key, default),
    )

    result = quotaService.adjust_group_quota(
        db_session,
        group_id=1,
        request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
        current_user=quota_owner(db_session),
    )

    assert result.hard_limit == 120
    assert db_session.query(models.StorageAlerts).one().delivery_status == "pending"
    enqueue.assert_called_once()


def test_netapp_volume_group_accepts_only_hard_limit(db_session, monkeypatch):
    seed_quota_target(db_session, volume_target=True)
    client = FakeQuotaClient()
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    monkeypatch.setattr(quotaService, "_send_adjustment_email", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as error:
        quotaService.adjust_group_quota(
            db_session,
            group_id=1,
            request=QuotaAdjustmentRequest(
                hard_limit=120,
                soft_limit=100,
                unit="GiB",
            ),
            current_user=quota_owner(db_session),
        )
    assert error.value.status_code == 422

    result = quotaService.adjust_group_quota(
        db_session,
        group_id=1,
        request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
        current_user=quota_owner(db_session),
    )
    assert client.calls == [
        ("volume", {"volume_name": "volume-1", "hard_limit": 120 * GiB})
    ]
    assert result.soft_limit is None


def test_isilon_user_adjustment_defaults_soft_limit_and_grace_and_uses_current_username(db_session, monkeypatch):
    seed_quota_target(db_session, storage_type="isilon", volume_target=True)
    client = FakeQuotaClient()
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    monkeypatch.setattr(quotaService, "_send_adjustment_email", lambda *args, **kwargs: None)
    monkeypatch.setattr(quotaService, "_enqueue_adjustment_feishu", lambda _event_id: None)

    result = quotaService.adjust_storage_usage_quota(
        db_session,
        storage_usage_id=1,
        request=QuotaAdjustmentRequest(
            hard_limit=80,
            unit="GiB",
        ),
        current_user=quota_owner(db_session),
    )
    assert client.calls == [
        (
            "quota",
            {
                "quota_type": "user",
                "volume_name": "/ifs/project-1",
                "qtree_name": None,
                "path": "/ifs/project-1",
                "username": "alice",
                "hard_limit": 80 * GiB,
                "soft_limit": 72 * GiB,
                "soft_grace": 7 * 24 * 3600,
            },
        )
    ]
    assert result.storage_type == "isilon"
    assert result.soft_limit == 72
    assert result.soft_grace_seconds == 7 * 24 * 3600
    assert db_session.get(models.StorageUsage, 1).soft_limit == 72


def test_isilon_user_adjustment_defaults_grace_when_soft_limit_is_explicit(db_session, monkeypatch):
    """Callers may override the soft limit without specifying Isilon's grace period."""
    seed_quota_target(db_session, storage_type="isilon", volume_target=True)
    client = FakeQuotaClient()
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    monkeypatch.setattr(quotaService, "_send_adjustment_email", lambda *args, **kwargs: None)
    monkeypatch.setattr(quotaService, "_enqueue_adjustment_feishu", lambda _event_id: None)

    quotaService.adjust_storage_usage_quota(
        db_session,
        storage_usage_id=1,
        request=QuotaAdjustmentRequest(hard_limit=80, soft_limit=60, unit="GiB"),
        current_user=quota_owner(db_session),
    )

    assert client.calls[0][1]["soft_limit"] == 60 * GiB
    assert client.calls[0][1]["soft_grace"] == 7 * 24 * 3600


def test_quota_adjustment_preserves_native_device_json_error(db_session, monkeypatch):
    seed_quota_target(db_session, storage_type="isilon", volume_target=True)
    native_error = {
        "errors": [
            {
                "code": "AEC_FORBIDDEN",
                "message": "Quota Management privilege is required",
            }
        ]
    }
    response = requests.Response()
    response.status_code = 403
    response.headers["content-type"] = "application/json"
    response._content = json.dumps(native_error).encode()
    client = FailingQuotaClient(requests.HTTPError(response=response))
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)

    result = quotaService.adjust_group_quota(
        db_session,
        group_id=1,
        request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
        current_user=quota_owner(db_session),
    )

    assert isinstance(result, Response)
    assert result.status_code == 403
    assert result.body == response.content
    assert result.headers["content-type"] == "application/json"
    assert client.closed is True


def test_quota_adjustment_preserves_native_device_text_error(db_session, monkeypatch):
    seed_quota_target(db_session, storage_type="netapp", volume_target=False)
    response = requests.Response()
    response.status_code = 409
    response.headers["content-type"] = "text/plain; charset=utf-8"
    response._content = b"quota rule is locked"
    client = FailingQuotaClient(requests.HTTPError(response=response))
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)

    result = quotaService.adjust_group_quota(
        db_session,
        group_id=1,
        request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
        current_user=quota_owner(db_session),
    )

    assert isinstance(result, Response)
    assert result.status_code == 409
    assert result.body == b"quota rule is locked"
    assert result.headers["content-type"] == "text/plain; charset=utf-8"
    assert client.closed is True


def test_quota_client_suppresses_warning_only_when_tls_verification_is_disabled(monkeypatch):
    cluster = MagicMock(
        storage_host="storage.internal",
        storage_user="collector",
        storage_password="secret",
        protocol="https",
        tls_verify=False,
        storage_type="isilon",
        storage_port=8080,
        isilon_session_cache_mode="none",
        isilon_session_cache_path=None,
    )
    disable_warnings = MagicMock()
    monkeypatch.setattr(quotaService, "disable_warnings", disable_warnings, raising=False)
    monkeypatch.setattr(quotaService, "IsilonClient", MagicMock())

    quotaService._build_client(cluster)

    disable_warnings.assert_called_once_with(InsecureRequestWarning)


def _response(payload, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = payload
    response.raise_for_status.side_effect = None
    return response


def test_netapp_client_patches_existing_quota_rule_and_reads_back():
    client = object.__new__(NetAppClient)
    client.base_url = "https://netapp/api"
    client.origin = "https://netapp"
    client.logger = None
    client.session = MagicMock()
    client._get_all_records = MagicMock(
        side_effect=[
            [{"uuid": "rule-1"}],
            [{"space": {"hard_limit": 120 * GiB, "soft_limit": 100 * GiB}}],
        ]
    )
    client.session.patch.return_value = _response({})

    result = client.update_quota(
        quota_type="tree",
        volume_name="volume-1",
        qtree_name="qtree-1",
        path="/unused",
        username=None,
        hard_limit=120 * GiB,
        soft_limit=100 * GiB,
        soft_grace=None,
    )

    client.session.patch.assert_called_once_with(
        "https://netapp/api/storage/quota/rules/rule-1",
        params={"return_timeout": 120},
        json={"space": {"hard_limit": 120 * GiB, "soft_limit": 100 * GiB}},
        timeout=120,
    )
    assert result["hard_limit"] == 120 * GiB


def test_isilon_client_updates_explicit_quota_and_creates_for_linked_user():
    client = object.__new__(IsilonClient)
    client.base_url = "https://isilon/platform"
    client.api_version = "14"
    client.logger = None
    client.session = MagicMock()
    client.get_quotas = MagicMock(
        side_effect=[
            [
                {
                    "id": "linked-1",
                    "type": "user",
                    "path": "/ifs/project-1",
                    "linked": True,
                    "persona": {"name": "alice"},
                }
            ],
            [
                {
                    "id": "explicit-1",
                    "type": "user",
                    "path": "/ifs/project-1",
                    "linked": False,
                    "persona": {"name": "alice"},
                }
            ],
        ]
    )
    client.session.post.return_value = _response({})
    client.session.get.return_value = _response(
        {"quotas": [{"thresholds": {"hard": 80 * GiB, "soft": 60 * GiB, "soft_grace": 3600}}]}
    )

    result = client.update_quota(
        quota_type="user",
        volume_name="/ifs/project-1",
        qtree_name=None,
        path="/ifs/project-1",
        username="alice",
        hard_limit=80 * GiB,
        soft_limit=60 * GiB,
        soft_grace=3600,
    )

    client.session.post.assert_called_once_with(
        "https://isilon/platform/14/quota/quotas",
        json={
            "type": "user",
            "path": "/ifs/project-1",
            "persona": {"type": "user", "name": "alice"},
            "thresholds": {"hard": 80 * GiB, "soft": 60 * GiB, "soft_grace": 3600},
        },
        timeout=60,
    )
    assert result["soft_grace"] == 3600


def test_isilon_client_updates_existing_quota_with_mutable_fields_only():
    client = object.__new__(IsilonClient)
    client.base_url = "https://isilon/platform"
    client.api_version = "22"
    client.logger = None
    client.session = MagicMock()
    client.get_quotas = MagicMock(
        side_effect=[
            [
                {
                    "id": "quota-1",
                    "type": "directory",
                    "path": "/ifs/project-1",
                    "linked": False,
                }
            ],
            [
                {
                    "id": "quota-1",
                    "type": "directory",
                    "path": "/ifs/project-1",
                    "linked": False,
                }
            ],
        ]
    )
    client.session.put.return_value = _response({})
    client.session.get.return_value = _response(
        {"quotas": [{"thresholds": {"hard": 120 * GiB, "soft": 100 * GiB, "soft_grace": 3600}}]}
    )

    client.update_quota(
        quota_type="directory",
        volume_name="/ifs/project-1",
        qtree_name=None,
        path="/ifs/project-1",
        username=None,
        hard_limit=120 * GiB,
        soft_limit=100 * GiB,
        soft_grace=3600,
    )

    client.session.put.assert_called_once_with(
        "https://isilon/platform/22/quota/quotas/quota-1",
        json={"thresholds": {"hard": 120 * GiB, "soft": 100 * GiB, "soft_grace": 3600}},
        timeout=60,
    )


@pytest.fixture
def quota_api(api_client_factory, session_factory, monkeypatch):
    from routers import group, storage_usage

    base_config.set("jwt.secret_key", "test-jwt-secret-key-for-unit-tests-32")
    base_config.set("super_admin_usernames", ["admin"])
    session = session_factory()
    try:
        session.add(models.User(id=1, username="admin", rd_username="admin"))
        session.commit()
    finally:
        session.close()

    monkeypatch.setattr(
        quotaService,
        "adjust_group_quota",
        lambda _db, group_id, request, current_user=None, audit_context=None: {
            "id": group_id,
            "resource_type": "group",
            "storage_type": "netapp",
            "hard_limit": request.hard_limit_gib,
            "soft_limit": request.soft_limit_gib,
            "unit": "GiB",
            "soft_grace_seconds": None,
        },
    )
    monkeypatch.setattr(
        quotaService,
        "adjust_storage_usage_quota",
        lambda _db, storage_usage_id, request, current_user=None, audit_context=None: {
            "id": storage_usage_id,
            "resource_type": "storage_usage",
            "storage_type": "netapp",
            "hard_limit": request.hard_limit_gib,
            "soft_limit": request.soft_limit_gib,
            "unit": "GiB",
            "soft_grace_seconds": None,
        },
    )
    return api_client_factory(
        [group.router, storage_usage.router],
        headers={"Authorization": f"Bearer {issue_token(1)}"},
    )


def test_quota_routes_use_resource_paths_and_reject_extra_input(quota_api):
    group_response = quota_api.patch(
        f"{API_PREFIX}/groups/7/quota",
        json={"hard_limit": 1, "soft_limit": 0.5, "unit": "TiB"},
    )
    assert group_response.status_code == 200
    assert group_response.json()["hard_limit"] == 1024

    usage_response = quota_api.patch(
        f"{API_PREFIX}/storage-usages/9/quota",
        json={"hard_limit": 100, "unit": "GiB", "unexpected": True},
    )
    assert usage_response.status_code == 422


def test_quota_route_returns_native_device_json_without_502_wrapper(quota_api, monkeypatch):
    native_error = {
        "errors": [
            {
                "code": "AEC_FORBIDDEN",
                "message": "Quota Management privilege is required",
            }
        ]
    }
    monkeypatch.setattr(
        quotaService,
        "adjust_group_quota",
        lambda *_args, **_kwargs: JSONResponse(status_code=403, content=native_error),
    )

    response = quota_api.patch(
        f"{API_PREFIX}/groups/7/quota",
        json={"hard_limit": 120, "unit": "GiB"},
    )

    assert response.status_code == 403
    assert response.json() == native_error
