"""Complete the vendor event association catalog with evidence-backed actions.

Revision ID: 000000000017
Revises: 000000000016
"""

from alembic import op
import sqlalchemy as sa


revision = "000000000017"
down_revision = "000000000016"
branch_labels = None
depends_on = None


_UNKNOWN_TITLE_ZH = "未收录的厂商事件代码"
_UNKNOWN_DESCRIPTION_ZH = "尚未获得该事件代码的逐项官方语义与处置证据。"
_POWERSCALE_EVENT_LIST_URL = (
    "https://infohub.delltechnologies.com/en-us/l/"
    "powerscale-onefs-advanced-alert-configurations/"
    "appendix-b-full-list-of-srs-brevity/"
)

_PREVIOUS_REVIEWED_EVIDENCE_CHECK = (
    "review_status <> 'reviewed' OR ("
    "association_type <> 'unknown' "
    "AND official_reference_url IS NOT NULL "
    "AND trim(official_reference_url) <> '' "
    "AND official_reference_url NOT LIKE '%@%' "
    "AND official_reference_url NOT LIKE '% %' "
    "AND ((storage_type = 'netapp' AND ("
    "lower(official_reference_url) LIKE 'https://netapp.com/%' "
    "OR lower(official_reference_url) LIKE 'https://%.netapp.com/%'"
    ")) OR (storage_type = 'isilon' AND ("
    "lower(official_reference_url) LIKE 'https://dell.com/%' "
    "OR lower(official_reference_url) LIKE 'https://%.dell.com/%' "
    "OR lower(official_reference_url) LIKE 'https://delltechnologies.com/%' "
    "OR lower(official_reference_url) LIKE 'https://%.delltechnologies.com/%'"
    "))) "
    "AND version_scope IS NOT NULL "
    "AND trim(version_scope) <> ''"
    ")"
)
_REVIEWED_EVIDENCE_CHECK = (
    _PREVIOUS_REVIEWED_EVIDENCE_CHECK[:-1]
    + " AND recommended_solution_zh IS NOT NULL "
    + "AND trim(recommended_solution_zh) <> ''"
    + ")"
)


def _reviewed(
    storage_type: str,
    event_code: str,
    association_type: str,
    title_zh: str,
    description_zh: str,
    official_reference_url: str,
    version_scope: str,
    recommended_solution_zh: str,
    default_severity: str | None = None,
) -> dict:
    return {
        "storage_type": storage_type,
        "event_code": event_code,
        "association_type": association_type,
        "title_zh": title_zh,
        "description_zh": description_zh,
        "official_reference_url": official_reference_url,
        "default_severity": default_severity,
        "version_scope": version_scope,
        "review_status": "reviewed",
        "recommended_solution_zh": recommended_solution_zh,
        "is_active": True,
    }


def _pending(storage_type: str, event_code: str) -> dict:
    return {
        "storage_type": storage_type,
        "event_code": event_code,
        "association_type": "unknown",
        "title_zh": _UNKNOWN_TITLE_ZH,
        "description_zh": _UNKNOWN_DESCRIPTION_ZH,
        "official_reference_url": None,
        "default_severity": None,
        "version_scope": None,
        "review_status": "pending",
        "recommended_solution_zh": None,
        "is_active": True,
    }


