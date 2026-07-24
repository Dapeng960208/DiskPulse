# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from importlib import import_module
from utils.datetime_utils import utc_now

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import vendorEventDefinitionCrud
from models import VendorEventDefinition
from schemas.vendorEventDefinitionSchema import validate_reviewed_definition_values
from services.audit_service import AuditContext, append_audit_event


ASSOCIATION_TYPE_LABELS = {
    "fault_log": "故障日志",
    "performance_anomaly": "性能异常",
    "capacity_threshold": "容量/配额阈值",
    "system_activity": "系统运行事件",
    "telemetry_degradation": "监控能力下降",
    "unknown": "未分类厂商事件",
}

UNKNOWN_TITLE_ZH = "未收录的厂商事件代码"
UNKNOWN_DESCRIPTION_ZH = (
    "尚未在事件代码目录中确认该厂商事件的中文含义，"
    "请结合当前事件日志与厂商运行时事件目录复核。"
)

_NETAPP_WAFL_VOLUME_URL = (
    "https://docs.netapp.com/us-en/ontap-ems-9181/wafl-vol-events.html"
)
_NETAPP_WAFL_SCAN_URL = (
    "https://docs.netapp.com/us-en/ontap-ems-9181/wafl-scan-events.html"
)
_POWERSCALE_EVENT_LIST_URL = (
    "https://infohub.delltechnologies.com/en-us/l/"
    "powerscale-onefs-advanced-alert-configurations/"
    "appendix-b-full-list-of-srs-brevity/"
)
_LEGACY_COMMON_DEFINITIONS: tuple[dict[str, object], ...] = (
    {
        "storage_type": "netapp",
        "event_code": "wafl.vol.blks_used.done",
        "association_type": "system_activity",
        "title_zh": "已用块计算完成",
        "description_zh": "卷或聚合的已用块扫描计算已经结束，属于完成通知，不表示故障。",
        "official_reference_url": _NETAPP_WAFL_VOLUME_URL,
        "default_severity": "warning",
        "version_scope": "ONTAP 9.14.1、9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "wafl.vol.snap_create.done",
        "association_type": "system_activity",
        "title_zh": "快照创建扫描完成",
        "description_zh": "快照创建相关扫描已经完成，属于正常操作记录。",
        "official_reference_url": _NETAPP_WAFL_VOLUME_URL,
        "default_severity": "info",
        "version_scope": "ONTAP 9.14.1、9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "wafl.scan.ownblocks.done",
        "association_type": "system_activity",
        "title_zh": "归属块检查完成",
        "description_zh": "用于检查块归属关系的 WAFL 扫描已经结束。",
        "official_reference_url": _NETAPP_WAFL_SCAN_URL,
        "default_severity": "info",
        "version_scope": "ONTAP 9.11.1、9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "wafl.scan.done",
        "association_type": "system_activity",
        "title_zh": "WAFL 扫描完成",
        "description_zh": "某项 WAFL 扫描已经完成；具体扫描类型和对象应从事件参数读取。",
        "official_reference_url": _NETAPP_WAFL_SCAN_URL,
        "default_severity": "warning",
        "version_scope": "ONTAP 9.11.1、9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "nblade.execsOverLimit",
        "association_type": "performance_anomaly",
        "title_zh": "NFS 请求并发超过连接阈值",
        "description_zh": (
            "单个连接的并发在途请求超过允许值，系统开始限制请求，"
            "客户端性能可能下降。"
        ),
        "official_reference_url": (
            "https://docs.netapp.com/us-en/ontap-ems/"
            "nblade-execsoverlimit-events.html"
        ),
        "default_severity": None,
        "version_scope": "ONTAP 9.10.1–9.18.1；严重度采用事件实例值",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "secd.authsys.lookup.failed",
        "association_type": "fault_log",
        "title_zh": "UNIX 用户凭据查询失败",
        "description_zh": (
            "访问请求中的 UID 无法通过 NIS、LDAP 或本地文件名称服务解析。"
        ),
        "official_reference_url": (
            "https://docs.netapp.com/us-en/ontap-ems/secd-authsys-events.html"
        ),
        "default_severity": "error",
        "version_scope": "ONTAP 9.11.1–9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "sis.auto.session.change",
        "association_type": "system_activity",
        "title_zh": "后台去重会话数因负载调整",
        "description_zh": (
            "系统根据当前负载节流自动存储效率任务，并调整后台去重会话数量；"
            "不等同于去重失败。"
        ),
        "official_reference_url": (
            "https://docs.netapp.com/us-en/ontap-ems/sis-auto-events.html"
        ),
        "default_severity": "warning",
        "version_scope": "ONTAP 9.10.1–9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "fp.est.scan.catalog.updated",
        "association_type": "system_activity",
        "title_zh": "空间效率估算目录已更新",
        "description_zh": "卷空间效率估算扫描的结果已经写入目录文件，属于状态更新。",
        "official_reference_url": (
            "https://docs.netapp.com/us-en/ontap-ems-9181/fp-est-events.html"
        ),
        "default_severity": "warning",
        "version_scope": "ONTAP 9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "asup.aods.response.timeOut",
        "association_type": "fault_log",
        "title_zh": "AutoSupport OnDemand 响应超时",
        "description_zh": (
            "ONTAP 在规定时间内未收到 AutoSupport OnDemand 服务响应，"
            "应核查服务连通性。"
        ),
        "official_reference_url": (
            "https://docs.netapp.com/us-en/ontap-ems/asup-aods-events.html"
        ),
        "default_severity": "error",
        "version_scope": "ONTAP 9.11.1–9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "kern.uptime.filer",
        "association_type": "system_activity",
        "title_zh": "控制器运行状态周期记录",
        "description_zh": (
            "控制器周期性记录运行时长和协议操作计数，通常每小时产生一次，"
            "不表示故障。"
        ),
        "official_reference_url": (
            "https://docs.netapp.com/us-en/ontap-ems/kern-uptime-events.html"
        ),
        "default_severity": "warning",
        "version_scope": "ONTAP 9.10.1、9.14.1、9.16.1、9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "ccma.quota.throughput",
        "association_type": "telemetry_degradation",
        "title_zh": "性能归档保留空间不足",
        "description_zh": (
            "性能归档数据增长速度相对预留空间过高，可能缩短可保留的性能历史。"
        ),
        "official_reference_url": (
            "https://docs.netapp.com/us-en/ontap-ems/ccma-quota-events.html"
        ),
        "default_severity": "warning",
        "version_scope": "ONTAP 9.14.1、9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "netapp",
        "event_code": "nis.group.db.build.success",
        "association_type": "system_activity",
        "title_zh": "NIS 组数据库构建成功",
        "description_zh": "指定 SVM 的 NIS 组数据库已经成功构建，不是失败事件。",
        "official_reference_url": (
            "https://docs.netapp.com/us-en/ontap-ems/nis-group-events.html"
        ),
        "default_severity": "warning",
        "version_scope": "ONTAP 9.10.1–9.18.1",
        "review_status": "reviewed",
    },
    {
        "storage_type": "isilon",
        "event_code": "500010001",
        "association_type": "capacity_threshold",
        "title_zh": "SmartQuotas 配额阈值触发",
        "description_zh": (
            "某个 SmartQuotas 域达到软限制、硬限制或宽限期相关阈值；"
            "具体对象和阈值状态从事件实例参数读取。"
        ),
        "official_reference_url": _POWERSCALE_EVENT_LIST_URL,
        "default_severity": None,
        "version_scope": "OneFS 9.4.0.0（Dell H17458.1 事件列表）",
        "review_status": "reviewed",
    },
    {
        "storage_type": "isilon",
        "event_code": "500010002",
        "association_type": "fault_log",
        "title_zh": "SmartQuotas 通知发送失败",
        "description_zh": "系统未能向相关用户发送配额通知；不代表配额本身未生效。",
        "official_reference_url": _POWERSCALE_EVENT_LIST_URL,
        "default_severity": None,
        "version_scope": "OneFS 9.4.0.0（Dell H17458.1 事件列表）",
        "review_status": "reviewed",
    },
    {
        "storage_type": "isilon",
        "event_code": "400050004",
        "association_type": "system_activity",
        "title_zh": "CELOG 心跳事件",
        "description_zh": (
            "CELOG 的周期性心跳自检事件，通常仅用于确认节点能发送告警，"
            "不应当显示成故障。"
        ),
        "official_reference_url": (
            "https://infohub.delltechnologies.com/en-uk/l/"
            "powerscale-onefs-advanced-alert-configurations/"
            "general-alert-configuration-considerations/"
        ),
        "default_severity": None,
        "version_scope": "OneFS 8.0–9.4.0.0（Dell 心跳说明与 H17458.1 事件列表）",
        "review_status": "reviewed",
    },
    {
        "storage_type": "isilon",
        "event_code": "400100006",
        "association_type": "fault_log",
        "title_zh": "计划作业未按计划启动",
        "description_zh": (
            "指定 OneFS 作业未能按计划启动；应结合作业类型和当前事件日志核查。"
        ),
        "official_reference_url": _POWERSCALE_EVENT_LIST_URL,
        "default_severity": None,
        "version_scope": "OneFS 9.4.0.0（Dell H17458.1 事件列表）",
        "review_status": "reviewed",
    },
    {
        "storage_type": "isilon",
        "event_code": "SW_JOBENG_JOB_STATE",
        "association_type": "system_activity",
        "title_zh": "作业状态变化",
        "description_zh": "OneFS 作业引擎记录作业状态变化；需由目标阵列运行时目录复核。",
        "official_reference_url": None,
        "default_severity": None,
        "version_scope": "目标 OneFS 运行时事件目录",
        "review_status": "pending",
    },
    {
        "storage_type": "isilon",
        "event_code": "SW_JOBENG_JOB_PHASE_BEGIN",
        "association_type": "system_activity",
        "title_zh": "作业阶段开始",
        "description_zh": "OneFS 作业引擎记录作业阶段开始；需由目标阵列运行时目录复核。",
        "official_reference_url": None,
        "default_severity": None,
        "version_scope": "目标 OneFS 运行时事件目录",
        "review_status": "pending",
    },
    {
        "storage_type": "isilon",
        "event_code": "SW_JOBENG_JOB_PHASE_END",
        "association_type": "system_activity",
        "title_zh": "作业阶段结束",
        "description_zh": "OneFS 作业引擎记录作业阶段结束；需由目标阵列运行时目录复核。",
        "official_reference_url": None,
        "default_severity": None,
        "version_scope": "目标 OneFS 运行时事件目录",
        "review_status": "pending",
    },
    {
        "storage_type": "isilon",
        "event_code": "SW_CELOG_HEARTBEAT",
        "association_type": "system_activity",
        "title_zh": "CELOG 心跳事件",
        "description_zh": "OneFS CELOG 记录周期性心跳；需由目标阵列运行时目录复核。",
        "official_reference_url": None,
        "default_severity": None,
        "version_scope": "目标 OneFS 运行时事件目录",
        "review_status": "pending",
    },
    {
        "storage_type": "isilon",
        "event_code": "QUOTA_THRESHOLD_VIOLATION",
        "association_type": "capacity_threshold",
        "title_zh": "SmartQuotas 配额阈值触发",
        "description_zh": "OneFS 报告配额阈值事件；需由目标阵列运行时目录确认数字代码和描述。",
        "official_reference_url": None,
        "default_severity": None,
        "version_scope": "目标 OneFS 运行时事件目录",
        "review_status": "pending",
    },
    {
        "storage_type": "isilon",
        "event_code": "SW_JOBENG_JOBSCHED_NOT_STARTED",
        "association_type": "fault_log",
        "title_zh": "计划作业未按计划启动",
        "description_zh": "OneFS 报告计划作业未启动；需由目标阵列运行时目录复核。",
        "official_reference_url": None,
        "default_severity": None,
        "version_scope": "目标 OneFS 运行时事件目录",
        "review_status": "pending",
    },
    {
        "storage_type": "isilon",
        "event_code": "QUOTA_NOTIFY_FAILED",
        "association_type": "fault_log",
        "title_zh": "SmartQuotas 通知发送失败",
        "description_zh": "OneFS 报告配额通知发送失败；需由目标阵列运行时目录复核。",
        "official_reference_url": None,
        "default_severity": None,
        "version_scope": "目标 OneFS 运行时事件目录",
        "review_status": "pending",
    },
)

