# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from uuid import uuid4

from celery.utils.log import get_task_logger
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from appConfig import base_config
from celery_worker import diskpulse_app
from database import SessionLocal
from models import (
    Group,
    Project,
    StorageAlerts,
    StorageAlertState,
    StorageConf,
    StorageCluster,
    StorageUsage,
    User,
)
from schemas.storageAlertRuleSchema import DEFAULT_STORAGE_ALERT_RULE
from services.audit_service import AuditContext, append_audit_event
from services.feishuNotificationService import FeishuNotificationService
from services.storageAlertRuleService import (
    canonical_rule_signature,
    resolve_recipient_usernames,
    resolve_storage_alert_rule,
    transition_alert_state,
)


logger = get_task_logger(__name__)
RETRY_DELAYS_SECONDS = (60, 300, 900)
MAX_DELIVERY_ATTEMPTS = 4
DELIVERY_ATTEMPT_LEASE_SECONDS = 60
TARGET_TYPE_LABELS = {"storage_usage": "用户目录", "group": "项目组", "project": "项目"}
EVENT_TYPE_LABELS = {
    "trigger": "首次告警",
    "escalation": "告警升级",
    "repeat": "重复告警",
    "recovery": "恢复通知",
}
QUOTA_BASIS_LABELS = {"hard": "硬限额", "soft": "软限额"}
ALERT_LEVEL_LABELS = {"important": "重要", "serious": "严重", "emergency": "紧急"}


def _usernames_for_ids(db, user_ids):
    if not user_ids:
        return []
    rows = db.query(User.id, User.rd_username).filter(User.id.in_(user_ids)).all()
    by_id = {row.id: row.rd_username for row in rows}
    return [by_id.get(user_id) for user_id in user_ids]


def _effective_rule(system_rule, target_type, project, group=None):
    return resolve_storage_alert_rule(
        target_type=target_type,
        system_rule=system_rule,
        project_rule=project.storage_alert_rule if project else None,
        group_rule=group.storage_alert_rule if group else None,
    ).rule


def _display(value, suffix=""):
    return "未设置" if value is None else f"{value:.2f}{suffix}"


def _paragraphs(target, rule, ratio, event_type, context, previous_level=None):
    labels = {
        "username": "用户名",
        "cluster": "集群",
        "clusters": "集群",
        "project": "项目",
        "group_tag": "项目组标签",
        "group": "项目组",
        "linux_path": "Linux路径",
    }
    lines = [f"{labels[key]}：{', '.join(value) if isinstance(value, list) else value}\n" for key, value in context.items() if value]
    lines.extend(
        [
            f"事件：{EVENT_TYPE_LABELS.get(event_type, event_type)}\n",
            f"采用口径：{QUOTA_BASIS_LABELS.get(rule['quota_basis'], rule['quota_basis'])}，使用率：{ratio:.2f}%\n",
            f"硬限额：{_display(target.limit, ' GB')}，已使用：{_display(target.used, ' GB')}，硬限额使用率：{_display(target.use_ratio, '%')}\n",
            f"软限额：{_display(target.soft_limit, ' GB')}，已使用：{_display(target.used, ' GB')}，软限额使用率：{_display(target.soft_use_ratio, '%')}\n",
        ]
    )
    if previous_level:
        lines.append(f"恢复前等级：{ALERT_LEVEL_LABELS.get(previous_level, previous_level)}")
    return [[{"tag": "text", "text": line} for line in lines]]


