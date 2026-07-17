# -*- coding: utf-8 -*-
import importlib
import importlib.util
import inspect
import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from pydantic import ValidationError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULE = {
    "quota_basis": "hard",
    "important": {"threshold": 80, "repeat_hours": 24},
    "serious": {"threshold": 90, "repeat_hours": 6},
    "emergency": {"threshold": 95, "repeat_hours": 1},
}
NOW = datetime(2026, 7, 16, 10, 0, 0)


def _module(name):
    return importlib.import_module(name)


def _transition(state, ratio, *, rule=DEFAULT_RULE, observed_at=NOW, soft_limit_available=True):
    return _module("services.storageAlertRuleService").transition_alert_state(
        state=state,
        rule=rule,
        use_ratio=ratio,
        observed_at=observed_at,
        soft_limit_available=soft_limit_available,
    )


def test_rule_schema_accepts_complete_rule_and_rejects_invalid_contracts():
    schema = _module("schemas.storageAlertRuleSchema")

    assert schema.StorageAlertRule.model_validate(DEFAULT_RULE).model_dump() == DEFAULT_RULE
    invalid_rules = [
        {**DEFAULT_RULE, "quota_basis": "automatic"},
        {**DEFAULT_RULE, "important": {"threshold": 90, "repeat_hours": 24}},
        {**DEFAULT_RULE, "emergency": {"threshold": 101, "repeat_hours": 1}},
        {**DEFAULT_RULE, "serious": {"threshold": 90, "repeat_hours": 0}},
        {key: value for key, value in DEFAULT_RULE.items() if key != "serious"},
    ]
    for invalid_rule in invalid_rules:
        with pytest.raises(ValidationError):
            schema.StorageAlertRule.model_validate(invalid_rule)


def test_rule_signature_is_canonical_and_changes_with_effective_rule():
    service = _module("services.storageAlertRuleService")
    reordered = dict(reversed(list(DEFAULT_RULE.items())))

    assert service.canonical_rule_signature(DEFAULT_RULE) == service.canonical_rule_signature(reordered)
    assert len(service.canonical_rule_signature(DEFAULT_RULE)) == 64
    assert service.canonical_rule_signature(DEFAULT_RULE) != service.canonical_rule_signature(
        {**DEFAULT_RULE, "quota_basis": "soft"}
    )


@pytest.mark.parametrize(
    ("target_type", "project_rule", "group_rule", "expected_source"),
    [
        ("storage_usage", None, None, "system"),
        ("storage_usage", {**DEFAULT_RULE, "quota_basis": "soft"}, None, "project"),
        ("storage_usage", DEFAULT_RULE, {**DEFAULT_RULE, "quota_basis": "soft"}, "group"),
        ("group", DEFAULT_RULE, None, "project"),
        ("group", DEFAULT_RULE, {**DEFAULT_RULE, "quota_basis": "soft"}, "group"),
        ("project", {**DEFAULT_RULE, "quota_basis": "soft"}, DEFAULT_RULE, "project"),
    ],
)
def test_rule_inheritance_uses_complete_nearest_override(
    target_type, project_rule, group_rule, expected_source
):
    service = _module("services.storageAlertRuleService")

    resolved = service.resolve_storage_alert_rule(
        target_type=target_type,
        system_rule=DEFAULT_RULE,
        project_rule=project_rule,
        group_rule=group_rule,
    )

    assert resolved.source == expected_source
    assert resolved.rule == {"system": DEFAULT_RULE, "project": project_rule, "group": group_rule}[
        expected_source
    ]


def test_initial_alert_requires_two_consecutive_samples_and_uses_second_level():
    first = _transition(None, 81)
    assert first.event_type is None
    assert first.state.consecutive_breach_count == 1

    second = _transition(first.state, 96, observed_at=NOW + timedelta(minutes=1))
    assert (second.event_type, second.level) == ("trigger", "emergency")
    assert second.state.current_level == "emergency"
    assert second.state.consecutive_breach_count == 2


def test_normal_sample_between_breaches_clears_confirmation_count():
    first = _transition(None, 85)
    normal = _transition(first.state, 79, observed_at=NOW + timedelta(minutes=1))
    assert normal.event_type is None
    assert normal.state.consecutive_breach_count == 0