_REVIEWED_SOLUTION_BY_EVENT_CODE = {
    "wafl.vol.blks_used.done": "无需立即操作；保留该完成事件用于审计。",
    "wafl.vol.snap_create.done": "无需立即操作；保留该完成事件用于审计。",
    "wafl.scan.ownblocks.done": "无需立即操作；保留扫描完成记录用于审计。",
    "wafl.scan.done": "无需立即操作；如伴随失败事件，再按对应失败代码排查。",
    "nblade.execsOverLimit": "检查客户端并发请求和节点负载，并按官方事件页的处置步骤处理。",
    "secd.authsys.lookup.failed": "检查名称服务配置、网络连通性及相应认证后端。",
    "sis.auto.session.change": "无需立即操作；结合负载和存储效率作业状态持续观察。",
    "fp.est.scan.catalog.updated": "无需立即操作；保留目录更新记录用于审计。",
    "asup.aods.response.timeOut": "检查 AutoSupport OnDemand 服务连通性和配置。",
    "kern.uptime.filer": "无需立即操作；保留周期记录用于运行状态审计。",
    "ccma.quota.throughput": "检查性能归档保留空间和数据增长情况。",
    "nis.group.db.build.success": "无需立即操作；保留成功记录用于审计。",
}


def _normalize_common_definition(seed: dict[str, object]) -> dict[str, object]:
    """Keep the runtime seed from restoring unaudited PowerScale meanings."""
    if seed["storage_type"] == "isilon":
        return {
            "storage_type": "isilon",
            "event_code": seed["event_code"],
            "association_type": "unknown",
            "title_zh": UNKNOWN_TITLE_ZH,
            "description_zh": UNKNOWN_DESCRIPTION_ZH,
            "official_reference_url": None,
            "default_severity": None,
            "version_scope": None,
            "review_status": "pending",
        }

    normalized = dict(seed)
    normalized["recommended_solution_zh"] = _REVIEWED_SOLUTION_BY_EVENT_CODE[
        str(seed["event_code"])
    ]
    return normalized


