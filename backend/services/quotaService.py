# -*- coding: utf-8 -*-
import logging
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

import redis
import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from appConfig import base_config
from models import AuditEvent, Group, Qtree, StorageAlerts, StorageUsage, Volume
from schemas.quotaSchema import QuotaAdjustmentRequest, QuotaAdjustmentResponse
from services.audit_service import AuditContext, append_audit_event, serialize_audit_event
from services.storageAlertRuleService import resolve_recipient_usernames
from utils.auth_service import is_super_admin
from utils.isilonClient import IsilonClient
from utils.mailTools.emailNotification import EmailNotification
from utils.netAppClient import NetAppClient
from utils.storageDeviceHttp import device_error_response
from utils.storageTarget import resolve_group_storage_target


logger = logging.getLogger("app:quota-adjustment")
GiB = 1024 ** 3
_LOCK_TTL_SECONDS = 600
_LOCK_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


def _build_client(cluster):
    common = {
        "hostname": cluster.storage_host,
        "username": cluster.storage_user,
        "password": cluster.storage_password,
        "logger": logger,
        "protocol": cluster.protocol or "https",
        "tls_verify": cluster.tls_verify,
    }
    if common["protocol"] == "https" and common["tls_verify"] is False:
        disable_warnings(InsecureRequestWarning)
    if (cluster.storage_type or "").lower() == "netapp":
        return NetAppClient(port=cluster.storage_port or 443, **common)
    return IsilonClient(
        port=cluster.storage_port or 8080,
        session_cache_mode=cluster.isilon_session_cache_mode or "none",
        session_cache_path=cluster.isilon_session_cache_path,
        **common,
    )


def _validate_storage_request(storage_type: str, request: QuotaAdjustmentRequest) -> None:
    if storage_type == "isilon":
        if request.soft_limit is not None and request.soft_grace_seconds is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Isilon soft limit requires a grace period",
            )
    elif storage_type == "netapp":
        if request.soft_grace_seconds is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="NetApp quota does not support a per-rule grace period",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported storage type",
        )


def _ratio(used: float | None, limit: float | None) -> float | None:
    return round((used or 0) * 100 / limit, 2) if limit else None


def _display_limit(value: float | None) -> str:
    return "未设置" if value is None else f"{value:.2f} GiB"


def _quota_redis_client():
    return redis.StrictRedis(
        host=base_config.get("redis.host"),
        port=base_config.get("redis.port", 6379),
        db=base_config.get("redis.quota_db", 7),
        decode_responses=True,
    )


def _quota_rule_kwargs(*, resource, resource_type: str, target, volume, storage_type: str) -> dict:
    return {
        "quota_type": (
            "user" if resource_type == "StorageUsage" else "tree" if storage_type == "netapp" else "directory"
        ),
        "volume_name": volume.name,
        "qtree_name": target.name if isinstance(target, Qtree) else None,
        "path": target.name if storage_type == "isilon" else resource.linux_path,
        "username": resource.user.rd_username if resource_type == "StorageUsage" else None,
    }


def _quota_lock_key(*, cluster_id: int, storage_type: str, rule: dict) -> str:
    """Return a device-rule identity, never a user-controlled resource ID."""
    parts = (
        storage_type,
        str(cluster_id),
        rule["quota_type"],
        rule["volume_name"] or "",
        rule["qtree_name"] or "",
        rule["path"] or "",
        rule["username"] or "",
    )
    return "diskpulse:quota-lock:" + "|".join(parts)


@contextmanager
def _quota_target_lock(*, cluster_id: int, storage_type: str, rule: dict):
    key = _quota_lock_key(cluster_id=cluster_id, storage_type=storage_type, rule=rule)
    token = str(uuid4())
    try:
        client = _quota_redis_client()
        acquired = bool(client.set(key, token, nx=True, ex=_LOCK_TTL_SECONDS))
    except redis.RedisError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "quota_lock_unavailable"},
        ) from error
    try:
        yield acquired
    finally:
        if acquired:
            try:
                client.eval(_LOCK_RELEASE_SCRIPT, 1, key, token)
            except redis.RedisError:
                logger.warning("Quota lock release failed key=%s", key)


