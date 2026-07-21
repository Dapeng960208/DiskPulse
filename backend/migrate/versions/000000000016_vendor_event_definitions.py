"""Add the reviewed vendor event association catalog.

Revision ID: 000000000016
Revises: 000000000015
"""

from alembic import op
import sqlalchemy as sa


revision = "000000000016"
down_revision = "000000000015"
branch_labels = None
depends_on = None


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
_COMMON_SEEDS = (
    (
        "netapp",
        "wafl.vol.blks_used.done",
        "system_activity",
        "已用块计算完成",
        "卷或聚合的已用块扫描计算已经结束，属于完成通知，不表示故障。",
        _NETAPP_WAFL_VOLUME_URL,
        "warning",
        "ONTAP 9.14.1、9.18.1",
        "reviewed",
    ),
    (
        "netapp",
        "wafl.vol.snap_create.done",
        "system_activity",
        "快照创建扫描完成",
        "快照创建相关扫描已经完成，属于正常操作记录。",
        _NETAPP_WAFL_VOLUME_URL,
        "info",
        "ONTAP 9.14.1、9.18.1",
        "reviewed",
    ),
    (
        "netapp",
        "wafl.scan.ownblocks.done",
        "system_activity",
        "归属块检查完成",
        "用于检查块归属关系的 WAFL 扫描已经结束。",
        _NETAPP_WAFL_SCAN_URL,
        "info",
        "ONTAP 9.11.1、9.18.1",
        "reviewed",
    ),
    (
        "netapp",
        "wafl.scan.done",
        "system_activity",
        "WAFL 扫描完成",
        "某项 WAFL 扫描已经完成；具体扫描类型和对象应从事件参数读取。",
        _NETAPP_WAFL_SCAN_URL,
        "warning",
        "ONTAP 9.11.1、9.18.1",
        "reviewed",
    ),
    (
        "netapp",
        "nblade.execsOverLimit",
        "performance_anomaly",
        "NFS 请求并发超过连接阈值",
        "单个连接的并发在途请求超过允许值，系统开始限制请求，客户端性能可能下降。",
        "https://docs.netapp.com/us-en/ontap-ems/nblade-execsoverlimit-events.html",
        None,
        "ONTAP 9.10.1–9.18.1；严重度采用事件实例值",
        "reviewed",
    ),
    (
        "netapp",
        "secd.authsys.lookup.failed",
        "fault_log",
        "UNIX 用户凭据查询失败",
        "访问请求中的 UID 无法通过 NIS、LDAP 或本地文件名称服务解析。",
        "https://docs.netapp.com/us-en/ontap-ems/secd-authsys-events.html",
        "error",
        "ONTAP 9.11.1–9.18.1",
        "reviewed",
    ),
    (
        "netapp",
        "sis.auto.session.change",
        "system_activity",
        "后台去重会话数因负载调整",
        "系统根据当前负载节流自动存储效率任务，并调整后台去重会话数量；不等同于去重失败。",
        "https://docs.netapp.com/us-en/ontap-ems/sis-auto-events.html",
        "warning",
        "ONTAP 9.10.1–9.18.1",
        "reviewed",
    ),
    (
        "netapp",
        "fp.est.scan.catalog.updated",
        "system_activity",
        "空间效率估算目录已更新",
        "卷空间效率估算扫描的结果已经写入目录文件，属于状态更新。",
        "https://docs.netapp.com/us-en/ontap-ems-9181/fp-est-events.html",
        "warning",
        "ONTAP 9.18.1",
        "reviewed",
    ),
    (
        "netapp",
        "asup.aods.response.timeOut",
        "fault_log",
        "AutoSupport OnDemand 响应超时",
        "ONTAP 在规定时间内未收到 AutoSupport OnDemand 服务响应，应核查服务连通性。",
        "https://docs.netapp.com/us-en/ontap-ems/asup-aods-events.html",
        "error",
        "ONTAP 9.11.1–9.18.1",
        "reviewed",
    ),
    (
        "netapp",
        "kern.uptime.filer",
        "system_activity",
        "控制器运行状态周期记录",
        "控制器周期性记录运行时长和协议操作计数，通常每小时产生一次，不表示故障。",
        "https://docs.netapp.com/us-en/ontap-ems/kern-uptime-events.html",
        "warning",
        "ONTAP 9.10.1、9.14.1、9.16.1、9.18.1",
        "reviewed",
    ),
    (
        "netapp",
        "ccma.quota.throughput",
        "telemetry_degradation",
        "性能归档保留空间不足",
        "性能归档数据增长速度相对预留空间过高，可能缩短可保留的性能历史。",
        "https://docs.netapp.com/us-en/ontap-ems/ccma-quota-events.html",
        "warning",
        "ONTAP 9.14.1、9.18.1",
        "reviewed",
    ),
    (
        "netapp",
        "nis.group.db.build.success",
        "system_activity",
        "NIS 组数据库构建成功",
        "指定 SVM 的 NIS 组数据库已经成功构建，不是失败事件。",
        "https://docs.netapp.com/us-en/ontap-ems/nis-group-events.html",
        "warning",
        "ONTAP 9.10.1–9.18.1",
        "reviewed",
    ),
    (
        "isilon",
        "500010001",
        "capacity_threshold",
        "SmartQuotas 配额阈值触发",
        "某个 SmartQuotas 域达到软限制、硬限制或宽限期相关阈值；具体对象和阈值状态从事件实例参数读取。",
        _POWERSCALE_EVENT_LIST_URL,
        None,
        "OneFS 9.4.0.0（Dell H17458.1 事件列表）",
        "reviewed",
    ),
    (
        "isilon",
        "500010002",
        "fault_log",
        "SmartQuotas 通知发送失败",
        "系统未能向相关用户发送配额通知；不代表配额本身未生效。",
        _POWERSCALE_EVENT_LIST_URL,
        None,
        "OneFS 9.4.0.0（Dell H17458.1 事件列表）",
        "reviewed",
    ),
    (
        "isilon",
        "400050004",
        "system_activity",
        "CELOG 心跳事件",
        "CELOG 的周期性心跳自检事件，通常仅用于确认节点能发送告警，不应当显示成故障。",
        (
            "https://infohub.delltechnologies.com/en-uk/l/"
            "powerscale-onefs-advanced-alert-configurations/"
            "general-alert-configuration-considerations/"
        ),
        None,
        "OneFS 8.0–9.4.0.0（Dell 心跳说明与 H17458.1 事件列表）",
        "reviewed",
    ),
    (
        "isilon",
        "400100006",
        "fault_log",
        "计划作业未按计划启动",
        "指定 OneFS 作业未能按计划启动；应结合作业类型和当前事件日志核查。",
        _POWERSCALE_EVENT_LIST_URL,
        None,
        "OneFS 9.4.0.0（Dell H17458.1 事件列表）",
        "reviewed",
    ),
    (
        "isilon",
        "SW_JOBENG_JOB_STATE",
        "system_activity",
        "作业状态变化",
        "OneFS 作业引擎记录作业状态变化；需由目标阵列运行时目录复核。",
        None,
        None,
        "目标 OneFS 运行时事件目录",
        "pending",
    ),
    (
        "isilon",
        "SW_JOBENG_JOB_PHASE_BEGIN",
        "system_activity",
        "作业阶段开始",
        "OneFS 作业引擎记录作业阶段开始；需由目标阵列运行时目录复核。",
        None,
        None,
        "目标 OneFS 运行时事件目录",
        "pending",
    ),
    (
        "isilon",
        "SW_JOBENG_JOB_PHASE_END",
        "system_activity",
        "作业阶段结束",
        "OneFS 作业引擎记录作业阶段结束；需由目标阵列运行时目录复核。",
        None,
        None,
        "目标 OneFS 运行时事件目录",
        "pending",
    ),
    (
        "isilon",
        "SW_CELOG_HEARTBEAT",
        "system_activity",
        "CELOG 心跳事件",
        "OneFS CELOG 记录周期性心跳；需由目标阵列运行时目录复核。",
        None,
        None,
        "目标 OneFS 运行时事件目录",
        "pending",
    ),
    (
        "isilon",
        "QUOTA_THRESHOLD_VIOLATION",
        "capacity_threshold",
        "SmartQuotas 配额阈值触发",
        "OneFS 报告配额阈值事件；需由目标阵列运行时目录确认数字代码和描述。",
        None,
        None,
        "目标 OneFS 运行时事件目录",
        "pending",
    ),
    (
        "isilon",
        "SW_JOBENG_JOBSCHED_NOT_STARTED",
        "fault_log",
        "计划作业未按计划启动",
        "OneFS 报告计划作业未启动；需由目标阵列运行时目录复核。",
        None,
        None,
        "目标 OneFS 运行时事件目录",
        "pending",
    ),
    (
        "isilon",
        "QUOTA_NOTIFY_FAILED",
        "fault_log",
        "SmartQuotas 通知发送失败",
        "OneFS 报告配额通知发送失败；需由目标阵列运行时目录复核。",
        None,
        None,
        "目标 OneFS 运行时事件目录",
        "pending",
    ),
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
        sa.column("is_active", sa.Boolean()),
    )