def _evaluate_one(
    db,
    *,
    target_type,
    target,
    project,
    group,
    system_rule,
    primary_usernames,
    observed_at,
    context,
):
    rule = _effective_rule(system_rule, target_type, project, group)
    basis = rule["quota_basis"]
    ratio = target.use_ratio if basis == "hard" else target.soft_use_ratio
    soft_available = target.soft_limit is not None and target.soft_limit > 0 and ratio is not None
    if ratio is None:
        return None
    state = (
        db.query(StorageAlertState)
        .filter_by(target_type=target_type, target_id=target.id)
        .with_for_update()
        .first()
    )
    result = transition_alert_state(
        state=state,
        rule=rule,
        use_ratio=ratio,
        observed_at=observed_at,
        soft_limit_available=soft_available,
    )
    if result.skipped:
        return None
    if state is None:
        candidate = StorageAlertState(
            target_type=target_type,
            target_id=target.id,
            rule_signature=result.state.rule_signature,
        )
        try:
            with db.begin_nested():
                db.add(candidate)
                db.flush()
            state = candidate
        except IntegrityError:
            state = (
                db.query(StorageAlertState)
                .filter_by(target_type=target_type, target_id=target.id)
                .with_for_update()
                .one()
            )
            result = transition_alert_state(
                state=state,
                rule=rule,
                use_ratio=ratio,
                observed_at=observed_at,
                soft_limit_available=soft_available,
            )
            if result.skipped:
                return None
    for field in (
        "rule_signature",
        "consecutive_breach_count",
        "current_level",
        "last_use_ratio",
        "last_observed_at",
        "last_notified_at",
    ):
        setattr(state, field, getattr(result.state, field))
    if not result.event_type:
        return None

    feishu = base_config.get("feishu_notification", {}) or {}
    group_cc = _usernames_for_ids(db, group.alert_cc_user_ids or []) if group else []
    emergency = (result.level or result.previous_level) == "emergency"
    recipients = resolve_recipient_usernames(
        primary_usernames=primary_usernames,
        group_cc_usernames=group_cc if target_type in {"storage_usage", "group"} else [],
        global_cc_usernames=feishu.get("cc_usernames", []),
        debug=bool(feishu.get("debug")),
        emergency=emergency,
        super_admin_usernames=base_config.get("super_admin_usernames", []),
    )
    if target_type == "storage_usage":
        target_name = f"Linux目录 {context.get('linux_path') or '-'}"
    else:
        name_key = {"group": "group", "project": "project"}[target_type]
        target_name = f"{TARGET_TYPE_LABELS[target_type]} {context.get(name_key) or '-'}"
    alert = StorageAlerts(
        storage_cluster_id=(None if target_type == "project" else getattr(target, "storage_cluster_id", None)),
        source="diskpulse",
        fingerprint=f"storage-rule:{target_type}:{target.id}:{observed_at.isoformat()}",
        severity=result.level or result.previous_level or "info",
        alert_level=result.level or result.previous_level,
        alert_type="alert",
        description=f"{target_name} {EVENT_TYPE_LABELS[result.event_type]}（使用率 {ratio:.2f}%）",
        threshold=rule[result.level]["threshold"] if result.level else rule["important"]["threshold"],
        avg_use_ratio=ratio,
        related_id=target.id,
        related_type={"storage_usage": "StorageUsage", "group": "Group", "project": "Project"}[target_type],
        related_info={
            "title": "存储恢复通知" if result.event_type == "recovery" else "存储容量告警",
            "context": context,
            "paragraphs": _paragraphs(
                target, rule, ratio, result.event_type, context, result.previous_level
            ),
        },
        event_type=result.event_type,
        quota_basis=basis,
        delivery_status="pending" if recipients else "skipped",
        recipient_usernames=recipients,
        delivery_attempts=0,
        next_attempt_at=observed_at if recipients else None,
        updated_at=observed_at,
    )
    db.add(alert)
    db.flush()
    return alert.id if recipients else None