_REVIEWED_DEFINITIONS = (
    _reviewed("netapp", "wafl.vol.blks_used.done", "system_activity", "已用块计算完成", "卷或聚合的已用块扫描计算已经结束，属于完成通知。", "https://docs.netapp.com/us-en/ontap-ems-9181/wafl-vol-events.html", "ONTAP 9.14.1、9.18.1", "无需立即操作；保留该完成事件用于审计。", "warning"),
    _reviewed("netapp", "wafl.vol.snap_create.done", "system_activity", "快照创建扫描完成", "快照创建相关扫描已经完成，属于正常操作记录。", "https://docs.netapp.com/us-en/ontap-ems-9181/wafl-vol-events.html", "ONTAP 9.14.1、9.18.1", "无需立即操作；保留该完成事件用于审计。", "info"),
    _reviewed("netapp", "wafl.scan.ownblocks.done", "system_activity", "归属块检查完成", "用于检查块归属关系的 WAFL 扫描已经结束。", "https://docs.netapp.com/us-en/ontap-ems-9181/wafl-scan-events.html", "ONTAP 9.11.1、9.18.1", "无需立即操作；保留扫描完成记录用于审计。", "info"),
    _reviewed("netapp", "wafl.scan.done", "system_activity", "WAFL 扫描完成", "某项 WAFL 扫描已经完成。", "https://docs.netapp.com/us-en/ontap-ems-9181/wafl-scan-events.html", "ONTAP 9.11.1、9.18.1", "无需立即操作；如伴随失败事件，再按对应失败代码排查。", "warning"),
    _reviewed("netapp", "nblade.execsOverLimit", "performance_anomaly", "NFS 请求并发超过连接阈值", "单个连接的并发在途请求超过允许值，客户端性能可能下降。", "https://docs.netapp.com/us-en/ontap-ems/nblade-execsoverlimit-events.html", "ONTAP 9.10.1–9.18.1", "检查客户端并发请求和节点负载，并按官方事件页的处置步骤处理。"),
    _reviewed("netapp", "secd.authsys.lookup.failed", "fault_log", "UNIX 用户凭据查询失败", "访问请求中的 UID 无法通过名称服务解析。", "https://docs.netapp.com/us-en/ontap-ems/secd-authsys-events.html", "ONTAP 9.11.1–9.18.1", "检查名称服务配置、网络连通性及相应认证后端。", "error"),
    _reviewed("netapp", "sis.auto.session.change", "system_activity", "后台去重会话数因负载调整", "系统根据当前负载调整后台存储效率会话数量。", "https://docs.netapp.com/us-en/ontap-ems/sis-auto-events.html", "ONTAP 9.10.1–9.18.1", "无需立即操作；结合负载和存储效率作业状态持续观察。", "warning"),
    _reviewed("netapp", "fp.est.scan.catalog.updated", "system_activity", "空间效率估算目录已更新", "卷空间效率估算扫描结果已经写入目录文件。", "https://docs.netapp.com/us-en/ontap-ems-9181/fp-est-events.html", "ONTAP 9.18.1", "无需立即操作；保留目录更新记录用于审计。", "warning"),
    _reviewed("netapp", "asup.aods.response.timeOut", "telemetry_degradation", "AutoSupport OnDemand 响应超时", "ONTAP 未在规定时间内收到 AutoSupport OnDemand 服务响应。", "https://docs.netapp.com/us-en/ontap-ems/asup-aods-events.html", "ONTAP 9.11.1–9.18.1", "检查 AutoSupport OnDemand 服务连通性和配置。", "error"),
    _reviewed("netapp", "kern.uptime.filer", "system_activity", "控制器运行状态周期记录", "控制器周期性记录运行时长和协议操作计数。", "https://docs.netapp.com/us-en/ontap-ems/kern-uptime-events.html", "ONTAP 9.10.1、9.14.1、9.16.1、9.18.1", "无需立即操作；保留周期记录用于运行状态审计。", "warning"),
    _reviewed("netapp", "ccma.quota.throughput", "telemetry_degradation", "性能归档保留空间不足", "性能归档数据增长速度相对预留空间过高。", "https://docs.netapp.com/us-en/ontap-ems/ccma-quota-events.html", "ONTAP 9.14.1、9.18.1", "检查性能归档保留空间和数据增长情况。", "warning"),
    _reviewed("netapp", "nis.group.db.build.success", "system_activity", "NIS 组数据库构建成功", "指定 SVM 的 NIS 组数据库已经成功构建。", "https://docs.netapp.com/us-en/ontap-ems/nis-group-events.html", "ONTAP 9.10.1–9.18.1", "无需立即操作；保留成功记录用于审计。", "warning"),
    _reviewed("netapp", "arw.volume.state", "system_activity", "卷防勒索软件状态变更", "卷的自主勒索软件保护状态发生变更。", "https://docs.netapp.com/us-en/ontap-ems-9141/arw-volume-events.html", "ONTAP 9.14.1", "检查该卷的防勒索软件状态；官方页面说明无须对状态变更事件单独操作。"),
    _reviewed("netapp", "asup.post.drop", "telemetry_degradation", "AutoSupport 消息投递失败", "AutoSupport 消息在重试后仍未成功投递。", "https://docs.netapp.com/us-en/ontap-ems-9161/asup-post-events.html", "ONTAP 9.16.1", "运行 system node autosupport check show-details；仍失败时联系 NetApp 支持。", "warning"),
    _reviewed("netapp", "callhome.management.log", "system_activity", "管理日志 CallHome", "系统发送每日 MANAGEMENT_LOG CallHome。", "https://docs.netapp.com/us-en/ontap-ems-9141/callhome-management-events.html", "ONTAP 9.14.1", "无需立即操作；该事件用于管理日志 CallHome 审计。", "info"),
    _reviewed("netapp", "callhome.performance.data", "system_activity", "性能数据 CallHome", "系统发送每周性能数据 CallHome。", "https://docs.netapp.com/us-en/ontap-ems-9161/callhome-performance-events.html", "ONTAP 9.16.1", "无需立即操作；该事件用于性能数据 CallHome 审计。", "info"),
    _reviewed("netapp", "configbr.backupCompleted", "system_activity", "配置备份完成", "计划配置备份已完成。", "https://docs.netapp.com/us-en/ontap-ems/configbr-backupcompleted-events.html", "ONTAP EMS 当前文档", "无需立即操作；保留配置备份完成记录用于审计。", "info"),
    _reviewed("netapp", "mhost.ca.connect.cert.error", "fault_log", "证书连接错误", "管理主机 CA 连接发生证书错误。", "https://docs.netapp.com/us-en/ontap-ems/mhost-ca-events.html", "ONTAP EMS 当前文档", "检查 CA 证书的有效性、信任链和管理主机连接。", "error"),
    _reviewed("netapp", "mhost.ca.connect.delete", "system_activity", "CA 连接删除", "管理主机 CA 连接已删除。", "https://docs.netapp.com/us-en/ontap-ems/mhost-ca-events.html", "ONTAP EMS 当前文档", "确认删除操作已获授权；如仍需连接，按官方步骤重新配置。", "info"),
    _reviewed("netapp", "mhost.ca.connect.failure", "fault_log", "CA 连接失败", "管理主机无法连接到 CA。", "https://docs.netapp.com/us-en/ontap-ems/mhost-ca-events.html", "ONTAP EMS 当前文档", "检查 CA 服务可用性、网络路径和证书配置。", "error"),
    _reviewed("netapp", "quota.push.rules.complete", "system_activity", "配额规则推送完成", "配额规则推送已经完成。", "https://docs.netapp.com/us-en/ontap-ems-9171/quota-push-events.html", "ONTAP 9.17.1", "无需立即操作；保留完成记录用于配额变更审计。", "info"),
    _reviewed("netapp", "quota.push.rules.start", "system_activity", "配额规则推送开始", "配额规则推送已经开始。", "https://docs.netapp.com/us-en/ontap-ems-9171/quota-push-events.html", "ONTAP 9.17.1", "无需立即操作；等待完成或后续失败事件。", "info"),
    _reviewed("netapp", "quota.resize.start", "system_activity", "配额调整开始", "配额调整操作已经开始。", "https://docs.netapp.com/us-en/ontap-ems-9111/quota-resize-events.html", "ONTAP 9.11.1", "无需立即操作；等待调整完成或后续失败事件。", "info"),
    _reviewed("netapp", "quota.resize.stop", "system_activity", "配额调整停止", "配额调整操作已经停止。", "https://docs.netapp.com/us-en/ontap-ems-9111/quota-resize-events.html", "ONTAP 9.11.1", "检查配额调整是否按预期完成；如未完成，按官方步骤重新执行。", "warning"),
    _reviewed("netapp", "quota.softlimit.exceeded", "capacity_threshold", "配额软限制超过", "配额使用量超过软限制。", "https://docs.netapp.com/us-en/ontap-ems/quota-softlimit-events.html", "ONTAP EMS 当前文档", "通知相关用户清理或申请扩容，并按配额通知策略跟进。", "warning"),
    _reviewed("netapp", "quota.softlimit.normal", "system_activity", "配额软限制恢复正常", "配额使用量已恢复到软限制以下。", "https://docs.netapp.com/us-en/ontap-ems/quota-softlimit-events.html", "ONTAP EMS 当前文档", "无需立即操作；保留恢复记录用于审计。", "info"),
    _reviewed("netapp", "wafl.quota.user.exceeded", "capacity_threshold", "用户配额超过", "用户使用量已超过配额。", "https://docs.netapp.com/us-en/ontap-ems/wafl-quota-events.html", "ONTAP EMS 当前文档", "减少占用或提高配额；必要时执行配额调整。", "warning"),
    _reviewed("netapp", "wafl.analytics.enterOverload", "telemetry_degradation", "文件系统分析进入过载", "文件系统分析因过载受到限制。", "https://docs.netapp.com/us-en/ontap-ems/wafl-analytics-events.html", "ONTAP EMS 当前文档", "降低分析负载或等待系统恢复；关注后续退出过载事件。", "warning"),
    _reviewed("netapp", "wafl.analytics.exitOverload", "system_activity", "文件系统分析退出过载", "文件系统分析已退出过载状态。", "https://docs.netapp.com/us-en/ontap-ems/wafl-analytics-events.html", "ONTAP EMS 当前文档", "无需立即操作；保留恢复记录用于审计。", "info"),
    _reviewed("netapp", "wafl.compress.cde.event", "system_activity", "压缩数据效率事件", "WAFL 压缩数据效率操作产生状态事件。", "https://docs.netapp.com/us-en/ontap-ems-9101/wafl-compress-events.html", "ONTAP 9.10.1", "根据事件页的具体消息确认状态；无失败伴随时无需立即操作。", "info"),
    _reviewed("netapp", "wafl.data.compaction.event", "system_activity", "数据压缩整理事件", "WAFL 数据压缩整理操作产生状态事件。", "https://docs.netapp.com/us-en/ontap-ems/wafl-data-events.html", "ONTAP EMS 当前文档", "根据事件页的具体消息确认状态；无失败伴随时无需立即操作。", "info"),
    _reviewed("netapp", "wafl.rclm.est.scan.done", "system_activity", "空间回收估算扫描完成", "空间回收估算扫描已完成。", "https://docs.netapp.com/us-en/ontap-ems/wafl-rclm-events.html", "ONTAP EMS 当前文档", "无需立即操作；保留扫描完成记录用于审计。", "info"),
    _reviewed("netapp", "wafl.spacemgmnt.policyChg", "system_activity", "空间管理策略变更", "WAFL 空间管理策略发生变更。", "https://docs.netapp.com/us-en/ontap-ems-9181/wafl-spacemgmnt-events.html", "ONTAP 9.18.1", "确认策略变更已获授权，并核对相关卷或聚合配置。", "warning"),
)

