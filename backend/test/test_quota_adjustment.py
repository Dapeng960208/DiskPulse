# -*- coding: utf-8 -*-
import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest
import requests
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from urllib3.exceptions import InsecureRequestWarning

import models
from appConfig import base_config
from schemas.quotaSchema import QuotaAdjustmentRequest
from services import quotaService
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


def seed_quota_target(db, *, storage_type="netapp", volume_target=False):
    db.add_all(
        [
            models.User(id=1, username="alice", rd_username="alice"),
            models.Project(id=1, name="project-1"),
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
        )

    assert error.value.status_code == 409
    build_client.assert_not_called()


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
        )
    assert error.value.status_code == 422

    result = quotaService.adjust_group_quota(
        db_session,
        group_id=1,
        request=QuotaAdjustmentRequest(hard_limit=120, unit="GiB"),
    )
    assert client.calls == [
        ("volume", {"volume_name": "volume-1", "hard_limit": 120 * GiB})
    ]
    assert result.soft_limit is None


def test_isilon_user_adjustment_requires_grace_and_uses_current_username(db_session, monkeypatch):
    seed_quota_target(db_session, storage_type="isilon", volume_target=True)
    client = FakeQuotaClient()
    monkeypatch.setattr(quotaService, "_build_client", lambda _cluster: client)
    monkeypatch.setattr(quotaService, "_send_adjustment_email", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as error:
        quotaService.adjust_storage_usage_quota(
            db_session,
            storage_usage_id=1,
            request=QuotaAdjustmentRequest(
                hard_limit=80,
                soft_limit=60,
                unit="GiB",
            ),
        )
    assert error.value.status_code == 422

    result = quotaService.adjust_storage_usage_quota(
        db_session,
        storage_usage_id=1,
        request=QuotaAdjustmentRequest(
            hard_limit=80,
            soft_limit=60,
            unit="GiB",
            soft_grace=2,
            soft_grace_unit="hours",
        ),
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
                "soft_limit": 60 * GiB,
                "soft_grace": 7200,
            },
        )
    ]
    assert result.storage_type == "isilon"
    assert db_session.get(models.StorageUsage, 1).soft_limit == 60


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
    )

    assert isinstance(result, JSONResponse)
    assert result.status_code == 403
    assert json.loads(result.body) == native_error
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

    base_config.set("jwt.secret_key", "test-secret")
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
        lambda _db, group_id, request: {
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
        lambda _db, storage_usage_id, request: {
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