def test_active_alert_escalates_immediately_and_downgrades_silently():
    triggered = _transition(_transition(None, 82).state, 82, observed_at=NOW + timedelta(minutes=1))
    escalation = _transition(triggered.state, 92, observed_at=NOW + timedelta(minutes=2))
    assert (escalation.event_type, escalation.level) == ("escalation", "serious")

    downgrade = _transition(escalation.state, 85, observed_at=NOW + timedelta(minutes=3))
    assert downgrade.event_type is None
    assert downgrade.state.current_level == "important"

    reescalation = _transition(downgrade.state, 92, observed_at=NOW + timedelta(minutes=4))
    assert (reescalation.event_type, reescalation.level) == ("escalation", "serious")


def test_repeat_waits_for_current_level_frequency_and_recovery_clears_active_state():
    triggered = _transition(_transition(None, 91).state, 91, observed_at=NOW + timedelta(minutes=1))
    early = _transition(triggered.state, 91, observed_at=NOW + timedelta(hours=5))
    assert early.event_type is None

    repeated = _transition(early.state, 91, observed_at=NOW + timedelta(hours=6, minutes=1))
    assert (repeated.event_type, repeated.level) == ("repeat", "serious")

    recovered = _transition(repeated.state, 79, observed_at=NOW + timedelta(hours=6, minutes=2))
    assert (recovered.event_type, recovered.previous_level) == ("recovery", "serious")
    assert recovered.state.current_level is None


def test_rule_change_resets_state_silently_and_soft_missing_does_not_mutate_state():
    triggered = _transition(_transition(None, 91).state, 91, observed_at=NOW + timedelta(minutes=1))
    soft_rule = {**DEFAULT_RULE, "quota_basis": "soft"}

    reset = _transition(triggered.state, 91, rule=soft_rule, observed_at=NOW + timedelta(minutes=2))
    assert reset.event_type is None
    assert reset.state.current_level is None
    assert reset.state.consecutive_breach_count == 1

    skipped = _transition(
        triggered.state,
        99,
        rule=soft_rule,
        observed_at=NOW + timedelta(minutes=3),
        soft_limit_available=False,
    )
    assert skipped.skipped is True
    assert skipped.state == triggered.state


@pytest.mark.parametrize(
    ("debug", "emergency", "expected"),
    [
        (False, False, ["owner", "group-cc", "global-cc"]),
        (False, True, ["owner", "group-cc", "admin", "global-cc"]),
        (True, True, ["admin", "global-cc"]),
    ],
)
def test_recipient_resolution_cleans_deduplicates_and_honors_emergency_and_debug(
    debug, emergency, expected
):
    service = _module("services.storageAlertRuleService")

    recipients = service.resolve_recipient_usernames(
        primary_usernames=[" owner ", ""],
        group_cc_usernames=["group-cc", "owner"],
        global_cc_usernames=["global-cc", " group-cc "],
        debug=debug,
        emergency=emergency,
        super_admin_usernames=["admin", " admin "],
    )

    assert recipients == expected


def test_recipient_resolution_returns_empty_when_every_recipient_source_is_empty():
    service = _module("services.storageAlertRuleService")

    assert service.resolve_recipient_usernames(
        primary_usernames=[],
        group_cc_usernames=[],
        global_cc_usernames=[],
        debug=False,
        emergency=False,
        super_admin_usernames=[],
    ) == []


def test_feishu_service_uses_token_and_post_protocol_without_exposing_app_key():
    module = _module("services.feishuNotificationService")
    token_response = Mock()
    token_response.raise_for_status.return_value = None
    token_response.json.return_value = {"data": {"access_token": "token-1"}}
    send_response = Mock()
    send_response.raise_for_status.return_value = None
    send_response.json.return_value = {"code": 0}
    config = {
        "enabled": True,
        "base_url": "https://notify.example/api",
        "app": "feishu_bot",
        "app_key": "secret-value",
        "timeout_seconds": 5,
        "tls_verify": True,
    }

    with patch.object(module.httpx, "post", side_effect=[token_response, send_response]) as post:
        module.FeishuNotificationService(config).send(
            usernames=["alice"], title="存储告警", paragraphs=[[{"tag": "text", "text": "超限"}]]
        )

    assert post.call_args_list == [
        call(
            "https://notify.example/api/auth/token",
            json={"app": "feishu_bot", "app_key": "secret-value"},
            timeout=5,
            verify=True,
        ),
        call(
            "https://notify.example/api/send_info",
            headers={"Authorization": "Bearer token-1"},
            json={
                "username": "alice",
                "msg_type": "post",
                "title": "存储告警",
                "paragraphs": [[{"tag": "text", "text": "超限"}]],
            },
            timeout=5,
            verify=True,
        ),
    ]
    assert "secret-value" not in repr(module.FeishuNotificationService(config))