_PENDING_ISILON_CODES = (
    "100010060", "100010062", "400050004", "400070007", "400100006",
    "400200001", "400200002", "400260000", "500010001", "500010002",
    "900180001", "HW_POWEREDGE_IDRAC_MGMT_SERVICE", "QUOTA_NOTIFY_FAILED",
    "QUOTA_THRESHOLD_VIOLATION", "SW_ACCOUNT_UPDATED", "SW_CELOG_HEARTBEAT",
    "SW_JOBENG_JOB_PHASE_BEGIN", "SW_JOBENG_JOB_PHASE_END",
    "SW_JOBENG_JOBSCHED_NOT_STARTED", "SW_JOBENG_JOB_STATE",
    "SW_LICENSE_ENTITLEMENTS_EXCEEDED", "SW_SECURITY_VERIFICATION_FAILURE",
    "SW_SECURITY_VERIFICATION_SUCCESS", "SYS_NVME_PCI_LINK_ERROR", "SYS_PCI_AER",
)
_PENDING_NETAPP_CODES = (
    "disk.ddr.scan.start", "disk.ddr.scan.summary", "license.check.ok",
    "monitor.volumes.one.ok", "quota.exceeded", "quota.normal",
    "raid.aggr.log.CP.count", "tsse_compression_done", "wafl.inode.fill.enable",
    "wafl.scan.start",
)