def evaluate_storage_alerts(
    successful_cluster_ids,
    refreshed_project_ids,
    sample_identity=None,
    refreshed_storage_usage_ids=(),
    refreshed_group_ids=(),
    observed_at=None,
):
    observed_at = observed_at or sample_identity or datetime.now()
    if isinstance(observed_at, str):
        observed_at = datetime.fromisoformat(observed_at)
    delivery_ids = []
    with SessionLocal.begin() as db:
        config = db.query(StorageConf).first()
        system_rule = (config.storage_alert_rule if config else None) or DEFAULT_STORAGE_ALERT_RULE
        cluster_ids = set(successful_cluster_ids)
        usages = (
            db.query(StorageUsage)
            .options(
                joinedload(StorageUsage.user),
                joinedload(StorageUsage.storage_cluster),
                joinedload(StorageUsage.group).joinedload(Group.project),
                joinedload(StorageUsage.group).joinedload(Group.group_tag),
            )
            .filter(
                StorageUsage.storage_cluster_id.in_(cluster_ids),
                StorageUsage.id.in_(set(refreshed_storage_usage_ids)),
                StorageUsage.updated_at == observed_at,
            )
            .all()
        )
        for usage in usages:
            if not usage.group or not usage.group.enable_monitoring or not usage.user or not usage.user.is_alert:
                continue
            event_id = _evaluate_one(
                db,
                target_type="storage_usage",
                target=usage,
                project=usage.group.project,
                group=usage.group,
                system_rule=system_rule,
                primary_usernames=[usage.user.rd_username],
                observed_at=observed_at,
                context={
                    "username": usage.user.rd_username,
                    "cluster": usage.storage_cluster.name if usage.storage_cluster else None,
                    "project": usage.group.project.name if usage.group.project else None,
                    "group_tag": usage.group.group_tag.name if usage.group.group_tag else None,
                    "group": usage.group.name,
                    "linux_path": usage.linux_path,
                },
            )
            if event_id:
                delivery_ids.append(event_id)

        groups = (
            db.query(Group)
            .options(joinedload(Group.project), joinedload(Group.in_charge_user))
            .options(joinedload(Group.storage_cluster), joinedload(Group.group_tag))
            .filter(
                Group.storage_cluster_id.in_(cluster_ids),
                Group.enable_monitoring.is_(True),
                Group.id.in_(set(refreshed_group_ids)),
                Group.updated_at == observed_at,
            )
            .all()
        )
        for group in groups:
            event_id = _evaluate_one(
                db,
                target_type="group",
                target=group,
                project=group.project,
                group=group,
                system_rule=system_rule,
                primary_usernames=[group.in_charge_user.rd_username if group.in_charge_user else None],
                observed_at=observed_at,
                context={
                    "cluster": group.storage_cluster.name if group.storage_cluster else None,
                    "group_tag": group.group_tag.name if group.group_tag else None,
                    "project": group.project.name if group.project else None,
                    "group": group.name,
                    "linux_path": group.linux_path,
                },
            )
            if event_id:
                delivery_ids.append(event_id)

        projects = (
            db.query(Project)
            .options(joinedload(Project.in_charge_user))
            .filter(
                Project.id.in_(set(refreshed_project_ids)),
                Project.status == 1,
                Project.is_alert.is_(True),
            )
            .all()
        )
        for project in projects:
            cluster_names = [
                row[0]
                for row in db.query(StorageCluster.name)
                .join(Group, Group.storage_cluster_id == StorageCluster.id)
                .filter(Group.project_id == project.id, Group.enable_monitoring.is_(True))
                .distinct()
                .order_by(StorageCluster.name)
                .all()
            ]
            event_id = _evaluate_one(
                db,
                target_type="project",
                target=project,
                project=project,
                group=None,
                system_rule=system_rule,
                primary_usernames=[project.in_charge_user.rd_username if project.in_charge_user else None],
                observed_at=observed_at,
                context={"project": project.name, "clusters": cluster_names},
            )
            if event_id:
                delivery_ids.append(event_id)
    return delivery_ids


def _latest_alert_sample():
    with SessionLocal() as db:
        observed_at = max(
            filter(
                None,
                (
                    db.query(func.max(StorageUsage.updated_at)).scalar(),
                    db.query(func.max(Group.updated_at)).scalar(),
                ),
            ),
            default=None,
        )
        if observed_at is None:
            return None
        usages = (
            db.query(StorageUsage.id, StorageUsage.storage_cluster_id)
            .filter(StorageUsage.updated_at == observed_at)
            .order_by(StorageUsage.id)
            .all()
        )
        groups = (
            db.query(Group.id, Group.storage_cluster_id)
            .filter(Group.updated_at == observed_at)
            .order_by(Group.id)
            .all()
        )
        project_ids = tuple(
            row.id
            for row in db.query(Project.id)
            .filter(Project.updated_at == observed_at)
            .order_by(Project.id)
            .all()
        )
    return {
        "successful_cluster_ids": tuple(
            sorted(
                {
                    row.storage_cluster_id
                    for row in (*usages, *groups)
                    if row.storage_cluster_id is not None
                }
            )
        ),
        "refreshed_project_ids": project_ids,
        "sample_identity": observed_at.isoformat(),
        "refreshed_storage_usage_ids": tuple(row.id for row in usages),
        "refreshed_group_ids": tuple(row.id for row in groups),
    }


@diskpulse_app.task(soft_time_limit=120, time_limit=150)
def storage_alerts_schedule_task():
    from celery_tasks.tasks.redis_lock import redis_lock

    with redis_lock("storage_alert_evaluation_lock", expires=140) as have_lock:
        if not have_lock:
            return []
        sample = _latest_alert_sample()
        if sample is None:
            return []
        event_ids = evaluate_storage_alerts(**sample)
    for event_id in event_ids:
        deliver_storage_alert_task.delay(event_id)
    if event_ids:
        try:
            from celery_tasks.tasks import forecast_incidents

            # Derived Incident evidence references this immutable raw alert only.
            forecast_incidents.diskpulse_alert_evidence_task.delay(event_ids)
        except Exception:
            logger.warning("Unable to enqueue derived Incident evidence for storage alerts")
    return event_ids


def _delivery_audit_context(audit_context_payload=None) -> AuditContext:
    if audit_context_payload is not None:
        return AuditContext(
            request_id=audit_context_payload["request_id"],
            trace_id=audit_context_payload["trace_id"],
            operation_id=audit_context_payload["operation_id"],
            actor_type=audit_context_payload.get("actor_type", "service"),
            actor_user_id=audit_context_payload.get("actor_user_id"),
        )
    return AuditContext(
        request_id=uuid4(),
        trace_id=uuid4(),
        operation_id=uuid4(),
        actor_type="service",
    )


