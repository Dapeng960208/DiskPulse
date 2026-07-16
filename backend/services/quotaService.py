# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from models import Group, Qtree, StorageAlerts, StorageUsage, Volume
from schemas.quotaSchema import QuotaAdjustmentRequest, QuotaAdjustmentResponse
from utils.isilonClient import IsilonClient
from utils.mailTools.emailNotification import EmailNotification
from utils.netAppClient import NetAppClient
from utils.storageDeviceHttp import device_error_response
from utils.storageTarget import resolve_group_storage_target


logger = logging.getLogger("app:quota-adjustment")
GiB = 1024 ** 3


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
        },
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

    client = None
    old_hard_limit = resource.limit
    old_soft_limit = resource.soft_limit
    try:
        client = _build_client(cluster)
        if resource_type == "Group" and storage_type == "netapp" and isinstance(target, Volume):
            device_result = client.update_volume_capacity(
                volume_name=volume.name,
                hard_limit=int(round(request.hard_limit_bytes)),
            )
        else:
            device_result = client.update_quota(
                quota_type=(
                    "user"
                    if resource_type == "StorageUsage"
                    else "tree" if storage_type == "netapp" else "directory"
                ),
                volume_name=volume.name,
                qtree_name=target.name if isinstance(target, Qtree) else None,
                path=(target.name if storage_type == "isilon" else resource.linux_path),
                username=(resource.user.rd_username if resource_type == "StorageUsage" else None),
                hard_limit=int(round(request.hard_limit_bytes)),
                soft_limit=(
                    int(round(request.soft_limit_bytes))
                    if request.soft_limit_bytes is not None
                    else None
                ),
                soft_grace=request.soft_grace_seconds,
            )
    except HTTPException:
        raise
    except requests.HTTPError as error:
        native_response = device_error_response(error)
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

    result = QuotaAdjustmentResponse(
        id=resource.id,
        resource_type="group" if resource_type == "Group" else "storage_usage",
        storage_type=storage_type,
        hard_limit=hard_limit,
        soft_limit=soft_limit,
        soft_grace_seconds=device_result.get("soft_grace"),
    )
    _record_adjustment(
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
) -> QuotaAdjustmentResponse:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
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
    )


def adjust_storage_usage_quota(
    db: Session,
    *,
    storage_usage_id: int,
    request: QuotaAdjustmentRequest,
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
    resolved = resolve_group_storage_target(storage_usage.group)
    return _execute_adjustment(
        db,
        resource=storage_usage,
        resource_type="StorageUsage",
        target=resolved["target"],
        volume=resolved["volume"],
        request=request,
    )