def _quota_http_error(status_code: int, code: str, **detail) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, **detail})


def _require_safe_limit(*, resource, request: QuotaAdjustmentRequest, current_user) -> None:
    if resource.used is None or request.hard_limit_gib >= resource.used:
        return
    if not request.force_below_usage:
        raise _quota_http_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "quota_below_usage_requires_force")
    if not is_super_admin(current_user):
        raise _quota_http_error(status.HTTP_403_FORBIDDEN, "quota_below_usage_requires_super_admin")
    if not request.change_reason:
        raise _quota_http_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "quota_below_usage_requires_force")


def _sync_local_quota(*, resource, resource_type: str, target, device_result: dict) -> tuple[float, float | None]:
    hard_limit = device_result["hard_limit"] / GiB
    soft_limit = (
        device_result.get("soft_limit") / GiB
        if device_result.get("soft_limit") not in (None, -1)
        else None
    )
    now = datetime.now()
    resource.limit = hard_limit
    resource.soft_limit = soft_limit
    resource.use_ratio = _ratio(resource.used, hard_limit)
    resource.soft_use_ratio = _ratio(resource.used, soft_limit)
    resource.updated_at = now
    if resource_type == "Group":
        target.limit = hard_limit
        target.soft_limit = soft_limit
        target.use_ratio = _ratio(target.used, hard_limit)
        target.soft_use_ratio = _ratio(target.used, soft_limit)
        target.updated_at = now
    return hard_limit, soft_limit


def _result_from_device(*, resource, resource_type: str, storage_type: str, device_result: dict, operation_id: str, verification_source: str) -> QuotaAdjustmentResponse:
    return QuotaAdjustmentResponse(
        id=resource.id,
        resource_type="group" if resource_type == "Group" else "storage_usage",
        storage_type=storage_type,
        hard_limit=device_result["hard_limit"] / GiB,
        soft_limit=(
            device_result.get("soft_limit") / GiB
            if device_result.get("soft_limit") not in (None, -1)
            else None
        ),
        soft_grace_seconds=device_result.get("soft_grace"),
        operation_id=operation_id,
        verification_source=verification_source,
    )


def _read_quota_result(*, client, resource, resource_type: str, target, volume, storage_type: str, rule: dict) -> dict:
    if resource_type == "Group" and storage_type == "netapp" and isinstance(target, Volume):
        return client.read_volume_capacity(volume_name=volume.name)
    return client.read_quota(**rule)


def _enqueue_adjustment_feishu(event_id: int, *, audit_context: AuditContext | None = None) -> None:
    from celery_tasks.tasks.storage_alerts import deliver_storage_alert_task

    if audit_context is None:
        deliver_storage_alert_task.delay(event_id)
        return
    deliver_storage_alert_task.delay(
        event_id,
        audit_context_payload={
            "request_id": audit_context.request_id,
            "trace_id": audit_context.trace_id,
            "operation_id": audit_context.operation_id,
            "actor_type": audit_context.actor_type,
            "actor_user_id": audit_context.actor_user_id,
        },
    )