COMMON_DEFINITIONS: tuple[dict[str, object], ...] = tuple(
    _normalize_common_definition(seed) for seed in _LEGACY_COMMON_DEFINITIONS
)


def association_type_label(association_type: str) -> str:
    return ASSOCIATION_TYPE_LABELS.get(
        association_type,
        ASSOCIATION_TYPE_LABELS["unknown"],
    )


def serialize_definition(definition: VendorEventDefinition) -> dict:
    return {
        "id": definition.id,
        "storage_type": definition.storage_type,
        "event_code": definition.event_code,
        "association_type": definition.association_type,
        "association_type_label": association_type_label(
            definition.association_type
        ),
        "title_zh": definition.title_zh,
        "description_zh": definition.description_zh,
        "official_reference_url": definition.official_reference_url,
        "default_severity": definition.default_severity,
        "version_scope": definition.version_scope,
        "review_status": definition.review_status,
        "recommended_solution_zh": definition.recommended_solution_zh,
        "is_active": definition.is_active,
        "created_at": definition.created_at,
        "updated_at": definition.updated_at,
    }


def resolve_definition(
    db: Session,
    storage_type: str | None,
    event_code: str | None,
) -> dict:
    normalized_storage_type = (storage_type or "").strip().lower()
    normalized_event_code = (event_code or "").strip()
    definition = None
    if normalized_storage_type and normalized_event_code:
        definition = vendorEventDefinitionCrud.get_definition(
            db,
            normalized_storage_type,
            normalized_event_code,
        )
    if (
        definition is not None
        and definition.is_active
        and definition.review_status == "reviewed"
    ):
        return serialize_definition(definition)
    return {
        "id": None,
        "storage_type": normalized_storage_type,
        "event_code": normalized_event_code,
        "association_type": "unknown",
        "association_type_label": ASSOCIATION_TYPE_LABELS["unknown"],
        "title_zh": UNKNOWN_TITLE_ZH,
        "description_zh": UNKNOWN_DESCRIPTION_ZH,
        "official_reference_url": None,
        "default_severity": None,
        "version_scope": None,
        "review_status": "pending",
        "recommended_solution_zh": None,
        "is_active": False,
        "created_at": None,
        "updated_at": None,
    }