CATALOG_DEFINITIONS = (
    *_REVIEWED_DEFINITIONS,
    *(_pending("isilon", event_code) for event_code in _PENDING_ISILON_CODES),
    *(_pending("netapp", event_code) for event_code in _PENDING_NETAPP_CODES),
)


def _definition_table():
    return sa.table(
        "vendor_event_definitions",
        sa.column("storage_type", sa.String(length=32)),
        sa.column("event_code", sa.String(length=255)),
        sa.column("association_type", sa.String(length=32)),
        sa.column("title_zh", sa.String(length=255)),
        sa.column("description_zh", sa.Text()),
        sa.column("official_reference_url", sa.String(length=1000)),
        sa.column("default_severity", sa.String(length=16)),
        sa.column("version_scope", sa.String(length=255)),
        sa.column("review_status", sa.String(length=16)),
        sa.column("recommended_solution_zh", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )


def _upsert_catalog_rows(bind, rows) -> None:
    definitions = _definition_table()
    existing = {
        (storage_type, event_code)
        for storage_type, event_code in bind.execute(
            sa.select(definitions.c.storage_type, definitions.c.event_code)
        )
    }
    for row in rows:
        key = (row["storage_type"], row["event_code"])
        if key in existing:
            bind.execute(
                sa.update(definitions)
                .where(
                    definitions.c.storage_type == row["storage_type"],
                    definitions.c.event_code == row["event_code"],
                )
                .values(**row)
            )
        else:
            bind.execute(sa.insert(definitions).values(**row))
            existing.add(key)


def _replace_reviewed_evidence_check(check_sql: str, *, drop_solution: bool) -> None:
    if op.get_context().as_sql:
        op.execute(
            "-- replace ck_vendor_event_definition_reviewed_evidence: " + check_sql
        )
        return
    with op.batch_alter_table("vendor_event_definitions", recreate="always") as batch:
        batch.drop_constraint(
            "ck_vendor_event_definition_reviewed_evidence",
            type_="check",
        )
        batch.create_check_constraint(
            "ck_vendor_event_definition_reviewed_evidence",
            check_sql,
        )
        if drop_solution:
            batch.drop_column("recommended_solution_zh")


def upgrade() -> None:
    op.add_column(
        "vendor_event_definitions",
        sa.Column("recommended_solution_zh", sa.Text(), nullable=True),
    )
    _upsert_catalog_rows(op.get_bind(), CATALOG_DEFINITIONS)
    _replace_reviewed_evidence_check(
        _REVIEWED_EVIDENCE_CHECK,
        drop_solution=False,
    )


def downgrade() -> None:
    _replace_reviewed_evidence_check(
        _PREVIOUS_REVIEWED_EVIDENCE_CHECK,
        drop_solution=True,
    )