def _record_adjustment(
    db: Session,
    *,
    resource,
    resource_type: str,
    storage_type: str,
    old_hard_limit: float | None,
    old_soft_limit: float | None,
    hard_limit: float,
    soft_limit: float | None,
    soft_grace_seconds: int | None,
) -> StorageAlerts:
    feishu = base_config.get("feishu_notification", {}) or {}
    primary_username = (
        resource.user.rd_username
        if isinstance(resource, StorageUsage) and resource.user
        else resource.in_charge_user.rd_username
        if isinstance(resource, Group) and resource.in_charge_user
        else None
    )
    recipients = resolve_recipient_usernames(
        primary_usernames=[primary_username],
        group_cc_usernames=[],
        global_cc_usernames=feishu.get("cc_usernames", []),
        debug=bool(feishu.get("debug")),
        super_admin_usernames=base_config.get("super_admin_usernames", []),
    )
    resource_label = "用户目录" if isinstance(resource, StorageUsage) else "项目组"
    resource_name = (
        resource.linux_path if isinstance(resource, StorageUsage) else resource.name
    )
    alert = StorageAlerts(
        storage_cluster_id=resource.storage_cluster_id,
        source="diskpulse",
        fingerprint=f"diskpulse:quota-adjustment:{resource_type}:{resource.id}",
        severity="info",
        alert_level="low",
        alert_type="quota_adjustment",
        description=(
            f"{getattr(resource, 'linux_path', None) or getattr(resource, 'name', resource.id)}"
            f" 配额从 {old_hard_limit} GiB 调整为 {hard_limit} GiB"
        ),
        threshold=int(old_hard_limit or 0),
        avg_use_ratio=hard_limit,
        related_id=resource.id,
        related_type=resource_type,
        related_info={
            "old_hard_limit": old_hard_limit,
            "old_soft_limit": old_soft_limit,
            "new_hard_limit": hard_limit,
            "new_soft_limit": soft_limit,
            "soft_grace_seconds": soft_grace_seconds,
            "storage_type": storage_type,
            "title": "存储配额调整",
            "paragraphs": [
                [
                    {"tag": "text", "text": f"{resource_label}：{resource_name}\n"},
                    {
                        "tag": "text",
                        "text": f"硬限额：{_display_limit(old_hard_limit)} → {_display_limit(hard_limit)}\n",
                    },
                    {
                        "tag": "text",
                        "text": f"软限额：{_display_limit(old_soft_limit)} → {_display_limit(soft_limit)}",
                    },
                ]
            ],
        },
        delivery_status="pending" if recipients else "skipped",
        recipient_usernames=recipients,
        delivery_attempts=0,
        next_attempt_at=datetime.now() if recipients else None,
        updated_at=datetime.now(),
    )
    db.add(alert)
    return alert


def _send_adjustment_email(db: Session, resource, result: QuotaAdjustmentResponse) -> None:
    recipient = []
    if isinstance(resource, StorageUsage) and resource.user and resource.user.email:
        recipient.append(resource.user.email)
    if isinstance(resource, Group) and resource.in_charge_user and resource.in_charge_user.email:
        recipient.append(resource.in_charge_user.email)
    EmailNotification(db=db, type="storage_usage").send_email_via_template(
        subject=f"【配额调整】【{getattr(resource, 'linux_path', resource.id)}】结果反馈",
        recipient=recipient,
        data={
            "resource": getattr(resource, "linux_path", None) or getattr(resource, "name", resource.id),
            "hard_limit": result.hard_limit,
            "soft_limit": result.soft_limit,
            "storage_type": result.storage_type,
            "soft_grace_seconds": result.soft_grace_seconds,
        },
        template_name="quotaAdjustmentFeedback",
    )


