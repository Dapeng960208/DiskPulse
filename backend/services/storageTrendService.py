# -*- coding: utf-8 -*-
from types import SimpleNamespace

from crud import configCrud
from schemas.storageAlertRuleSchema import DEFAULT_STORAGE_ALERT_RULE
from schemas.storageTrendSchema import StorageTrendMeta, StorageTrendThresholds
from services.storageAlertRuleService import resolve_storage_alert_rule


PHYSICAL_HARD_QUOTA_TYPES = {"storage_cluster", "aggregate"}
TB_TREND_TARGET_TYPES = {"aggregate", "volume", "qtree", "project", "group", "storage_cluster"}


def _parents(target_type, target):
    if target_type == "project":
        return target, None
    if target_type == "group":
        return getattr(target, "project", None), target
    if target_type == "storage_usage":
        group = getattr(target, "group", None)
        return getattr(group, "project", None), group
    return None, None


def build_storage_trend_meta(db, *, target_type, target) -> StorageTrendMeta:
    config = configCrud.get_storage_config(db=db)
    system_rule = getattr(config, "storage_alert_rule", None) or DEFAULT_STORAGE_ALERT_RULE
    project, group = _parents(target_type, target)
    resolved = resolve_storage_alert_rule(
        target_type=target_type,
        system_rule=system_rule,
        project_rule=getattr(project, "storage_alert_rule", None),
        group_rule=getattr(group, "storage_alert_rule", None),
    )
    rule = dict(resolved.rule)
    quota_basis = "hard" if target_type in PHYSICAL_HARD_QUOTA_TYPES else rule["quota_basis"]
    limit_name = "soft_limit" if quota_basis == "soft" else "limit"
    quota_limit = getattr(target, limit_name, None)

    return StorageTrendMeta(
        quota_basis=quota_basis,
        rule_source=resolved.source,
        thresholds=StorageTrendThresholds(
            important=rule["important"]["threshold"],
            serious=rule["serious"]["threshold"],
            emergency=rule["emergency"]["threshold"],
        ),
        quota_limit_gb=float(quota_limit) if quota_limit is not None else None,
        quota_limit_tb=round(float(quota_limit) / 1024, 4) if quota_limit is not None else None,
        ratio_indicator="soft_use_ratio" if quota_basis == "soft" else "used_ratio",
    )


def build_dashboard_trend_meta(db, *, project, quota_limit_gb) -> StorageTrendMeta:
    target = project or SimpleNamespace(limit=quota_limit_gb)
    return build_storage_trend_meta(
        db,
        target_type="project" if project else "storage_cluster",
        target=target,
    )


def resolve_trend_indicator(indicator: str, trend_meta: StorageTrendMeta) -> str:
    return trend_meta.ratio_indicator if indicator == "alert_ratio" else indicator


def trend_data_unit(target_type: str, indicator: str) -> str:
    if indicator in {"use_ratio", "alert_ratio"}:
        return "%"
    if indicator == "file_used":
        return "count"
    return "TB" if target_type in TB_TREND_TARGET_TYPES else "GB"


def format_trend_data(data: list, data_unit: str) -> list:
    if data_unit != "TB":
        return data
    return [
        [*point[:-1], round(float(point[-1]) / 1024, 4)]
        if isinstance(point, (list, tuple)) and point
        else point
        for point in data
    ]
