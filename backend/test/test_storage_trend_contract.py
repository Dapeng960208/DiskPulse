# -*- coding: utf-8 -*-
from types import SimpleNamespace


SYSTEM_RULE = {
    "quota_basis": "hard",
    "important": {"threshold": 80, "repeat_hours": 24},
    "serious": {"threshold": 90, "repeat_hours": 6},
    "emergency": {"threshold": 95, "repeat_hours": 1},
}

PROJECT_RULE = {
    "quota_basis": "soft",
    "important": {"threshold": 72, "repeat_hours": 12},
    "serious": {"threshold": 86, "repeat_hours": 4},
    "emergency": {"threshold": 94, "repeat_hours": 1},
}

GROUP_RULE = {
    "quota_basis": "soft",
    "important": {"threshold": 75, "repeat_hours": 8},
    "serious": {"threshold": 88, "repeat_hours": 3},
    "emergency": {"threshold": 96, "repeat_hours": 1},
}


def test_public_realtime_and_dashboard_schemas_expose_trend_meta():
    from schemas.commonSchema import ResponseStorageUsageModel
    from schemas.dashboardSchema import DashboardSummaryResponse
    from schemas.storageTrendSchema import StorageTrendMeta

    assert "trend_meta" in ResponseStorageUsageModel.model_fields
    assert "trend_meta" in DashboardSummaryResponse.model_fields
    assert set(StorageTrendMeta.model_fields) == {
        "quota_basis",
        "rule_source",
        "thresholds",
        "quota_limit_gb",
        "ratio_indicator",
    }


def test_effective_trend_meta_uses_group_project_system_precedence(monkeypatch):
    from services import storageTrendService

    monkeypatch.setattr(
        storageTrendService.configCrud,
        "get_storage_config",
        lambda db: SimpleNamespace(storage_alert_rule=SYSTEM_RULE),
    )
    project = SimpleNamespace(
        storage_alert_rule=PROJECT_RULE,
        limit=500,
        soft_limit=450,
    )
    group = SimpleNamespace(
        storage_alert_rule=GROUP_RULE,
        project=project,
        limit=200,
        soft_limit=180,
    )
    usage = SimpleNamespace(group=group, limit=100, soft_limit=90)

    group_meta = storageTrendService.build_storage_trend_meta(
        None, target_type="storage_usage", target=usage
    )
    assert group_meta.model_dump() == {
        "quota_basis": "soft",
        "rule_source": "group",
        "thresholds": {"important": 75, "serious": 88, "emergency": 96},
        "quota_limit_gb": 90.0,
        "ratio_indicator": "soft_use_ratio",
    }

    group.storage_alert_rule = None
    project_meta = storageTrendService.build_storage_trend_meta(
        None, target_type="storage_usage", target=usage
    )
    assert project_meta.rule_source == "project"
    assert project_meta.thresholds.important == 72

    project.storage_alert_rule = None
    system_meta = storageTrendService.build_storage_trend_meta(
        None, target_type="storage_usage", target=usage
    )
    assert system_meta.rule_source == "system"
    assert system_meta.quota_basis == "hard"
    assert system_meta.quota_limit_gb == 100


def test_physical_capacity_trends_force_hard_quota_but_keep_system_thresholds(monkeypatch):
    from services import storageTrendService

    soft_system_rule = {**SYSTEM_RULE, "quota_basis": "soft"}
    monkeypatch.setattr(
        storageTrendService.configCrud,
        "get_storage_config",
        lambda db: SimpleNamespace(storage_alert_rule=soft_system_rule),
    )

    meta = storageTrendService.build_storage_trend_meta(
        None,
        target_type="storage_cluster",
        target=SimpleNamespace(limit=2048, soft_limit=1024),
    )

    assert meta.quota_basis == "hard"
    assert meta.rule_source == "system"
    assert meta.quota_limit_gb == 2048
    assert meta.ratio_indicator == "used_ratio"
    assert meta.thresholds.model_dump() == {
        "important": 80,
        "serious": 90,
        "emergency": 95,
    }


def test_alert_ratio_resolves_to_effective_hard_or_soft_history_column():
    from services.storageTrendService import resolve_trend_indicator

    hard = SimpleNamespace(ratio_indicator="used_ratio")
    soft = SimpleNamespace(ratio_indicator="soft_use_ratio")

    assert resolve_trend_indicator("alert_ratio", hard) == "used_ratio"
    assert resolve_trend_indicator("alert_ratio", soft) == "soft_use_ratio"
    assert resolve_trend_indicator("use_ratio", soft) == "use_ratio"
    assert resolve_trend_indicator("used", soft) == "used"


def test_questdb_query_whitelist_and_models_include_soft_history_snapshots():
    from crud.questDbCrud import ALLOWED_INDICATORS
    from questdb.models import (
        GroupStorageUsage,
        ProjectStorageUsage,
        QtreeStorageUsage,
        StorageUsage,
        VolumeStorageUsage,
    )

    assert "soft_use_ratio" in ALLOWED_INDICATORS
    for model in (
        VolumeStorageUsage,
        QtreeStorageUsage,
        ProjectStorageUsage,
        GroupStorageUsage,
        StorageUsage,
    ):
        assert {"soft_limit", "soft_use_ratio"} <= set(model.__table__.columns.keys())

