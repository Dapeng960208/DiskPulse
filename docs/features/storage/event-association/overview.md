# 厂商事件关联目录

## 目标与边界

厂商事件关联目录为 NetApp ONTAP EMS 和 Dell PowerScale（Isilon）事件代码提供可维护的中文语义。它解决“只有事件代码或故障指纹，无法判断这是性能异常、故障日志还是正常系统运行事件”的问题，但不替代 `storage_alerts` 中的原始厂商事件，也不修改设备返回的日志正文。

目录只保存短中文说明、分类和官网依据，不复制厂商事件手册。未经官网或设备运行时目录确认的代码必须保持“未分类厂商事件/待审核”，不能根据代码相邻关系、英文名称或相似描述猜测含义，也不能静态假设 PowerScale 数字代码与符号代码互为别名。

## 数据模型与分类

`vendor_event_definitions` 以 `(storage_type, event_code)` 唯一标识一条定义。主要字段包括存储类型、事件代码、关联类型、中文标题、中文说明、官网链接、默认严重级别、适用版本、审核状态、`recommended_solution_zh`（中文推荐解决方案）、启用状态和创建/更新时间。默认严重级别只用于解释目录，具体事件仍优先展示设备实例返回的严重级别。

关联类型使用固定枚举：

| 值 | 中文含义 | 使用边界 |
| --- | --- | --- |
| `fault_log` | 故障日志 | 厂商明确表示失败、不可用或错误，需要排查设备或服务。 |
| `performance_anomaly` | 性能异常 | 并发、延迟、吞吐或后台任务受负载限制，可能影响性能但不等同于硬件故障。 |
| `capacity_threshold` | 容量/配额阈值 | 容量、配额、软硬限制或宽限期阈值事件。 |
| `system_activity` | 系统运行事件 | 扫描完成、作业阶段、状态变化、心跳等操作记录，不应展示成故障。 |
| `telemetry_degradation` | 监控能力下降 | 性能归档、遥测或监控留存能力下降，影响观测质量。 |
| `unknown` | 未分类厂商事件 | 尚无足够依据，必须等待人工审核或设备运行时目录确认。 |

审核状态只有 `reviewed`（已审核）和 `pending`（待审核）。只有 `is_active=true` 且 `review_status=reviewed` 的定义能影响业务分类和展示。定义进入 `reviewed` 前必须同时满足：关联类型不是 `unknown`、有非空版本范围、逐代码的厂商官方 HTTPS 依据，以及非空的 `recommended_solution_zh`；方案只能翻译官方处置步骤或明确的“无需操作”结论。

任何状态只要填写官网依据，都会执行存储类型与域名绑定校验：NetApp 只允许 `netapp.com` 及其子域；Isilon/PowerScale 只允许 `dell.com`、`delltechnologies.com` 及其子域。链接禁止用户信息、显式端口、空白、尾点和任意位置的 `@`，避免把跨厂商或伪装链接作为审核依据。

`pending` 只是超级管理员目录中的审核候选，不向普通用户输出其候选标题或类型，不形成正式中文语义，也不进入“重复故障”。自动发现的新代码只创建 `unknown + pending` 占位定义，不从事件正文推断分类。

## 官网依据与基础定义

独立初始化目录汇总了测试库原有的 68 个代码，以及原 revision `000000000018` 整理的 NetApp、Dell SRS Brevity 候选和 Dell《PowerScale OneFS Event Reference Guide》（2021 年 10 月）Software events、Hardware events 两章。两章中的 499 条 PowerScale 代码均保存中文标题、说明和管理员操作并升级为 `reviewed`。目录还读取 NetApp《raid events : ONTAP EMS reference》（2026 年 5 月 19 日生成，文档源为 ONTAP 9.14.1），只收录 `WARNING` 及以上严重度；该文档实际筛出 `ERROR` 104 条、`ALERT` 31 条、`EMERGENCY` 17 条，共 152 条，未出现 `WARNING`。初始化目录共覆盖 730 条代码，合计 688 条 `reviewed` 和 42 条 `pending`。完整索引见 [NetApp ONTAP 清单](netapp-event-association-list.md)和 [Dell PowerScale 清单](isilon-event-association-list.md)，待核验原因见[待核验事件清单](unverified-code-list.md)。不得为了维持历史审核数量保留泛化 KB、概览页面或社区帖的推断结果。基础的 12 条已审核 NetApp 定义如下：