def _placeholder_values(storage_type: str, event_code: str) -> dict:
    return {
        "storage_type": storage_type,
        "event_code": event_code,
        "association_type": "unknown",
        "title_zh": UNKNOWN_TITLE_ZH,
        "description_zh": UNKNOWN_DESCRIPTION_ZH,
        "official_reference_url": None,
        "default_severity": None,
        "version_scope": None,
        "review_status": "pending",
        "recommended_solution_zh": None,
        "is_active": True,
    }


def _is_generated_placeholder(definition: VendorEventDefinition) -> bool:
    return (
        definition.review_status == "pending"
        and definition.association_type == "unknown"
        and definition.title_zh == UNKNOWN_TITLE_ZH
    )


def seed_common_definitions(db: Session) -> int:
    inserted = 0
    existing_by_key = vendorEventDefinitionCrud.get_definition_map(
        db,
        (
            (str(seed["storage_type"]), str(seed["event_code"]))
            for seed in COMMON_DEFINITIONS
        ),
    )
    for seed in COMMON_DEFINITIONS:
        storage_type = str(seed["storage_type"])
        event_code = str(seed["event_code"])
        existing = existing_by_key.get((storage_type, event_code))
        if existing is None:
            vendorEventDefinitionCrud.create_definition(db, **_seed_values(seed))
            inserted += 1
            continue
        if _is_generated_placeholder(existing):
            vendorEventDefinitionCrud.update_definition(
                db,
                existing.id,
                **{
                    key: value
                    for key, value in _seed_values(seed).items()
                    if key not in {"storage_type", "event_code"}
                },
            )
    return inserted