def test_delivery_retry_contract_is_initial_plus_one_five_and_fifteen_minutes():
    tasks = _module("celery_tasks.tasks.storage_alerts")

    assert tasks.RETRY_DELAYS_SECONDS == (60, 300, 900)
    assert tasks.MAX_DELIVERY_ATTEMPTS == 4


def test_public_alert_schema_and_filter_contract_hide_delivery_internals():
    schema = _module("schemas.storageAlertsSchema").StorageAlert
    crud = _module("crud.storageAlertCrud")
    public_fields = set(schema.model_fields)

    assert {"event_type", "quota_basis", "delivery_status", "cluster_name", "project_name"} <= public_fields
    assert {"recipient_usernames", "delivery_error"}.isdisjoint(public_fields)
    assert {"event_type", "quota_basis", "delivery_status"} <= set(
        inspect.signature(crud.get_storage_alerts).parameters
    )


def test_alert_list_resolves_cluster_and_project_for_historical_directory_events(db_session):
    import models

    db_session.add_all(
        [
            models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"),
            models.Project(id=1, name="project-a"),
            models.GroupTag(id=1, name="team"),
            models.Volume(id=1, storage_cluster_id=1, name="volume-a"),
            models.Group(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                volume_id=1,
                name="group-a",
            ),
            models.StorageUsage(id=1, storage_cluster_id=1, group_id=1, linux_path="/data/alice"),
            models.StorageAlerts(
                storage_cluster_id=1,
                source="diskpulse",
                severity="important",
                alert_level="important",
                alert_type="alert",
                description="legacy summary",
                threshold=80,
                avg_use_ratio=85,
                related_id=1,
                related_type="StorageUsage",
                related_info={"context": {"cluster": "cluster-a", "linux_path": "/data/alice"}},
            ),
        ]
    )
    db_session.commit()

    rows, total = _module("crud.storageAlertCrud").get_storage_alerts(db_session, 1, 20)

    assert total == 1
    assert (rows[0].cluster_name, rows[0].project_name) == ("cluster-a", "project-a")


def test_storage_rule_api_schemas_expose_rules_without_secrets_or_internal_delivery_fields():
    config_fields = set(_module("schemas.configSchemas").StorageConfPublic.model_fields)
    project_fields = set(_module("schemas.projectsSchema").Project.model_fields)
    group_fields = set(_module("schemas.groupSchema").Group.model_fields)

    assert "storage_alert_rule" in config_fields
    assert {"storage_alert_rule", "is_alert"} <= project_fields
    assert {"storage_alert_rule", "alert_cc_user_ids"} <= group_fields
    assert "app_key" not in config_fields


def test_storage_alert_evaluation_has_an_independent_beat_schedule():
    worker_source = (BACKEND_ROOT / "celery_worker.py").read_text(encoding="utf-8")
    collection_source = (BACKEND_ROOT / "celery_tasks" / "tasks" / "storages.py").read_text(
        encoding="utf-8"
    )

    assert '"storage_alerts_schedule_task": {' in worker_source
    assert (
        '"task": "celery_tasks.tasks.storage_alerts.storage_alerts_schedule_task"'
        in worker_source
    )
    assert "evaluate_storage_alerts_task.delay" not in collection_source


def test_independent_alert_schedule_selects_only_the_latest_committed_sample(
    db_session, session_factory, monkeypatch
):
    import models

    tasks = _module("celery_tasks.tasks.storage_alerts")
    monkeypatch.setattr(tasks, "SessionLocal", session_factory)
    previous = NOW - timedelta(minutes=1)
    db_session.add_all(
        [
            models.Project(id=1, name="old-project", updated_at=previous),
            models.Project(id=2, name="latest-project", updated_at=NOW),
            models.Group(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                volume_id=1,
                name="old-group",
                updated_at=previous,
            ),
            models.Group(
                id=2,
                project_id=2,
                storage_cluster_id=2,
                group_tag_id=1,
                volume_id=2,
                name="latest-group",
                updated_at=NOW,
            ),
            models.StorageUsage(
                id=1,
                storage_cluster_id=1,
                linux_path="/old",
                updated_at=previous,
            ),
            models.StorageUsage(
                id=2,
                storage_cluster_id=2,
                linux_path="/latest",
                updated_at=NOW,
            ),
        ]
    )
    db_session.commit()

    assert tasks._latest_alert_sample() == {
        "successful_cluster_ids": (2,),
        "refreshed_project_ids": (2,),
        "sample_identity": NOW.isoformat(),
        "refreshed_storage_usage_ids": (2,),
        "refreshed_group_ids": (2,),
    }


