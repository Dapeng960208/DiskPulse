# -*- coding: utf-8 -*-
import ast
import importlib
import importlib.util
import inspect
import textwrap
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest
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

    assert {"event_type", "quota_basis", "delivery_status"} <= public_fields
    assert {"recipient_usernames", "delivery_error"}.isdisjoint(public_fields)
    assert {"event_type", "quota_basis", "delivery_status"} <= set(
        inspect.signature(crud.get_storage_alerts).parameters
    )


def test_storage_rule_api_schemas_expose_rules_without_secrets_or_internal_delivery_fields():
    config_fields = set(_module("schemas.configSchemas").StorageConfPublic.model_fields)
    project_fields = set(_module("schemas.projectsSchema").Project.model_fields)
    group_fields = set(_module("schemas.groupSchema").Group.model_fields)

    assert "storage_alert_rule" in config_fields
    assert {"storage_alert_rule", "is_alert"} <= project_fields
    assert {"storage_alert_rule", "alert_cc_user_ids"} <= group_fields
    assert "app_key" not in config_fields


def test_collection_enqueues_alert_evaluation_only_after_collection_transaction():
    storages = _module("celery_tasks.tasks.storages")
    tree = ast.parse(textwrap.dedent(inspect.getsource(storages.storages_schedule_fetching_task)))
    function = tree.body[0]
    transactions = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.With)
        and any("db.begin" in ast.unparse(item.context_expr) for item in node.items)
    ]
    assert transactions
    transaction = transactions[0]
    assert any(
        isinstance(node, ast.Assign)
        and "refreshed_project_ids" in ast.unparse(node)
        and "finalize_project_totals" in ast.unparse(node)
        for node in ast.walk(transaction)
    )
    enqueues = [
        node
        for node in ast.walk(function)
        if "evaluate_storage_alerts_task.delay" in ast.unparse(node)
        and isinstance(node, ast.Call)
    ]

    assert len(enqueues) == 1
    assert enqueues[0].lineno > transaction.end_lineno


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