def _seed_values(seed: dict[str, object]) -> dict[str, object]:
    values = dict(seed)
    if (
        values.get("review_status") == "reviewed"
        and not values.get("recommended_solution_zh")
    ):
        values["recommended_solution_zh"] = (
            "请依据厂商官方事件页及目标设备运行时事件详情完成处置。"
        )
    return values


def list_definition_page(
    db: Session,
    *,
    page: int,
    size: int,
    storage_type: str | None = None,
    association_type: str | None = None,
    keyword: str | None = None,
    review_status: str | None = None,
) -> dict:
    filters = {
        "storage_type": storage_type,
        "association_type": association_type,
        "keyword": keyword,
        "review_status": review_status,
    }
    rows = vendorEventDefinitionCrud.list_definitions(
        db,
        **filters,
        offset=(page - 1) * size,
        limit=size,
    )
    return {
        "content": [serialize_definition(row) for row in rows],
        "total": vendorEventDefinitionCrud.count_definitions(db, **filters),
    }


def get_definition_detail(db: Session, definition_id: int) -> dict:
    definition = vendorEventDefinitionCrud.get_definition_by_id(db, definition_id)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="厂商事件代码定义不存在",
        )
    return serialize_definition(definition)


def _audit_summary(definition: VendorEventDefinition) -> dict:
    return {
        "storage_type": definition.storage_type,
        "event_code": definition.event_code,
        "association_type": definition.association_type,
        "title_zh": definition.title_zh,
        "review_status": definition.review_status,
        "is_active": definition.is_active,
    }


