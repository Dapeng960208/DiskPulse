# -*- coding: utf-8 -*-
import json

import pytest

from appConfig import base_config
import models
from routers import vendor_event_definitions
from utils.security import issue_token


BASE_PATH = "/storage-pulse/api/admin/vendor-event-definitions"


def _user(db, *, user_id: int, username: str):
    db.add(models.User(id=user_id, rd_username=username))
    db.commit()


def _client(api_client_factory, *, user_id: int, admin_username: str = "admin"):
    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", [admin_username])
    return api_client_factory(
        [vendor_event_definitions.router],
        headers={"Authorization": f"Bearer {issue_token(user_id)}"},
    )


def _payload(**overrides):
    payload = {
        "storage_type": "netapp",
        "event_code": "disk.offline",
        "association_type": "fault_log",
        "title_zh": "磁盘离线",
        "description_zh": "存储节点报告磁盘已离线。",
        "official_reference_url": "https://docs.netapp.com/us-en/ontap-ems/",
        "default_severity": "critical",
        "version_scope": "ONTAP 9",
        "review_status": "reviewed",
        "is_active": True,
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("get", BASE_PATH, None),
        ("post", BASE_PATH, _payload()),
        ("patch", f"{BASE_PATH}/1", {"title_zh": "更新标题"}),
        ("delete", f"{BASE_PATH}/1", None),
        ("post", f"{BASE_PATH}/discover", None),
    ],
    ids=["list", "create", "update", "delete", "discover"],
)
def test_vendor_event_definition_admin_api_rejects_non_admin_users(
    db_session,
    api_client_factory,
    method,
    path,
    json_body,
):
    _user(db_session, user_id=2, username="reader")
    client = _client(api_client_factory, user_id=2)

    response = client.request(method, path, json=json_body)

    assert response.status_code == 403
    assert response.json()["detail"] == "super admin permission required"