def test_storage_alert_migration_revision_and_schema_contract():
    path = BACKEND_ROOT / "migrate" / "versions" / "000000000006_storage_alert_rules.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    source = path.read_text(encoding="utf-8")

    assert migration.revision == "000000000006"
    assert migration.down_revision == "000000000005"
    for contract in (
        "storage_alert_rule",
        "alert_cc_user_ids",
        "storage_alert_states",
        "event_type",
        "quota_basis",
        "delivery_status",
        "recipient_usernames",
        "delivery_attempts",
        "next_attempt_at",
        "delivery_error",
    ):
        assert contract in source


def test_storage_alert_migration_preserves_default_rule_values_and_offline_sql():
    paths = sorted((BACKEND_ROOT / "migrate" / "versions").glob("00000000000[1-6]_*.py"))
    migrations = []
    for path in paths:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migrations.append(migration)
    with sa.create_engine("sqlite://").begin() as connection:
        for migration in migrations[:-1]:
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
        connection.execute(sa.text("INSERT INTO storage_conf (id, name) VALUES (1, 'test')"))
        migration = migrations[-1]
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        stored = connection.execute(
            sa.text("SELECT storage_alert_rule FROM storage_conf WHERE id = 1")
        ).scalar_one()
        assert json.loads(stored) == DEFAULT_RULE
        migration.downgrade()

    for dialect in ("postgresql", "mysql"):
        output = io.StringIO()
        context = MigrationContext.configure(
            dialect_name=dialect,
            opts={"as_sql": True, "output_buffer": output},
        )
        migration.op = Operations(context)
        migration.upgrade()
        sql = output.getvalue().replace("\\:", ":")
        for value in (80, 24, 90, 6, 95, 1):
            assert f'"threshold":{value}' in sql or f'"repeat_hours":{value}' in sql


def test_storage_alert_migration_generates_sqlite_offline_upgrade_and_downgrade_sql():
    path = BACKEND_ROOT / "migrate" / "versions" / "000000000006_storage_alert_rules.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    output = io.StringIO()
    context = MigrationContext.configure(
        dialect_name="sqlite",
        opts={"as_sql": True, "output_buffer": output},
    )
    migration.op = Operations(context)

    migration.upgrade()
    migration.downgrade()

    sql = output.getvalue().replace("\\:", ":")
    assert "ALTER TABLE storage_conf ADD COLUMN storage_alert_rule" in sql
    assert "ALTER TABLE groups ADD COLUMN alert_cc_user_ids" in sql
    assert "CREATE TABLE storage_alert_states" in sql
    assert "ALTER TABLE storage_alerts ADD COLUMN delivery_status" in sql
    assert "DROP TABLE storage_alert_states" in sql
    assert "ALTER TABLE storage_conf DROP COLUMN storage_alert_rule" in sql
    for value in (80, 24, 90, 6, 95, 1):
        assert f'"threshold":{value}' in sql or f'"repeat_hours":{value}' in sql