def _prepare_delivery_attempt(event_id, *, context: AuditContext, config):
    with SessionLocal.begin() as db:
        event = db.query(StorageAlerts).filter_by(id=event_id).with_for_update().first()
        if event is None or event.delivery_status not in {"pending", "retrying", "delivering"}:
            return None
        now = datetime.now()
        if event.next_attempt_at is None or event.next_attempt_at > now:
            return None
        # Enforce lease: skip if another worker holds the delivery attempt
        now = datetime.now()
        if event.next_attempt_at is not None and event.next_attempt_at > now:
            return None
        if not event.recipient_usernames:
            event.delivery_status = "skipped"
            return None
        if not config.get("enabled"):
            event.delivery_status = "skipped"
            return None
        # Review fix: an active delivery lease prevents duplicate task deliveries.
        event.delivery_status = "delivering"
        event.delivery_attempts += 1
        event.next_attempt_at = now + timedelta(seconds=DELIVERY_ATTEMPT_LEASE_SECONDS)
        append_audit_event(
            db,
            context=context,
            phase="attempt",
            action="notification.storage_alert.deliver",
            resource_type="storage_alert",
            resource_id=event.id,
            outcome="success",
            metadata={"delivery_attempt": event.delivery_attempts},
        )
        info = event.related_info or {}
        return {
            "attempt": event.delivery_attempts,
            "usernames": list(event.recipient_usernames),
            "title": info.get("title", "存储容量告警"),
            "paragraphs": info.get("paragraphs", []),
        }


def _record_delivery_result(event_id, *, context: AuditContext, attempt: int, error=None):
    with SessionLocal.begin() as db:
        event = db.query(StorageAlerts).filter_by(id=event_id).with_for_update().first()
        if event is None or event.delivery_attempts != attempt:
            return
        if error is not None:
            event.delivery_error = str(error)[:512]
            if event.delivery_attempts >= MAX_DELIVERY_ATTEMPTS:
                event.delivery_status = "failed"
                event.next_attempt_at = None
            else:
                event.delivery_status = "retrying"
                event.next_attempt_at = datetime.now() + timedelta(
                    seconds=RETRY_DELAYS_SECONDS[event.delivery_attempts - 1]
                )
            append_audit_event(
                db,
                context=context,
                phase="result",
                action="notification.storage_alert.deliver",
                resource_type="storage_alert",
                resource_id=event.id,
                outcome="failure",
                reason_code="notification_delivery_failed",
                after_summary={
                    "delivery_status": event.delivery_status,
                    "delivery_attempt": attempt,
                },
            )
        else:
            event.delivery_status = "sent"
            event.notified_at = datetime.now()
            event.next_attempt_at = None
            event.delivery_error = None
            append_audit_event(
                db,
                context=context,
                phase="result",
                action="notification.storage_alert.deliver",
                resource_type="storage_alert",
                resource_id=event.id,
                outcome="success",
                after_summary={
                    "delivery_status": event.delivery_status,
                    "delivery_attempt": attempt,
                },
            )


@diskpulse_app.task(soft_time_limit=30, time_limit=45)
def deliver_storage_alert_task(event_id, audit_context_payload=None):
    audit_context = _delivery_audit_context(audit_context_payload)
    config = base_config.get("feishu_notification", {}) or {}
    delivery = _prepare_delivery_attempt(event_id, context=audit_context, config=config)
    if delivery is None:
        return
    try:
        FeishuNotificationService(config).send(
            usernames=delivery["usernames"],
            title=delivery["title"],
            paragraphs=delivery["paragraphs"],
        )
    except Exception as error:
        _record_delivery_result(
            event_id,
            context=audit_context,
            attempt=delivery["attempt"],
            error=error,
        )
        logger.warning("Feishu storage alert delivery failed: event=%s", event_id)
    else:
        _record_delivery_result(
            event_id,
            context=audit_context,
            attempt=delivery["attempt"],
        )


@diskpulse_app.task(soft_time_limit=50, time_limit=55)
def retry_storage_alerts_task():
    now = datetime.now()
    with SessionLocal() as db:
        event_ids = [
            row.id
            for row in db.query(StorageAlerts.id)
            .filter(
                StorageAlerts.delivery_status.in_(("pending", "retrying", "delivering")),
                StorageAlerts.next_attempt_at <= now,
            )
            .limit(100)
            .all()
        ]
    for event_id in event_ids:
        deliver_storage_alert_task.delay(event_id)
    return event_ids