def test_super_admin_can_filter_and_complete_vendor_event_definition_crud_with_safe_audit(
    db_session,
    api_client_factory,
):
    _user(db_session, user_id=1, username="admin")
    db_session.add_all(
        [
            models.VendorEventDefinition(
                storage_type="netapp",
                event_code="disk.failed",
                association_type="fault_log",
                title_zh="磁盘故障",
                description_zh="磁盘报告明确故障。",
                official_reference_url="https://docs.netapp.com/us-en/ontap-ems/",
                version_scope="ONTAP 9",
                review_status="reviewed",
            ),
            models.VendorEventDefinition(
                storage_type="isilon",
                event_code="SW_JOBENG_JOB_STATE",
                association_type="system_activity",
                title_zh="作业状态变化",
                description_zh="OneFS 作业状态发生变化。",
                review_status="pending",
            ),
        ]
    )
    db_session.commit()
    client = _client(api_client_factory, user_id=1)

    listed = client.get(
        BASE_PATH,
        params={
            "page": 1,
            "size": 1,
            "storage_type": "netapp",
            "association_type": "fault_log",
            "keyword": "disk",
            "review_status": "reviewed",
        },
    )

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert [item["event_code"] for item in listed.json()["content"]] == [
        "disk.failed"
    ]

    created = client.post(BASE_PATH, json=_payload())

    assert created.status_code == 201
    definition_id = created.json()["id"]
    assert created.headers["location"] == f"{BASE_PATH}/{definition_id}"
    assert created.json()["association_type"] == "fault_log"
    assert created.json()["association_type_label"] == "故障日志"

    duplicate = client.post(BASE_PATH, json=_payload())
    assert duplicate.status_code == 409

    updated = client.patch(
        f"{BASE_PATH}/{definition_id}",
        json={
            "association_type": "performance_anomaly",
            "title_zh": "磁盘性能异常",
            "default_severity": "warning",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["association_type"] == "performance_anomaly"
    assert updated.json()["title_zh"] == "磁盘性能异常"

    invalid_reviewed = client.patch(
        f"{BASE_PATH}/{definition_id}",
        json={"official_reference_url": None},
    )
    assert invalid_reviewed.status_code == 422
    assert "已审核" in invalid_reviewed.json()["detail"]

    cross_vendor_reference = client.patch(
        f"{BASE_PATH}/{definition_id}",
        json={
            "official_reference_url": (
                "https://www.dell.com/support/manuals/en-us/powerscale-onefs/events"
            )
        },
    )
    assert cross_vendor_reference.status_code == 422
    assert "NetApp" in cross_vendor_reference.json()["detail"]

    db_session.expire_all()
    audit = (
        db_session.query(models.AuditEvent)
        .filter(
            models.AuditEvent.action == "vendor_event_definition.create",
            models.AuditEvent.outcome == "success",
        )
        .one()
    )
    assert audit.actor_user_id == 1
    assert audit.resource_type == "vendor_event_definition"
    assert audit.resource_id == definition_id
    assert audit.after_summary == {
        "storage_type": "netapp",
        "event_code": "disk.offline",
        "association_type": "fault_log",
        "title_zh": "磁盘离线",
        "review_status": "reviewed",
        "is_active": True,
    }
    assert "description_zh" not in audit.after_summary
    assert "official_reference_url" not in audit.after_summary

    deleted = client.delete(f"{BASE_PATH}/{definition_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(f"{BASE_PATH}/{definition_id}").status_code == 404


def test_discover_creates_safe_unknown_pending_definition_for_observed_code(
    db_session,
    api_client_factory,
):
    _user(db_session, user_id=1, username="admin")
    db_session.add(models.StorageCluster(id=7, name="cluster-7", storage_type="isilon"))
    db_session.add(
        models.StorageAlerts(
            id=901,
            storage_cluster_id=7,
            source="isilon",
            external_event_id="observed-901",
            fingerprint="isilon:UNREVIEWED_CODE:node:7",
            severity="warning",
            alert_level="warning",
            alert_type="vendor_event",
            description="Normalized event log",
            related_type="node",
            related_info={
                "event_code": "UNREVIEWED_CODE",
                "object_id": "7",
                "raw": {"secret": "must-not-leak"},
            },
        )
    )
    db_session.commit()
    client = _client(api_client_factory, user_id=1)

    discovered = client.post(f"{BASE_PATH}/discover")

    assert discovered.status_code == 200
    assert set(discovered.json()) == {
        "created",
        "existing",
        "reconciled_incidents",
    }
    assert discovered.json()["created"] >= 1
    assert discovered.json()["existing"] >= 0
    assert discovered.json()["reconciled_incidents"] == 0

    db_session.expire_all()
    definition = (
        db_session.query(models.VendorEventDefinition)
        .filter_by(storage_type="isilon", event_code="UNREVIEWED_CODE")
        .one()
    )
    assert definition.association_type == "unknown"
    assert definition.review_status == "pending"
    assert definition.title_zh == "未收录的厂商事件代码"

    listed = client.get(BASE_PATH, params={"keyword": "UNREVIEWED_CODE"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    serialized = json.dumps(
        {"discover": discovered.json(), "list": listed.json()},
        ensure_ascii=False,
    )
    assert "must-not-leak" not in serialized
    assert "related_info" not in serialized
    assert db_session.get(models.StorageAlerts, 901).related_info["raw"]["secret"] == (
        "must-not-leak"
    )


def test_pending_definition_with_http_reference_cannot_be_promoted_to_reviewed(
    db_session,
    api_client_factory,
):
    _user(db_session, user_id=1, username="admin")
    definition = models.VendorEventDefinition(
        storage_type="isilon",
        event_code="PENDING_HTTP_REFERENCE",
        association_type="fault_log",
        title_zh="待审核事件",
        description_zh="该定义的来源地址仍不符合审核要求。",
        official_reference_url="http://docs.example.test/event",
        version_scope="OneFS test fixture",
        review_status="pending",
    )
    db_session.add(definition)
    db_session.commit()
    client = _client(api_client_factory, user_id=1)

    response = client.patch(
        f"{BASE_PATH}/{definition.id}",
        json={"review_status": "reviewed"},
    )

    assert response.status_code == 422
    assert "HTTPS" in response.json()["detail"]
    db_session.expire_all()
    assert db_session.get(models.VendorEventDefinition, definition.id).review_status == (
        "pending"
    )


def test_create_normalizes_host_only_official_reference_before_database_validation(
    db_session,
    api_client_factory,
):
    _user(db_session, user_id=1, username="admin")
    client = _client(api_client_factory, user_id=1)

    response = client.post(
        BASE_PATH,
        json=_payload(
            event_code="host.only.reference",
            official_reference_url="https://docs.netapp.com",
        ),
    )

    assert response.status_code == 201
    assert response.json()["official_reference_url"] == "https://docs.netapp.com/"


def test_create_rejects_official_reference_shapes_not_supported_by_database(
    db_session,
    api_client_factory,
):
    _user(db_session, user_id=1, username="admin")
    client = _client(api_client_factory, user_id=1)

    for index, invalid_reference in enumerate(
        (
            "https://docs.netapp.com:443/event",
            "https://docs.netapp.com./event",
            "https://docs.netapp.com/event@v1",
        )
    ):
        response = client.post(
            BASE_PATH,
            json=_payload(
                event_code=f"unsupported.reference.shape.{index}",
                official_reference_url=invalid_reference,
            ),
        )

        assert response.status_code == 422
