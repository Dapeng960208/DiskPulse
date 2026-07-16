# -*- coding: utf-8 -*-
import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any

from schemas.storageAlertRuleSchema import StorageAlertRule


LEVELS = ("important", "serious", "emergency")


@dataclass(frozen=True)
class ResolvedRule:
    rule: dict
    source: str


@dataclass(frozen=True)
class AlertState:
    rule_signature: str
    consecutive_breach_count: int = 0
    current_level: str | None = None
    last_use_ratio: float | None = None
    last_observed_at: datetime | None = None
    last_notified_at: datetime | None = None


@dataclass(frozen=True)
class TransitionResult:
    state: AlertState | Any
    event_type: str | None = None
    level: str | None = None
    previous_level: str | None = None
    skipped: bool = False


def _rule_dict(rule: dict | StorageAlertRule) -> dict:
    return StorageAlertRule.model_validate(rule).model_dump()


def canonical_rule_signature(rule: dict | StorageAlertRule) -> str:
    payload = json.dumps(_rule_dict(rule), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_storage_alert_rule(*, target_type, system_rule, project_rule=None, group_rule=None):
    if target_type in {"storage_usage", "group"} and group_rule is not None:
        return ResolvedRule(_rule_dict(group_rule), "group")
    if target_type in {"storage_usage", "group", "project"} and project_rule is not None:
        return ResolvedRule(_rule_dict(project_rule), "project")
    return ResolvedRule(_rule_dict(system_rule), "system")


def _value(state, name, default=None):
    if state is None:
        return default
    return state.get(name, default) if isinstance(state, dict) else getattr(state, name, default)


def _copy_state(state, **values):
    if isinstance(state, AlertState):
        return replace(state, **values)
    if state is None or isinstance(state, dict):
        data = dict(state or {})
        data.update(values)
        return AlertState(**{field: data.get(field) for field in AlertState.__dataclass_fields__})
    for name, value in values.items():
        setattr(state, name, value)
    return state


def _level(rule, ratio):
    for level in reversed(LEVELS):
        if ratio >= rule[level]["threshold"]:
            return level
    return None


def transition_alert_state(*, state, rule, use_ratio, observed_at, soft_limit_available=True):
    normalized = _rule_dict(rule)
    if normalized["quota_basis"] == "soft" and not soft_limit_available:
        return TransitionResult(state=state, skipped=True)
    if state is not None and _value(state, "last_observed_at") is not None:
        if observed_at <= _value(state, "last_observed_at"):
            return TransitionResult(state=state, skipped=True)

    signature = canonical_rule_signature(normalized)
    level = _level(normalized, use_ratio)
    if state is None or _value(state, "rule_signature") != signature:
        new_state = AlertState(
            rule_signature=signature,
            consecutive_breach_count=1 if level else 0,
            last_use_ratio=use_ratio,
            last_observed_at=observed_at,
        )
        return TransitionResult(state=new_state)

    current = _value(state, "current_level")
    count = _value(state, "consecutive_breach_count", 0)
    common = {"last_use_ratio": use_ratio, "last_observed_at": observed_at}
    if level is None:
        new_state = _copy_state(
            state,
            consecutive_breach_count=0,
            current_level=None,
            **common,
        )
        if current:
            return TransitionResult(
                state=new_state,
                event_type="recovery",
                previous_level=current,
            )
        return TransitionResult(state=new_state)

    if current is None:
        count += 1
        new_state = _copy_state(state, consecutive_breach_count=count, **common)
        if count < 2:
            return TransitionResult(state=new_state)
        new_state = _copy_state(new_state, current_level=level, last_notified_at=observed_at)
        return TransitionResult(state=new_state, event_type="trigger", level=level)

    current_index = LEVELS.index(current)
    level_index = LEVELS.index(level)
    if level_index > current_index:
        new_state = _copy_state(state, current_level=level, last_notified_at=observed_at, **common)
        return TransitionResult(state=new_state, event_type="escalation", level=level)
    if level_index < current_index:
        return TransitionResult(state=_copy_state(state, current_level=level, **common))

    repeat_after = timedelta(hours=normalized[level]["repeat_hours"])
    last_notified = _value(state, "last_notified_at")
    if last_notified is None or observed_at - last_notified >= repeat_after:
        new_state = _copy_state(state, last_notified_at=observed_at, **common)
        return TransitionResult(state=new_state, event_type="repeat", level=level)
    return TransitionResult(state=_copy_state(state, **common))


def resolve_recipient_usernames(
    *,
    primary_usernames,
    group_cc_usernames,
    global_cc_usernames,
    debug,
    emergency=False,
    super_admin_usernames,
):
    business = list(primary_usernames) + list(group_cc_usernames)
    if debug:
        business_names = {str(username or "").strip() for username in business}
        candidates = list(super_admin_usernames) + [
            username
            for username in global_cc_usernames
            if str(username or "").strip() not in business_names
        ]
    else:
        candidates = business + (list(super_admin_usernames) if emergency else []) + list(global_cc_usernames)
    result = []
    for username in candidates:
        cleaned = str(username or "").strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result