def test_evaluator_uses_current_successful_samples_and_keeps_project_event_aggregated(
    db_session, session_factory, monkeypatch
):
    import models

    tasks = _module("celery_tasks.tasks.storage_alerts")
    monkeypatch.setattr(tasks, "SessionLocal", session_factory)
    config = {
        "feishu_notification": {"enabled": True, "debug": False, "cc_usernames": ["global"]},
        "super_admin_usernames": ["admin"],
    }
    monkeypatch.setattr(tasks.base_config, "get", lambda key, default=None: config.get(key, default))
    db_session.add_all(
        [
            models.User(id=1, rd_username="alice", is_alert=True),
            models.User(id=2, rd_username="owner", is_alert=True),
            models.User(id=3, rd_username="group-cc", is_alert=True),
            models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"),
            models.StorageCluster(id=2, name="cluster-b", storage_type="netapp"),
            models.GroupTag(id=1, name="team"),
            models.Project(
                id=1,
                name="project-a",
                status=1,
                is_alert=True,
                in_charge_user_id=2,
                limit=200,
                used=192,
                use_ratio=96,
            ),
            models.Volume(id=1, storage_cluster_id=1, name="vol-a"),
            models.Volume(id=2, storage_cluster_id=2, name="vol-b"),
            models.Group(
                id=1,
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                volume_id=1,
                name="group-a",
                enable_monitoring=True,
                in_charge_user_id=2,
                alert_cc_user_ids=[3],
                limit=100,
                used=96,
                use_ratio=96,
                updated_at=NOW,
            ),
            models.Group(
                id=2,
                project_id=1,
                storage_cluster_id=2,
                group_tag_id=1,
                volume_id=2,
                name="group-b",
                enable_monitoring=True,
                limit=100,
                used=96,
                use_ratio=96,
                updated_at=NOW,
            ),
            models.StorageUsage(
                id=1,
                storage_cluster_id=1,
                group_id=1,
                user_id=1,
                linux_path="/data/alice",
                limit=100,
                used=96,
                use_ratio=96,
                updated_at=NOW,
            ),
            models.StorageUsage(
                id=2,
                storage_cluster_id=1,
                group_id=1,
                user_id=1,
                linux_path="/data/stale",
                limit=100,
                used=99,
                use_ratio=99,
                updated_at=NOW - timedelta(hours=1),
            ),
            models.StorageConf(id=1, name="storage conf", storage_alert_rule=DEFAULT_RULE),
        ]
    )
    db_session.commit()

    assert tasks.evaluate_storage_alerts(
        [1], [1], NOW.isoformat(), [1], [1]
    ) == []
    second_sample = NOW + timedelta(minutes=1)
    db_session.query(models.StorageUsage).filter_by(id=1).update({"updated_at": second_sample})
    db_session.query(models.Group).filter_by(id=1).update({"updated_at": second_sample})
    db_session.commit()
    event_ids = tasks.evaluate_storage_alerts(
        [1], [1], second_sample.isoformat(), [1], [1]
    )

    assert tasks.evaluate_storage_alerts(
        [1], [1], second_sample.isoformat(), [1], [1]
    ) == []

    events = db_session.query(models.StorageAlerts).filter(models.StorageAlerts.id.in_(event_ids)).all()
    by_type = {event.related_type: event for event in events}
    assert set(by_type) == {"StorageUsage", "Group", "Project"}
    assert by_type["Project"].storage_cluster_id is None
    assert by_type["StorageUsage"].recipient_usernames == [
        "alice",
        "group-cc",
        "admin",
        "global",
    ]
    assert by_type["Group"].recipient_usernames == [
        "owner",
        "group-cc",
        "admin",
        "global",
    ]
    assert by_type["Project"].recipient_usernames == ["owner", "admin", "global"]
    assert all(event.alert_type == "alert" for event in events)
    assert by_type["StorageUsage"].description == (
        "Linux目录 /data/alice 首次告警（使用率 96.00%）"
    )
    assert by_type["Group"].description == "项目组 group-a 首次告警（使用率 96.00%）"
    assert by_type["Project"].description == "项目 project-a 首次告警（使用率 96.00%）"
    assert by_type["StorageUsage"].related_info["context"]["project"] == "project-a"
    assert db_session.query(models.StorageAlertState).filter_by(target_type="storage_usage", target_id=2).first() is None

    usage_text = "".join(
        item["text"] for item in by_type["StorageUsage"].related_info["paragraphs"][0]
    )
    assert all(
        value in usage_text
        for value in (
            "用户名：alice",
            "集群：cluster-a",
            "项目：project-a",
            "项目组标签：team",
            "项目组：group-a",
            "Linux路径：/data/alice",
            "事件：首次告警",
            "采用口径：硬限额",
            "硬限额：100.00 GB",
            "软限额：未设置",
            "已使用：96.00 GB",
            "硬限额使用率：96.00%",
            "软限额使用率：未设置",
        )
    )
    project_text = "".join(
        item["text"] for item in by_type["Project"].related_info["paragraphs"][0]
    )
    assert "项目：project-a" in project_text
    assert "集群：cluster-a, cluster-b" in project_text
    recovery_text = "".join(
        item["text"]
        for item in tasks._paragraphs(
            db_session.get(models.Project, 1),
            DEFAULT_RULE,
            79,
            "recovery",
            {"project": "project-a"},
            "serious",
        )[0]
    )
    assert "事件：恢复通知" in recovery_text
    assert "恢复前等级：严重" in recovery_text


