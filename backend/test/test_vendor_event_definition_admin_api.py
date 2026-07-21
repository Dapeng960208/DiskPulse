# -*- coding: utf-8 -*-
import json

import pytest

from appConfig import base_config
import models
from routers import vendor_event_definitions
from services import vendorEventDefinitionService
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
def test_vendor_event_definition_admin_api_rejects_unauthenticated_requests(
    db_session,
    api_client_factory,
    method,
    path,
    json_body,
):
    base_config.set("jwt.secret_key", "test-secret")
    base_config.set("super_admin_usernames", ["admin"])
    client = api_client_factory([vendor_event_definitions.router])

    response = client.request(method, path, json=json_body)

    assert response.status_code == 401


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

    update_audit = (
        db_session.query(models.AuditEvent)
        .filter(
            models.AuditEvent.action == "vendor_event_definition.update",
            models.AuditEvent.outcome == "success",
        )
        .one()
    )
    assert update_audit.actor_user_id == 1
    assert update_audit.resource_id == definition_id
    assert update_audit.before_summary["association_type"] == "fault_log"
    assert update_audit.after_summary["association_type"] == "performance_anomaly"
    assert update_audit.after_summary["title_zh"] == "磁盘性能异常"

    update_failures = (
        db_session.query(models.AuditEvent)
        .filter(
            models.AuditEvent.action == "vendor_event_definition.update",
            models.AuditEvent.outcome == "failure",
        )
        .all()
    )
    assert len(update_failures) == 2
    assert {failure.reason_code for failure in update_failures} == {
        "vendor_event_definition_validation_failed"
    }
    assert all(failure.resource_id == definition_id for failure in update_failures)

    deleted = client.delete(f"{BASE_PATH}/{definition_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(f"{BASE_PATH}/{definition_id}").status_code == 404

    db_session.expire_all()
    delete_audit = (
        db_session.query(models.AuditEvent)
        .filter(
            models.AuditEvent.action == "vendor_event_definition.delete",
            models.AuditEvent.outcome == "success",
        )
        .one()
    )
    assert delete_audit.actor_user_id == 1
    assert delete_audit.resource_id == definition_id
    assert delete_audit.before_summary["event_code"] == "disk.offline"
    assert delete_audit.after_summary is None


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
    db_session.add(
        models.StorageAlerts(
            id=902,
            storage_cluster_id=7,
            source="isilon",
            external_event_id="observed-902",
            fingerprint="isilon:oversized:node:7",
            severity="warning",
            alert_level="warning",
            alert_type="vendor_event",
            description="Oversized code must not abort discover",
            related_type="node",
            related_info={"event_code": "X" * 300, "object_id": "7"},
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
    common_seed_count = len(vendorEventDefinitionService.COMMON_DEFINITIONS)
    assert discovered.json()["created"] == common_seed_count + 1
    assert discovered.json()["existing"] == 0
    assert discovered.json()["reconciled_incidents"] == 0
    assert (
        db_session.query(models.VendorEventDefinition)
        .filter_by(storage_type="isilon", event_code="X" * 300)
        .count()
    ) == 0

    repeated = client.post(f"{BASE_PATH}/discover")
    assert repeated.status_code == 200
    assert repeated.json()["created"] == 0
    assert repeated.json()["existing"] == 1

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

    discover_audits = (
        db_session.query(models.AuditEvent)
        .filter(
            models.AuditEvent.action == "vendor_event_definition.discover",
            models.AuditEvent.outcome == "success",
        )
        .all()
    )
    assert len(discover_audits) == 2
    assert all(audit.actor_user_id == 1 for audit in discover_audits)
    summaries = [audit.after_summary for audit in discover_audits]
    assert {
        "created": common_seed_count + 1,
        "existing": 0,
        "reconciled_incidents": 0,
    } in summaries
    assert {"created": 0, "existing": 1, "reconciled_incidents": 0} in summaries


def test_discover_upgrades_generated_placeholder_when_common_seed_matches(
    db_session,
    api_client_factory,
):
    _user(db_session, user_id=1, username="admin")
    seed = dict(vendorEventDefinitionService.COMMON_DEFINITIONS[0])
    placeholder = models.VendorEventDefinition(
        storage_type=seed["storage_type"],
        event_code=seed["event_code"],
        association_type="unknown",
        title_zh=vendorEventDefinitionService.UNKNOWN_TITLE_ZH,
        description_zh=vendorEventDefinitionService.UNKNOWN_DESCRIPTION_ZH,
        review_status="pending",
    )
    db_session.add(placeholder)
    db_session.commit()
    placeholder_id = placeholder.id
    client = _client(api_client_factory, user_id=1)

    discovered = client.post(f"{BASE_PATH}/discover")

    assert discovered.status_code == 200
    db_session.expire_all()
    upgraded = db_session.get(models.VendorEventDefinition, placeholder_id)
    assert upgraded.association_type == seed["association_type"]
    assert upgraded.title_zh == seed["title_zh"]
    assert upgraded.review_status == seed["review_status"]
    assert upgraded.official_reference_url == seed["official_reference_url"]


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