def _seed_values(seed: tuple) -> dict:
    fields = (
        "storage_type",
        "event_code",
        "association_type",
        "title_zh",
        "description_zh",
        "official_reference_url",
        "default_severity",
        "version_scope",
        "review_status",
    )
    return {**dict(zip(fields, seed)), "is_active": True}


def _insert_missing_rows(bind, rows: list[dict]) -> None:
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
            continue
        bind.execute(sa.insert(definitions).values(**row))
        existing.add(key)


def upgrade() -> None:
    op.create_table(
        "vendor_event_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_type", sa.String(length=32), nullable=False),
        sa.Column("event_code", sa.String(length=255), nullable=False),
        sa.Column("association_type", sa.String(length=32), nullable=False),
        sa.Column("title_zh", sa.String(length=255), nullable=False),
        sa.Column("description_zh", sa.Text(), nullable=False),
        sa.Column("official_reference_url", sa.String(length=1000), nullable=True),
        sa.Column("default_severity", sa.String(length=16), nullable=True),
        sa.Column("version_scope", sa.String(length=255), nullable=True),
        sa.Column(
            "review_status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "storage_type IN ('netapp', 'isilon')",
            name="ck_vendor_event_definition_storage_type",
        ),
        sa.CheckConstraint(
            "association_type IN ("
            "'fault_log', 'performance_anomaly', 'capacity_threshold', "
            "'system_activity', 'telemetry_degradation', 'unknown'"
            ")",
            name="ck_vendor_event_definition_association_type",
        ),
        sa.CheckConstraint(
            "default_severity IS NULL OR default_severity IN ("
            "'critical', 'error', 'warning', 'info'"
            ")",
            name="ck_vendor_event_definition_default_severity",
        ),
        sa.CheckConstraint(
            "review_status IN ('reviewed', 'pending')",
            name="ck_vendor_event_definition_review_status",
        ),
        sa.CheckConstraint(
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
            ")",
            name="ck_vendor_event_definition_reviewed_evidence",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "storage_type",
            "event_code",
            name="uq_vendor_event_definition_storage_code",
        ),
    )
    op.create_index(
        "ix_vendor_event_definition_filters",
        "vendor_event_definitions",
        ["storage_type", "association_type", "review_status"],
    )
    op.create_index(
        "ix_vendor_event_definition_event_code",
        "vendor_event_definitions",
        ["event_code"],
    )

    bind = op.get_bind()
    _insert_missing_rows(bind, [_seed_values(seed) for seed in _COMMON_SEEDS])


def downgrade() -> None:
    op.drop_index(
        "ix_vendor_event_definition_event_code",
        table_name="vendor_event_definitions",
    )
    op.drop_index(
        "ix_vendor_event_definition_filters",
        table_name="vendor_event_definitions",
    )
    op.drop_table("vendor_event_definitions")