| 事件代码 | 中文含义 / 关联类型 | 已核实版本 | 官网依据 |
| --- | --- | --- | --- |
| `wafl.vol.blks_used.done` | 已用块计算完成 / 系统运行事件 | ONTAP 9.14.1、9.18.1 | [WAFL volume events](https://docs.netapp.com/us-en/ontap-ems-9181/wafl-vol-events.html) |
| `wafl.vol.snap_create.done` | 快照创建扫描完成 / 系统运行事件 | ONTAP 9.14.1、9.18.1 | [WAFL volume events](https://docs.netapp.com/us-en/ontap-ems-9181/wafl-vol-events.html) |
| `wafl.scan.ownblocks.done` | 归属块检查完成 / 系统运行事件 | ONTAP 9.11.1、9.18.1 | [WAFL scan events](https://docs.netapp.com/us-en/ontap-ems-9181/wafl-scan-events.html) |
| `wafl.scan.done` | WAFL 扫描完成 / 系统运行事件 | ONTAP 9.11.1、9.18.1 | [WAFL scan events](https://docs.netapp.com/us-en/ontap-ems-9181/wafl-scan-events.html) |
| `nblade.execsOverLimit` | NFS 请求并发超过连接阈值 / 性能异常 | ONTAP 9.10.1–9.18.1 | [nblade.execsOverLimit](https://docs.netapp.com/us-en/ontap-ems/nblade-execsoverlimit-events.html) |
| `secd.authsys.lookup.failed` | UNIX 用户凭据查询失败 / 故障日志 | ONTAP 9.11.1–9.18.1 | [secd.authsys events](https://docs.netapp.com/us-en/ontap-ems/secd-authsys-events.html) |
| `sis.auto.session.change` | 后台去重会话数因负载调整 / 系统运行事件 | ONTAP 9.10.1–9.18.1 | [sis.auto events](https://docs.netapp.com/us-en/ontap-ems/sis-auto-events.html) |
| `fp.est.scan.catalog.updated` | 空间效率估算目录已更新 / 系统运行事件 | ONTAP 9.18.1 | [fp.est events](https://docs.netapp.com/us-en/ontap-ems-9181/fp-est-events.html) |
| `asup.aods.response.timeOut` | AutoSupport OnDemand 响应超时 / 故障日志 | ONTAP 9.11.1–9.18.1 | [asup.aods events](https://docs.netapp.com/us-en/ontap-ems/asup-aods-events.html) |
| `kern.uptime.filer` | 控制器运行状态周期记录 / 系统运行事件 | ONTAP 9.10.1、9.14.1、9.16.1、9.18.1 | [kern.uptime events](https://docs.netapp.com/us-en/ontap-ems/kern-uptime-events.html) |
| `ccma.quota.throughput` | 性能归档保留空间不足 / 监控能力下降 | ONTAP 9.14.1、9.18.1 | [ccma.quota events](https://docs.netapp.com/us-en/ontap-ems/ccma-quota-events.html) |
| `nis.group.db.build.success` | NIS 组数据库构建成功 / 系统运行事件 | ONTAP 9.10.1–9.18.1 | [nis.group events](https://docs.netapp.com/us-en/ontap-ems/nis-group-events.html) |

初始化目录还审核了 `arw.volume.state`、`asup.post.drop`、`callhome.*`、`configbr.backupCompleted`、`mhost.ca.connect.*`、`quota.push.*`、`quota.resize.*`、`quota.softlimit.*`、`wafl.quota.user.exceeded`、`wafl.analytics.*`、`wafl.compress.cde.event`、`wafl.data.compaction.event`、`wafl.rclm.est.scan.done` 和 `wafl.spacemgmnt.policyChg`。每条都保存对应的 NetApp EMS 事件页、版本范围和简短中文处置；例如 [AutoSupport 投递失败](https://docs.netapp.com/us-en/ontap-ems-9161/asup-post-events.html)、[配额软限制](https://docs.netapp.com/us-en/ontap-ems/quota-softlimit-events.html) 与 [文件系统分析过载](https://docs.netapp.com/us-en/ontap-ems/wafl-analytics-events.html)。

NetApp RAID 补充定义使用 [ONTAP 9.14.1 raid events](https://docs.netapp.com/us-en/ontap-ems-9141/raid-aggr-events.html) 作为逐代码官方依据，翻译 `Description` 与 `Corrective Action`，并保留厂商严重度映射：`WARNING→warning`、`ERROR→error`、`ALERT/EMERGENCY→critical`。低于 `WARNING` 的 `NOTICE`、`INFORMATIONAL` 等事件不因本次 PDF 批量收录而升级；其中 `raid.aggr.log.CP.count` 仍按待核验清单管理。

Dell 的 [PowerScale SRS Brevity 事件清单](https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/)用于定位数字事件名称；[PowerScale OneFS Event Reference Guide（2021 年 10 月）](https://dl.dell.com/content/docu96961)的 Software events 与 Hardware events 章节用于补齐逐代码标题、说明和 Administrator action。该指南两章中的 499 条代码均已翻译并升级为 `reviewed`；SRS 页面有摘要但该版指南没有对应条目的 15 条代码，以及其他缺少版本化处置证据的代码继续保持 `pending`。

PowerScale 还提供[事件组定义 API](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference/event-eventgroup-definitions-resource?guid=guid-d68ee0f3-45ca-473a-9d00-bec680117ad9&lang=en-us)，用于部署时按目标 OneFS 运行时目录复核符号代码。PowerScale 严重级别可由设备环境配置，因此目录默认值允许为空，并以事件实例值为准。

## 时间关联建议（不改变审核语义）

Dell 的 [SRS Brevity 事件清单](https://infohub.delltechnologies.com/en-us/l/powerscale-onefs-advanced-alert-configurations/appendix-b-full-list-of-srs-brevity/)提供的是事件代码与英文摘要，不提供 DiskPulse 的时间窗口或重复判断规则。下面的时间标签是用于规划事件关联的操作性元数据，不是厂商对代码的再次解释；在逐代码官方语义、版本和处置证据补齐前，不得据此把 `pending` 定义改为 `reviewed`。

| 时间标签 | 适用的设备摘要模式 | 关联含义 | 建议窗口（以 `event_time` 为中心） |
| --- | --- | --- | --- |
| `point` 瞬时事实 | `Disk sector error`、`SMART status threshold exceeded`、`unsupported boot disk` | 单次事实；同一对象和代码在采集重试期间只保留一次证据 | 去重 5 分钟；跨事件关联 30 分钟 |
| `start` 开始/进入处理 | `FlexProtect job is in progress`、`Drive Stall ... evaluating the drive's health` | 表示任务或评估已开始，不能当作完成或恢复 | 向后 5 分钟寻找前置故障；向后最多 24 小时等待结束事件 |
| `state` 持续状态 | `write-cache ... is enabled`、`drives ... are not healthy` | 在收到相反状态前保持开放；重复上报更新 `last_evidence_at`，不创建新故障 | 同一对象 24 小时内合并；超过 24 小时重新开启一段状态 |
| `end` 完成/恢复 | `Disk Repair Completed`、`FlexProtect ... preparing to add the drive`（任务阶段结束摘要需运行时确认） | 只能关闭同一对象、同一任务指纹的开放关联，不能单独证明硬件已恢复 | 向前 24 小时匹配 `start`；无匹配时作为独立系统事件 |
| `heartbeat`/`activity` 心跳或运行记录 | `SW_CELOG_HEARTBEAT`、作业阶段开始/结束等符号代码 | 仅用于证明采集或作业活动，不进入重复故障 | 仅做 5 分钟去重，不跨窗口合并 |

### 关联键、时间和边界

1. 关联键至少包含 `storage_cluster_id`、厂商、`event_code`、对象类型和稳定对象 ID；不得只按事件代码或完整日志文本合并。
2. `event_time` 使用设备事件发生时间；缺失或无法解析时，该记录不能参与时间关联。入库和 Incident 计算继续遵守本页既有的 `Asia/Shanghai` 墙上时间与 UTC 转换规则。
3. “向前/向后”窗口只用于候选证据排序和去重，不改变 `fault_log`、`system_activity` 等目录类型，也不把 `pending` 代码变成正式诊断。
4. 收到 `end` 或相反状态时，仅关闭同一关联键的开放时间段；没有 `start`、对象不一致或窗口超时的记录必须保留为独立事件，并在界面标注“未找到匹配的开始事件”。
5. 这些窗口是实现前的默认建议。若采集周期、OneFS 版本或设备运行时目录证明不同的生命周期，应在对应代码定义中增加版本化覆盖值，并记录官方依据；不得静态假设数字代码与符号代码互为开始/结束别名。

`sis.auto.session.change` 表示 ONTAP 后台存储效率会话数发生调整，基础定义将它分为 `system_activity`（系统运行事件），不得解释为性能异常或故障日志。

同一代码在不同 ONTAP/OneFS 版本中的严重级别可能变化；目录用 `version_scope` 记录已核实范围。含义未确认或版本依据不足时继续保留待审核状态。

## 运行时关联与展示

厂商事件采集仍先把设备事实写入 `storage_alerts`。健康分析查询再按 `source + event_code` 解析目录，只将启用且已审核的定义返回为正式关联语义。目录缺失、定义停用或仍待审核时，统一返回“未分类厂商事件”安全说明，不持久化猜测结果。

故障指纹由厂商、事件代码、对象类型和稳定对象 ID 组成，只用于重复事件归组和技术追溯，不代表故障结论。页面默认展示“事件代码 + 中文含义 + 关联类型 + 日志摘要”；管理员从重复故障或系统事件所在行点击“查看日志”，读取具体 `storage_alerts` 记录并显示规范化日志正文、对象、发生时间、目录说明和推荐解决方案。已审核定义展示 `recommended_solution_zh`；待审核定义只展示“暂无可核验官方方案”，不输出候选分类或候选处置。原始指纹仅在日志对话框的可展开“技术关联信息”中保留，原始厂商载荷不由列表、详情或 AI 工具返回。

`asset_mapping_missing` 的中文含义是“资产映射不完整”：事件至少已归属存储集群，但节点、卷、Qtree 或项目的稳定映射链路不完整。已识别稳定节点身份的厂商事件不会产生此缺口。该缺口只限制影响范围定位，不表示事件代码或日志正文缺失，也不影响打开规范化日志。

“重复故障”只统计启用且已审核、关联类型为 `fault_log` 的重复事件。`system_activity`、`performance_anomaly`、`capacity_threshold`、`telemetry_degradation`、`unknown` 和任何待审核定义仍可在“系统事件”中查看，但不能仅因指纹重复就计为设备故障。

派生 Incident 使用两层门禁：启用且已审核的 `fault_log` 只在事件实例为 `critical` 时进入内部 `device_fault` 类别；启用且已审核的非故障类型即使是 `critical` 也不得进入 `device_fault`。缺少定义、待审核或停用定义的 `critical` 事件可保守进入处置队列，但用户可见类别必须表述为“设备健康风险”，关联类型继续保持 `unknown`，不得宣称已确认设备故障。

## 管理入口、接口与权限

超级管理员从“系统管理”的“事件与审计”分区进入“厂商事件关联目录” `/admin/vendor-event-definitions`，可以按存储类型、关联类型、审核状态和关键字查询，并新增、修改、删除、启停定义。目录列表与编辑表单展示推荐解决方案；已审核记录保存时必须填写该字段。写入字段均由服务端枚举、长度和 URL 约束校验，所有变更写入统一操作审计。

管理接口使用完整路径：

| 操作 | 接口 |
| --- | --- |
| 分页查询 | `GET /storage-pulse/api/admin/vendor-event-definitions` |
| 查看单条 | `GET /storage-pulse/api/admin/vendor-event-definitions/{id}` |
| 创建定义 | `POST /storage-pulse/api/admin/vendor-event-definitions` |
| 部分修改定义 | `PATCH /storage-pulse/api/admin/vendor-event-definitions/{id}` |
| 删除定义 | `DELETE /storage-pulse/api/admin/vendor-event-definitions/{id}` |
| 发现已有事件代码并执行兼容修复 | `POST /storage-pulse/api/admin/vendor-event-definitions/discover` |

上述接口和存储集群健康分析只允许超级管理员调用。具备项目权限的普通用户只能通过 Incident 详情或诊断看到启用且已审核定义的安全摘要；待审核目录、审计字段和维护操作均不对其开放。

## 发现、历史修复与部署

“发现已有代码”是升级后由超级管理员人工执行一次的历史补录，不是周期任务。内置的 730 条目录由独立初始化脚本负责；Discover 只对现有 NetApp/Isilon `storage_alerts.related_info.event_code` 做数据库端 `DISTINCT` 提取，不读取完整原始载荷，也不连接存储设备主动枚举代码。未收录代码只创建 `unknown + pending` 占位，只在管理目录中待审核。

该动作同时执行幂等的历史 Incident 兼容修复：只由非 `critical` 厂商事件错误生成的旧 `device_fault` Incident 标记为已解决并追加 `reconciled` 时间线；原始 `storage_alerts`、证据和诊断记录全部保留。重复执行可用于故障后重试，但不会重复创建占位项、关闭 Incident 或写入时间线。

迁移 revision `000000000016` 只创建目录表、索引和约束；`000000000017` 只增加推荐方案字段并收紧已审核证据约束；`000000000018` 作为已发布 revision 的兼容标记保留，不写目录数据。部署统一运行 `python backend/scripts/initialize_vendor_event_definitions.py`：命令先升级 Alembic 至 `head`，再按 `(storage_type, event_code)` 插入缺失定义；已有同键记录、管理员新增记录和 `storage_alerts` 原始厂商事件都不会被更新或删除。重复执行只会报告已有数量，不重复插入。自动化验证使用隔离数据库；真实设备运行时目录、版本差异和权限仍需在隔离环境验收。