def _append_definition_audit(
    db: Session,
    *,
    audit_context: AuditContext | None,
    action: str,
    outcome: str,
    definition_id: int | None = None,
    reason_code: str | None = None,
    before_summary: dict | None = None,
    after_summary: dict | None = None,
) -> None:
    if audit_context is None:
        return
    append_audit_event(
        db,
        context=audit_context,
        phase="result",
        action=action,
        resource_type="vendor_event_definition",
        resource_id=definition_id,
        outcome=outcome,
        reason_code=reason_code,
        before_summary=before_summary,
        after_summary=after_summary,
    )


def _record_failure(
    db: Session,
    *,
    audit_context: AuditContext | None,
    action: str,
    definition_id: int | None,
    reason_code: str,
) -> None:
    db.rollback()
    if audit_context is None:
        return
    try:
        _append_definition_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="failure",
            definition_id=definition_id,
            reason_code=reason_code,
        )
        db.commit()
    except Exception:
        db.rollback()


def create_definition(
    db: Session,
    payload,
    *,
    audit_context: AuditContext | None = None,
) -> dict:
    action = "vendor_event_definition.create"
    try:
        definition = vendorEventDefinitionCrud.create_definition(
            db,
            **payload.model_dump(),
        )
        _append_definition_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="success",
            definition_id=definition.id,
            after_summary=_audit_summary(definition),
        )
        db.commit()
        db.refresh(definition)
    except IntegrityError as error:
        _record_failure(
            db,
            audit_context=audit_context,
            action=action,
            definition_id=None,
            reason_code="vendor_event_definition_conflict",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该存储类型和事件代码已存在",
        ) from error
    except Exception:
        _record_failure(
            db,
            audit_context=audit_context,
            action=action,
            definition_id=None,
            reason_code="vendor_event_definition_create_failed",
        )
        raise
    return serialize_definition(definition)


def update_definition(
    db: Session,
    definition_id: int,
    payload,
    *,
    audit_context: AuditContext | None = None,
) -> dict:
    action = "vendor_event_definition.update"
    try:
        definition = vendorEventDefinitionCrud.get_definition_by_id(
            db,
            definition_id,
        )
        if definition is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="厂商事件代码定义不存在",
            )
        changes = payload.model_dump(exclude_unset=True)
        merged = {
            "storage_type": changes.get("storage_type", definition.storage_type),
            "review_status": changes.get("review_status", definition.review_status),
            "association_type": changes.get(
                "association_type",
                definition.association_type,
            ),
            "official_reference_url": changes.get(
                "official_reference_url",
                definition.official_reference_url,
            ),
            "version_scope": changes.get("version_scope", definition.version_scope),
            "recommended_solution_zh": changes.get(
                "recommended_solution_zh",
                definition.recommended_solution_zh,
            ),
        }
        try:
            validate_reviewed_definition_values(**merged)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        before_summary = _audit_summary(definition)
        definition = vendorEventDefinitionCrud.update_definition(
            db,
            definition_id,
            **changes,
        )
        _append_definition_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="success",
            definition_id=definition_id,
            before_summary=before_summary,
            after_summary=_audit_summary(definition),
        )
        db.commit()
        db.refresh(definition)
    except IntegrityError as error:
        _record_failure(
            db,
            audit_context=audit_context,
            action=action,
            definition_id=definition_id,
            reason_code="vendor_event_definition_conflict",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该存储类型和事件代码已存在",
        ) from error
    except HTTPException as error:
        _record_failure(
            db,
            audit_context=audit_context,
            action=action,
            definition_id=definition_id,
            reason_code=(
                "vendor_event_definition_not_found"
                if error.status_code == status.HTTP_404_NOT_FOUND
                else "vendor_event_definition_validation_failed"
            ),
        )
        raise
    except Exception:
        _record_failure(
            db,
            audit_context=audit_context,
            action=action,
            definition_id=definition_id,
            reason_code="vendor_event_definition_update_failed",
        )
        raise
    return serialize_definition(definition)