def test_group_alert_cc_users_are_deduplicated_and_must_exist(db_session):
    import models
    from crud import groupCrud
    from schemas.groupSchema import GroupBindingCreate

    db_session.add_all(
        [
            models.User(id=1, rd_username="cc-user"),
            models.Project(id=1, name="project-a"),
            models.StorageCluster(id=1, name="cluster-a", storage_type="netapp"),
            models.GroupTag(id=1, name="team"),
            models.Volume(id=1, storage_cluster_id=1, name="volume-a"),
        ]
    )
    db_session.commit()
    with pytest.raises(HTTPException) as error:
        groupCrud.create_group(
            db_session,
            GroupBindingCreate(
                name="invalid",
                project_id=1,
                storage_cluster_id=1,
                group_tag_id=1,
                volume_id=1,
                alert_cc_user_ids=[999],
            ),
        )
    assert error.value.status_code == 422
    group = groupCrud.create_group(
        db_session,
        GroupBindingCreate(
            name="valid",
            project_id=1,
            storage_cluster_id=1,
            group_tag_id=1,
            volume_id=1,
            alert_cc_user_ids=[1, 1],
        ),
    )
    assert group.alert_cc_user_ids == [1]


def test_delivery_marks_failed_after_initial_attempt_and_three_retries(
    db_session, session_factory, monkeypatch
):
    import models

    tasks = _module("celery_tasks.tasks.storage_alerts")
    monkeypatch.setattr(tasks, "SessionLocal", session_factory)
    monkeypatch.setattr(
        tasks.base_config,
        "get",
        lambda key, default=None: {
            "feishu_notification": {
                "enabled": True,
                "base_url": "https://notify.example/api",
                "app": "bot",
                "app_key": "secret",
            }
        }.get(key, default),
    )
    event = models.StorageAlerts(
        source="diskpulse",
        severity="important",
        alert_level="important",
        alert_type="usage",
        description="test",
        threshold=80,
        avg_use_ratio=81,
        related_type="group",
        event_type="trigger",
        quota_basis="hard",
        delivery_status="pending",
        recipient_usernames=["alice"],
        next_attempt_at=NOW,
        related_info={"title": "告警", "paragraphs": []},
    )
    db_session.add(event)
    db_session.commit()

    with patch.object(tasks.FeishuNotificationService, "send", side_effect=RuntimeError("down")):
        for _ in range(4):
            tasks.deliver_storage_alert_task.run(event.id)

    db_session.refresh(event)
    assert event.delivery_attempts == 4
    assert event.delivery_status == "failed"
    assert event.next_attempt_at is None
    assert event.delivery_error == "down"


def test_storage_alert_delivery_writes_service_audit_attempt_and_result(db_session, session_factory, monkeypatch):
    import models

    tasks = _module("celery_tasks.tasks.storage_alerts")
    monkeypatch.setattr(tasks, "SessionLocal", session_factory)
    monkeypatch.setattr(
        tasks.base_config,
        "get",
        lambda key, default=None: {
            "feishu_notification": {
                "enabled": True,
                "base_url": "https://notify.example/api",
                "app": "bot",
                "app_key": "notification-secret",
            }
        }.get(key, default),
    )
    event = models.StorageAlerts(
        source="diskpulse",
        severity="important",
        alert_level="important",
        alert_type="usage",
        description="test",
        threshold=80,
        avg_use_ratio=81,
        related_type="group",
        event_type="trigger",
        quota_basis="hard",
        delivery_status="pending",
        recipient_usernames=["alice"],
        next_attempt_at=NOW,
        related_info={"title": "private notification title", "paragraphs": []},
    )
    db_session.add(event)
    db_session.commit()

    with patch.object(tasks.FeishuNotificationService, "send", return_value=[]):
        tasks.deliver_storage_alert_task.run(event.id)

    events = db_session.query(models.AuditEvent).order_by(models.AuditEvent.occurred_at, models.AuditEvent.id).all()
    assert [(item.phase, item.outcome) for item in events] == [("attempt", "success"), ("result", "success")]
    assert all(
        (item.action, item.resource_type, item.resource_id, item.actor_type)
        == ("notification.storage_alert.deliver", "storage_alert", event.id, "service")
        for item in events
    )
    assert len({item.operation_id for item in events}) == 1
    payload = str([(item.before_summary, item.after_summary, item.event_metadata) for item in events])
    assert "private notification title" not in payload
    assert "notification-secret" not in payload
