# 待核验厂商事件清单

独立初始化目录使用《PowerScale OneFS Event Reference Guide》（2021 年 10 月）补齐 Software events 与 Hardware events 两章的 499 条事件定义。目录数据不再由 Alembic revision 写入；统一初始化命令在结构迁移完成后只插入数据库中缺失的 `(storage_type, event_code)`。

Dell SRS Brevity 表格另有 15 条代码未出现在该版指南中；连同原有 17 条仍缺逐代码版本或处置证据的 PowerScale 代码，以及 10 条 NetApp 代码，初始化目录保留 42 条 `unknown + pending` 定义。NetApp《raid events : ONTAP EMS reference》中 `WARNING` 及以上的 152 条已经纳入初始化目录；本节保留的 NetApp 项要么不属于该 RAID 文档，要么严重度低于本次收录门槛。完整索引见 [NetApp ONTAP 清单](netapp-event-association-list.md)和 [Dell PowerScale 清单](isilon-event-association-list.md)。

## Dell PowerScale（32 项）

官方入口包括 [PowerScale SRS Brevity 事件清单](https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/)和 [PowerScale OneFS Event Reference Guide（2021 年 10 月）](https://dl.dell.com/content/docu96961)。未匹配或版本证据不足的代码不得仅根据相邻代码或英文短名升级为已审核定义。

| 事件代码 | 厂商 | 缺失证据 | 所需补证方式 | 状态 |
| --- | --- | --- | --- | --- |
| `400040005` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `400040008` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `400040016` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900010000` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900030023` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900040035` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900090025` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900100010` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900100011` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900100012` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900100013` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900100014` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900100015` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900100016` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `900100017` | Dell PowerScale | SRS 表格有摘要，但 2021 年 10 月指南无对应条目 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `400200001` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `400200002` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `400260000` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `HW_POWEREDGE_IDRAC_MGMT_SERVICE` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `QUOTA_NOTIFY_FAILED` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `QUOTA_THRESHOLD_VIOLATION` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SW_ACCOUNT_UPDATED` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SW_CELOG_HEARTBEAT` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SW_JOBENG_JOB_PHASE_BEGIN` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SW_JOBENG_JOB_PHASE_END` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SW_JOBENG_JOBSCHED_NOT_STARTED` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SW_JOBENG_JOB_STATE` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SW_LICENSE_ENTITLEMENTS_EXCEEDED` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SW_SECURITY_VERIFICATION_FAILURE` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SW_SECURITY_VERIFICATION_SUCCESS` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SYS_NVME_PCI_LINK_ERROR` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `SYS_PCI_AER` | Dell PowerScale | 精确事件语义、适用版本或可审核处置仍不完整 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |

## NetApp ONTAP（10 项）

已查 ONTAP EMS 当前与版本化事件页。`raid.aggr.log.CP.count` 虽存在于 RAID 文档，但严重度低于 `WARNING`，本次不升级；其他项目需要能同时证明精确代码含义、适用版本与官方处置的事件页或目标阵列 EMS 输出。

| 事件代码 | 厂商 | 已查官方入口 | 缺失证据 | 所需补证方式 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `disk.ddr.scan.start` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 对应版本 EMS 页或目标阵列 EMS 输出 | `pending` |
| `disk.ddr.scan.summary` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `license.check.ok` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `monitor.volumes.one.ok` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `quota.exceeded` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `quota.normal` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `raid.aggr.log.CP.count` | NetApp ONTAP | ONTAP 9.14.1 RAID EMS 文档 | 严重度低于本次 `WARNING` 收录门槛 | 如需启用，单独审核其系统活动语义 | `pending` |
| `tsse_compression_done` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `wafl.inode.fill.enable` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `wafl.scan.start` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |

补证后须在管理目录中填写官方 HTTPS URL、适用版本、明确关联类型和非空中文方案，才可提升为 `reviewed`。