def delete_definition(
    db: Session,
    definition_id: int,
    *,
    audit_context: AuditContext | None = None,
) -> None:
    action = "vendor_event_definition.delete"
    try:
        definition = vendorEventDefinitionCrud.get_definition_by_id(
            db,
            definition_id,
        )
        if definition is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="厂商事件代码定义不存在",
            )
        before_summary = _audit_summary(definition)
        vendorEventDefinitionCrud.delete_definition(db, definition_id)
        _append_definition_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="success",
            definition_id=definition_id,
            before_summary=before_summary,
        )
        db.commit()
    except HTTPException:
        _record_failure(
            db,
            audit_context=audit_context,
            action=action,
            definition_id=definition_id,
            reason_code="vendor_event_definition_not_found",
        )
        raise
    except Exception:
        _record_failure(
            db,
            audit_context=audit_context,
            action=action,
            definition_id=definition_id,
            reason_code="vendor_event_definition_delete_failed",
        )
        raise


def _reconcile_legacy_incidents(db: Session) -> int:
    try:
        reconciliation_service = import_module(
            "services.incidentReconciliationService"
        )
    except ModuleNotFoundError as error:
        if error.name != "services.incidentReconciliationService":
            raise
        return 0
    result = reconciliation_service.reconcile_legacy_vendor_incidents(
        db,
        dry_run=False,
        now=utc_now(),
    )
    return int(result.get("closed", 0))


def discover(
    db: Session,
    *,
    audit_context: AuditContext | None = None,
) -> dict:
    action = "vendor_event_definition.discover"
    try:
        created = seed_common_definitions(db)
        existing = 0
        observed_codes = vendorEventDefinitionCrud.list_observed_vendor_event_codes(db)
        existing_by_key = vendorEventDefinitionCrud.get_definition_map(
            db,
            observed_codes,
        )
        for storage_type, event_code in observed_codes:
            definition = existing_by_key.get((storage_type, event_code))
            if definition is not None:
                existing += 1
                continue
            if len(event_code) > 255:
                # Historical alerts are uncontrolled input; a single oversized
                # code must not abort the whole discover run.
                continue
            try:
                with db.begin_nested():
                    vendorEventDefinitionCrud.create_definition(
                        db,
                        **_placeholder_values(storage_type, event_code),
                    )
                created += 1
            except IntegrityError:
                # A concurrent discover or admin create inserted the same
                # (storage_type, event_code) after our existence snapshot.
                existing += 1
        reconciled_incidents = _reconcile_legacy_incidents(db)
        result = {
            "created": created,
            "existing": existing,
            "reconciled_incidents": reconciled_incidents,
        }
        _append_definition_audit(
            db,
            audit_context=audit_context,
            action=action,
            outcome="success",
            after_summary=result,
        )
        db.commit()
    except Exception:
        _record_failure(
            db,
            audit_context=audit_context,
            action=action,
            definition_id=None,
            reason_code="vendor_event_definition_discover_failed",
        )
        raise
    return result


discover_definitions = discover
