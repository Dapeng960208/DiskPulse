# 厂商事件待核验清单

`000000000017` 对测试库现有的 68 个事件代码逐项给出结果。本清单中的 35 项已在公开厂商资料中检索，但缺少“精确代码 + 可审核语义/版本 + 明确处置或无需操作”的完整证据，故目录固定为 `unknown + pending`，URL、版本和推荐方案均为空。

## Dell PowerScale（25 项）

已查入口：[PowerScale SRS Brevity 事件清单](https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/)。该公开清单不足以为以下单项代码提供完整处置闭环；需要目标 OneFS 版本的 Event Reference Guide 或设备运行时事件目录输出。

| 事件代码 | 厂商 | 已查官方入口 | 缺失证据 | 所需补证方式 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `100010060` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 目标 OneFS Event Reference Guide 或设备运行时目录 | `pending` |
| `100010062` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `400050004` | Dell PowerScale | SRS Brevity 清单 | 可审核处置步骤 | 同上 | `pending` |
| `400070007` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `400100006` | Dell PowerScale | SRS Brevity 清单 | 可审核处置步骤 | 同上 | `pending` |
| `400200001` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `400200002` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `400260000` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `500010001` | Dell PowerScale | SRS Brevity 清单 | 可审核处置步骤 | 同上 | `pending` |
| `500010002` | Dell PowerScale | SRS Brevity 清单 | 可审核处置步骤 | 同上 | `pending` |
| `900180001` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `HW_POWEREDGE_IDRAC_MGMT_SERVICE` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `QUOTA_NOTIFY_FAILED` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `QUOTA_THRESHOLD_VIOLATION` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SW_ACCOUNT_UPDATED` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SW_CELOG_HEARTBEAT` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SW_JOBENG_JOB_PHASE_BEGIN` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SW_JOBENG_JOB_PHASE_END` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SW_JOBENG_JOBSCHED_NOT_STARTED` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SW_JOBENG_JOB_STATE` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SW_LICENSE_ENTITLEMENTS_EXCEEDED` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SW_SECURITY_VERIFICATION_FAILURE` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SW_SECURITY_VERIFICATION_SUCCESS` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SYS_NVME_PCI_LINK_ERROR` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `SYS_PCI_AER` | Dell PowerScale | SRS Brevity 清单 | 精确事件语义、版本与处置 | 同上 | `pending` |

## NetApp ONTAP（10 项）

已查 ONTAP EMS 当前与版本化事件页；需要能同时证明精确代码含义、适用版本与官方处置的事件页或目标阵列 EMS 输出。

| 事件代码 | 厂商 | 已查官方入口 | 缺失证据 | 所需补证方式 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `disk.ddr.scan.start` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 对应版本 EMS 页或目标阵列 EMS 输出 | `pending` |
| `disk.ddr.scan.summary` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `license.check.ok` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `monitor.volumes.one.ok` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `quota.exceeded` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `quota.normal` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `raid.aggr.log.CP.count` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义与处置 | 同上 | `pending` |
| `tsse_compression_done` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `wafl.inode.fill.enable` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |
| `wafl.scan.start` | NetApp ONTAP | ONTAP EMS 事件页 | 精确事件语义、版本与处置 | 同上 | `pending` |

补证后须在管理目录中填写官方 HTTPS URL、适用版本、明确关联类型和非空中文方案，才可提升为 `reviewed`。