def _execute_adjustment(
    db: Session,
    *,
    resource,
    resource_type: str,
    target,
    volume,
    request: QuotaAdjustmentRequest,
    current_user=None,
    audit_context: AuditContext | None = None,
) -> QuotaAdjustmentResponse:
    cluster = resource.storage_cluster if isinstance(resource, Group) else resource.group.storage_cluster
    storage_type = (cluster.storage_type or "").lower()
    _validate_storage_request(storage_type, request)
    if target is None or volume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage target not found",
        )
    if (
        resource_type == "Group"
        and storage_type == "netapp"
        and isinstance(target, Volume)
        and request.soft_limit is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="NetApp volume targets support only a hard limit",
        )

    old_hard_limit = resource.limit
    old_soft_limit = resource.soft_limit
    project_id = resource.project_id if isinstance(resource, Group) else resource.group.project_id
    resource_id = resource.id
    audit_resource_type = "group" if resource_type == "Group" else "storage_usage"
    operation_id = audit_context.operation_id if audit_context is not None else str(uuid4())
    _require_safe_limit(resource=resource, request=request, current_user=current_user)
    rule = _quota_rule_kwargs(
        resource=resource,
        resource_type=resource_type,
        target=target,
        volume=volume,
        storage_type=storage_type,
    )

    with _quota_target_lock(cluster_id=cluster.id, storage_type=storage_type, rule=rule) as acquired:
        if not acquired:
            raise _quota_http_error(status.HTTP_409_CONFLICT, "quota_adjustment_in_progress")
        return _execute_adjustment_locked(
            db,
            resource=resource,
            resource_type=resource_type,
            target=target,
            volume=volume,
            request=request,
            current_user=current_user,
            audit_context=audit_context,
            storage_type=storage_type,
            old_hard_limit=old_hard_limit,
            old_soft_limit=old_soft_limit,
            project_id=project_id,
            resource_id=resource_id,
            audit_resource_type=audit_resource_type,
            operation_id=operation_id,
            rule=rule,
        )


def _execute_adjustment_locked(
    db: Session,
    *,
    resource,
    resource_type: str,
    target,
    volume,
    request: QuotaAdjustmentRequest,
    current_user,
    audit_context: AuditContext | None,
    storage_type: str,
    old_hard_limit: float | None,
    old_soft_limit: float | None,
    project_id: int,
    resource_id: int,
    audit_resource_type: str,
    operation_id: str,
    rule: dict,
) -> QuotaAdjustmentResponse:
    cluster = resource.storage_cluster if isinstance(resource, Group) else resource.group.storage_cluster
    if audit_context is not None:
        append_audit_event(
            db,
            context=audit_context,
            phase="attempt",
            action="quota.adjust",
            resource_type=audit_resource_type,
            resource_id=resource_id,
            project_id=project_id,
            outcome="success",
            before_summary={"hard_limit": old_hard_limit, "soft_limit": old_soft_limit},
            metadata={
                "storage_type": storage_type,
                "force_below_usage": request.force_below_usage,
                "change_reason": request.change_reason,
            },
        )
        # Keep a durable pre-device record even if the target is unavailable.
        db.commit()
    client = None
    verification_source = "post_write_readback"
    try:
        client = _build_client(cluster)
        if resource_type == "Group" and storage_type == "netapp" and isinstance(target, Volume):
            device_result = client.update_volume_capacity(
                volume_name=volume.name,
                hard_limit=int(round(request.hard_limit_bytes)),
            )
        else:
            device_result = client.update_quota(
                **rule,
                hard_limit=int(round(request.hard_limit_bytes)),
                soft_limit=(
                    int(round(request.soft_limit_bytes))
                    if request.soft_limit_bytes is not None
                    else None
                ),
                soft_grace=request.soft_grace_seconds,
            )
    except HTTPException:
        if audit_context is not None:
            append_audit_event(
                db,
                context=audit_context,
                phase="result",
                action="quota.adjust",
                resource_type=audit_resource_type,
                resource_id=resource_id,
                project_id=project_id,
                outcome="failure",
                reason_code="quota_adjustment_rejected",
            )
            db.commit()
        raise
    except (requests.Timeout, requests.ConnectionError) as error:
        try:
            device_result = _read_quota_result(
                client=client, resource=resource, resource_type=resource_type, target=target,
                volume=volume, storage_type=storage_type, rule=rule,
            )
        except Exception as readback_error:
            logger.warning(
                "Quota write outcome unknown cluster_id=%s resource_type=%s resource_id=%s write_error=%s readback_error=%s",
                cluster.id, resource_type, resource.id, type(error).__name__, type(readback_error).__name__,
            )
            if audit_context is not None:
                append_audit_event(
                    db, context=audit_context, phase="result", action="quota.adjust",
                    resource_type=audit_resource_type, resource_id=resource_id, project_id=project_id,
                    outcome="failure", reason_code="quota_outcome_unknown",
                )
                db.commit()
            raise _quota_http_error(
                status.HTTP_502_BAD_GATEWAY,
                "quota_outcome_unknown",
                operation_id=operation_id,
            ) from readback_error
        expected_hard = int(round(request.hard_limit_bytes))
        expected_soft = int(round(request.soft_limit_bytes)) if request.soft_limit_bytes is not None else None
        if device_result.get("hard_limit") != expected_hard or device_result.get("soft_limit") != expected_soft:
            if audit_context is not None:
                append_audit_event(
                    db, context=audit_context, phase="result", action="quota.adjust",
                    resource_type=audit_resource_type, resource_id=resource_id, project_id=project_id,
                    outcome="failure", reason_code="quota_outcome_unknown",
                )
                db.commit()
            raise _quota_http_error(
                status.HTTP_502_BAD_GATEWAY,
                "quota_outcome_unknown",
                operation_id=operation_id,
            )
        verification_source = "post_timeout_readback"
    except requests.HTTPError as error:
        native_response = device_error_response(error)
        if audit_context is not None:
            append_audit_event(
                db,
                context=audit_context,
                phase="result",
                action="quota.adjust",
                resource_type=audit_resource_type,
                resource_id=resource_id,
                project_id=project_id,
                outcome="failure",
                reason_code="quota_device_rejected",
            )
            db.commit()
        if native_response is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Storage quota adjustment failed",
            ) from error
        logger.error(
            "Quota device request rejected cluster_id=%s resource_type=%s resource_id=%s device_status=%s",
            cluster.id,
            resource_type,
            resource.id,
            native_response.status_code,
        )
        return native_response
    except Exception as error:
        if audit_context is not None:
            append_audit_event(
                db,
                context=audit_context,
                phase="result",
                action="quota.adjust",
                resource_type=audit_resource_type,
                resource_id=resource_id,
                project_id=project_id,
                outcome="failure",
                reason_code="quota_device_unavailable",
            )
            db.commit()
        logger.error(
            "Quota device update failed cluster_id=%s resource_type=%s resource_id=%s error_type=%s",
            cluster.id,
            resource_type,
            resource.id,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage quota adjustment failed",
        ) from error
    finally:
        if client is not None:
            client.close()

    hard_limit, soft_limit = _sync_local_quota(
        resource=resource, resource_type=resource_type, target=target, device_result=device_result,
    )
    result = _result_from_device(
        resource=resource, resource_type=resource_type, storage_type=storage_type,
        device_result=device_result, operation_id=operation_id, verification_source=verification_source,
    )
    alert = _record_adjustment(
        db,
        resource=resource,
        resource_type=resource_type,
        storage_type=storage_type,
        old_hard_limit=old_hard_limit,
        old_soft_limit=old_soft_limit,
        hard_limit=hard_limit,
        soft_limit=soft_limit,
        soft_grace_seconds=result.soft_grace_seconds,
    )
    if audit_context is not None:
        append_audit_event(
            db,
            context=audit_context,
            phase="result",
            action="quota.adjust",
            resource_type=audit_resource_type,
            resource_id=resource_id,
            project_id=project_id,
            outcome="success",
            before_summary={"hard_limit": old_hard_limit, "soft_limit": old_soft_limit},
            after_summary={"hard_limit": hard_limit, "soft_limit": soft_limit},
            metadata={
                "storage_type": storage_type,
                "force_below_usage": request.force_below_usage,
                "change_reason": request.change_reason,
                "verification_source": verification_source,
            },
        )
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.critical(
            "Quota device update succeeded but local sync failed cluster_id=%s resource_type=%s resource_id=%s",
            cluster.id,
            resource_type,
            resource.id,
        )
        raise

    if alert.delivery_status == "pending":
        try:
            _enqueue_adjustment_feishu(alert.id, audit_context=audit_context)
        except Exception as error:
            logger.error(
                "Quota adjustment Feishu enqueue failed resource_type=%s resource_id=%s error_type=%s",
                resource_type,
                resource.id,
                type(error).__name__,
            )

    try:
        _send_adjustment_email(db, resource, result)
    except Exception as error:
        logger.error(
            "Quota adjustment email failed resource_type=%s resource_id=%s error_type=%s",
            resource_type,
            resource.id,
            type(error).__name__,
        )
    return result


def adjust_group_quota(
    db: Session,
    *,
    group_id: int,
    request: QuotaAdjustmentRequest,
    current_user=None,
    audit_context: AuditContext | None = None,
) -> QuotaAdjustmentResponse:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    require_group_quota_adjustment_permission(
        db=db,
        group_id=group_id,
        current_user=current_user,
    )
    resolved = resolve_group_storage_target(group)
    target = resolved["target"]
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage target not found")
    target_column = Group.qtree_id if isinstance(target, Qtree) else Group.volume_id
    if db.query(Group).filter(target_column == target.id).count() > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Storage target is shared by multiple groups",
        )
    return _execute_adjustment(
        db,
        resource=group,
        resource_type="Group",
        target=target,
        volume=resolved["volume"],
        request=request,
        current_user=current_user,
        audit_context=audit_context,
    )


def adjust_storage_usage_quota(
    db: Session,
    *,
    storage_usage_id: int,
    request: QuotaAdjustmentRequest,
    current_user=None,
    audit_context: AuditContext | None = None,
) -> QuotaAdjustmentResponse:
    storage_usage = db.get(StorageUsage, storage_usage_id)
    if storage_usage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage usage not found",
        )
    if storage_usage.group is None or storage_usage.user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage usage relations not found",
        )
    require_group_quota_adjustment_permission(
        db=db,
        group_id=storage_usage.group_id,
        current_user=current_user,
    )
    resolved = resolve_group_storage_target(storage_usage.group)
    return _execute_adjustment(
        db,
        resource=storage_usage,
        resource_type="StorageUsage",
        target=resolved["target"],
        volume=resolved["volume"],
        request=request,
        current_user=current_user,
        audit_context=audit_context,
    )


def _reconcile_quota(
    db: Session,
    *,
    resource,
    resource_type: str,
    target,
    volume,
    current_user,
    audit_context: AuditContext | None = None,
) -> QuotaAdjustmentResponse:
    cluster = resource.storage_cluster if isinstance(resource, Group) else resource.group.storage_cluster
    storage_type = (cluster.storage_type or "").lower()
    rule = _quota_rule_kwargs(
        resource=resource,
        resource_type=resource_type,
        target=target,
        volume=volume,
        storage_type=storage_type,
    )
    operation_id = audit_context.operation_id if audit_context is not None else str(uuid4())
    audit_resource_type = "group" if resource_type == "Group" else "storage_usage"
    project_id = resource.project_id if isinstance(resource, Group) else resource.group.project_id
    with _quota_target_lock(cluster_id=cluster.id, storage_type=storage_type, rule=rule) as acquired:
        if not acquired:
            raise _quota_http_error(status.HTTP_409_CONFLICT, "quota_adjustment_in_progress")
        client = None
        try:
            client = _build_client(cluster)
            device_result = _read_quota_result(
                client=client, resource=resource, resource_type=resource_type, target=target,
                volume=volume, storage_type=storage_type, rule=rule,
            )
        except Exception as error:
            if audit_context is not None:
                append_audit_event(
                    db, context=audit_context, phase="result", action="quota.reconcile",
                    resource_type=audit_resource_type, resource_id=resource.id, project_id=project_id,
                    outcome="failure", reason_code="quota_device_unavailable",
                )
                db.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Storage quota reconciliation failed") from error
        finally:
            if client is not None:
                client.close()

        old_hard_limit, old_soft_limit = resource.limit, resource.soft_limit
        hard_limit, soft_limit = _sync_local_quota(
            resource=resource, resource_type=resource_type, target=target, device_result=device_result,
        )
        result = _result_from_device(
            resource=resource, resource_type=resource_type, storage_type=storage_type,
            device_result=device_result, operation_id=operation_id,
            verification_source="manual_reconciliation",
        )
        if audit_context is not None:
            append_audit_event(
                db, context=audit_context, phase="result", action="quota.reconcile",
                resource_type=audit_resource_type, resource_id=resource.id, project_id=project_id,
                outcome="success", before_summary={"hard_limit": old_hard_limit, "soft_limit": old_soft_limit},
                after_summary={"hard_limit": hard_limit, "soft_limit": soft_limit},
                metadata={"storage_type": storage_type, "verification_source": "manual_reconciliation"},
            )
        db.commit()
        return result


def reconcile_group_quota(
    db: Session, *, group_id: int, current_user=None, audit_context: AuditContext | None = None,
) -> QuotaAdjustmentResponse:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    require_group_quota_adjustment_permission(db=db, group_id=group_id, current_user=current_user)
    resolved = resolve_group_storage_target(group)
    if resolved["target"] is None or resolved["volume"] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage target not found")
    return _reconcile_quota(
        db, resource=group, resource_type="Group", target=resolved["target"], volume=resolved["volume"],
        current_user=current_user, audit_context=audit_context,
    )


def reconcile_storage_usage_quota(
    db: Session, *, storage_usage_id: int, current_user=None, audit_context: AuditContext | None = None,
) -> QuotaAdjustmentResponse:
    storage_usage = db.get(StorageUsage, storage_usage_id)
    if storage_usage is None or storage_usage.group is None or storage_usage.user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage usage not found")
    require_group_quota_adjustment_permission(
        db=db, group_id=storage_usage.group_id, current_user=current_user,
    )
    resolved = resolve_group_storage_target(storage_usage.group)
    if resolved["target"] is None or resolved["volume"] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage target not found")
    return _reconcile_quota(
        db, resource=storage_usage, resource_type="StorageUsage", target=resolved["target"], volume=resolved["volume"],
        current_user=current_user, audit_context=audit_context,
    )


def quota_history(
    db: Session,
    *,
    resource_type: str,
    resource_id: int,
    group_id: int,
    current_user,
) -> list[dict]:
    require_group_quota_adjustment_permission(db=db, group_id=group_id, current_user=current_user)
    rows = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.resource_type == resource_type,
            AuditEvent.resource_id == resource_id,
            AuditEvent.phase == "result",
            AuditEvent.action.in_(("quota.adjust", "quota.reconcile")),
        )
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .limit(10)
        .all()
    )
    return [serialize_audit_event(row) for row in rows]


def group_quota_history(db: Session, *, group_id: int, current_user) -> list[dict]:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return quota_history(
        db, resource_type="group", resource_id=group.id, group_id=group.id, current_user=current_user,
    )


def storage_usage_quota_history(db: Session, *, storage_usage_id: int, current_user) -> list[dict]:
    storage_usage = db.get(StorageUsage, storage_usage_id)
    if storage_usage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage usage not found")
    return quota_history(
        db, resource_type="storage_usage", resource_id=storage_usage.id,
        group_id=storage_usage.group_id, current_user=current_user,
    )


def require_group_quota_adjustment_permission(*, db: Session, group_id: int, current_user) -> Group:
    """Only the responsible group owner may use the non-admin quota exception."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    if is_super_admin(current_user):
        return None
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if group.in_charge_user_id == current_user.id:
        return group
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="quota adjustment permission required")
