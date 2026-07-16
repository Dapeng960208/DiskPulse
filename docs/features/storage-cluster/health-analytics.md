# 存储集群健康分析

## 目标与入口

存储集群详情用于查看当前集群的存储分布，以及在一个时间范围内查看已用容量变化、按严重级别汇总的错误、存储空间性能指标和重复设备故障，并按需导出健康分析结果。

入口只保留在“系统管理 → 存储集群”列表最后一列的“详情”按钮，不再提供独立“存储健康”或“存储一览”菜单和集群选择器。页签顺序为“容量趋势”“存储分布”“性能分析”“故障分析”；存储分布、性能和故障数据在相应页签首次打开时加载，普通页签往返复用已加载数据。容量、性能和故障分析共用页面时间范围；存储分布展示当前容量树，不使用时间范围或健康报告导出，因此打开该页签时隐藏筛选工具栏。页面不重复展示集群名称、描述、API 用户名、端口和 TLS 等集群配置字段。

## 数据来源与统计口径

| 能力 | 数据来源 | 统计口径 |
| --- | --- | --- |
| 存储分布 | PostgreSQL 中当前集群的存储资源 | 按当前 `storage_cluster_id` 返回存储空间/Qtree（NetApp）容量树；不使用健康分析时间范围。 |
| 容量变化 | QuestDB `storage_cluster_storage_usages` | 所选范围最后一个已用容量减去第一个已用容量；期初为零时变化率为 `null`。 |
| 严重级别统计 | PostgreSQL `storage_alerts` | 合并可归属当前集群的 DiskPulse 容量告警与 NetApp/Isilon 设备事件，按 `critical`、`error`、`warning`、`info` 汇总。 |
| 存储空间性能 | QuestDB `storage_performance_metrics` | 按 P95 延迟降序返回最多 100 个存储空间，页面可选择 10、20、50、100 条；返回 P95、平均、最大、读、写延迟，以及平均 IOPS、平均吞吐量和样本数。NetApp 使用 Volume；PowerScale 使用已固定的 path workload，并映射为对应 Directory Quota 路径。 |
| 重复故障 | PostgreSQL `storage_alerts` | 仅统计 `source=netapp` 或 `source=isilon` 的设备事件；同一 `fingerprint` 在所选范围出现至少两次时计为重复故障。 |
| 系统事件 | PostgreSQL `storage_alerts` | 按当前集群、时间范围、关键字和日志等级查询 NetApp/Isilon 原生事件；数据库分页默认每页 20 条，包含来源、严重级别、事件代码、事件对象、内容和发生时间。 |

DiskPulse 既有容量告警使用 `source=diskpulse`，严重级别映射为 `high→critical`、`medium→warning`、`low→info`。原“告警”页面只查询 `source=diskpulse`，NetApp/Isilon 原生事件归类为“系统事件”并仅在存储健康中展示，不再与容量、周报或扩容记录混排。严重级别统计只接受 `diskpulse`、`netapp`、`isilon` 来源，重复故障和系统事件只接受 `netapp`、`isilon`；其他来源即使写入 `storage_alerts` 也不进入对应分析。无法唯一归属到存储集群的项目级容量告警保留在原告警范围内，不进入集群健康分析。设备故障指纹由厂商、事件代码、对象类型和对象 ID 组成，不使用可能包含动态内容的完整消息。

NetApp 事件来自 ONTAP EMS，性能来自 Volume `metric`。ONTAP 返回的 Volume 总、读、写延迟以微秒为单位，采集器统一除以 `1000` 转为毫秒后写入 QuestDB；`iops.total` 和 `throughput.total` 分别按 IOPS、B/s 写入统一字段。字段名必须使用 ONTAP REST 返回的单数 `metric`，请求不存在的 `metrics` 会返回 `400`。

PowerScale 事件来自 event group/list。逐存储空间性能先通过 `/platform/latest` 发现资源版本，再从 `/{version}/performance/datasets` 选择包含 `path` 识别维度的 dataset，读取 `/{version}/performance/datasets/{id}/workloads` 建立 workload ID 到完整路径的映射，最后使用 dataset 的 `statkey` 请求 `/{version}/statistics/current`。每条 workload 的 `latency_read`、`latency_write` 和 `latency_other` 按 `sum/count` 求平均，OneFS 该计数使用微秒口径，写入 QuestDB 前统一除以 `1000` 转为毫秒；综合延迟使用三类请求的加权平均，`protocol_ops`（兼容 `ops`）映射到 IOPS，`bytes_in + bytes_out` 映射到吞吐量，`time` Unix 时间戳作为设备采集时间。不能用节点磁盘延迟替代目录延迟，也不能按容量或 IOPS 推算未返回路径的延迟。

采集和查询都会用当前集群 PostgreSQL `Volume.name` 校验 workload 路径，仅保留已经同步为 Directory Quota 存储空间的对象。父目录或其他已固定 workload 即使存在性能数据，也不会误标成 DiskPulse Volume；该校验同时屏蔽修复前已写入的错误节点/父路径样本。

OneFS event list 外层记录中的 `events[]` 按单条设备事件展开；event group 使用 `last_event`（缺失时使用 `time_noticed`）作为发生时间，并从 `causes` 取得事件代码和描述。OneFS 整数 Unix 时间戳统一换算为系统本地 naive 时间后入库。

“事件对象”表示厂商事件关联的节点，而不是日志正文摘要。NetApp EMS 的原始对象 ID 通常是 ONTAP 节点 UUID，看起来像哈希但实际是设备提供的稳定节点标识；页面优先从原始事件的 `node.name` 显示节点名称，名称缺失时才回退 UUID。Isilon/PowerScale 的数字来自 OneFS 事件 `devid`（或 `specifier.devid`），表示事件所属节点/设备编号，页面显示为“节点 N”。原始 ID 仍随接口返回，并在页面悬停提示中保留，便于与厂商日志核对。

## 采集与保留边界

- 设备事件每分钟采集；首次回看 24 小时，之后回看最近 5 分钟，并按厂商事件 ID 去重。
- `storage_alerts.updated_at` 沿用系统本地 naive 时间口径；厂商事件携带时区时先换算为系统本地时间再去除时区信息。NetApp 增量查询的 `since` 单独换算为 UTC `Z` 格式，不能据此把事件入库时间描述为 UTC。
- 性能指标每 5 分钟采集，从功能启用后开始累计，不回灌设备历史性能。
- `storage_performance_metrics` 保留 180 天；所有分析查询和导出时间范围最多 180 天。
- 本功能不新增 `storage_alerts` 清理任务，其既有历史数据仍按系统原有策略保留，但超过 180 天不能通过健康分析接口查询。
- 单个集群采集失败只记录服务端日志，不影响其他集群，也不写入虚构的零值。

## API

接口统一挂载在 `/storage-pulse/api`，并要求有效的 `Authorization: Bearer <token>`。本功能沿用存储集群详情的登录用户访问边界，不新增权限或角色。

| 能力 | 路径 |
| --- | --- |
| 存储分布 | `GET /aggregates/storage-trees/?storage_cluster_id={storage_cluster_id}` |
| 容量变化 | `GET /storage-clusters/{storage_cluster_id}/analytics/capacity-change` |
| 严重级别统计 | `GET /storage-clusters/{storage_cluster_id}/analytics/error-severity` |
| 存储空间性能 | `GET /storage-clusters/{storage_cluster_id}/analytics/top-latency` |
| 重复故障 | `GET /storage-clusters/{storage_cluster_id}/analytics/repeated-faults` |
| 系统事件 | `GET /storage-clusters/{storage_cluster_id}/analytics/system-events` |
| 导出 | `GET /storage-clusters/{storage_cluster_id}/analytics/export` |

除存储分布外，所有健康分析接口要求 `start_time` 和 `end_time`，开始时间必须早于结束时间，范围不得超过 180 天。性能接口支持对象类型和 `limit` 参数，数量默认 10、最多 100；页面提供 10、20、50、100 四档，并可多选 P95、平均、最大、读、写延迟、IOPS 和吞吐量，默认只选 P95。系统事件接口支持 `keyword`（事件代码、对象标识/名称或内容）、`severity=critical|error|warning|info`、`page` 和 `page_size`；默认 `page=1&page_size=20`，单页最多 100 条，返回 `data`、`total`、`page`、`page_size`。过滤条件在数据库分页和 `total` 统计前生效。无数据时返回空集合和可空汇总值，不把无数据表示成故障。

导出接口接受：

```text
format=csv|excel|pdf
section=capacity|severity|latency|faults|all
```

- 导出当前板块时，CSV、Excel、PDF 均直接下载。
- `section=all&format=excel` 返回包含四个工作表的 Excel。
- `section=all&format=pdf` 返回包含四个章节的 PDF。
- `section=all&format=csv` 返回包含四个 CSV 的 ZIP。
- 容量导出包含期初、期末、变化量和变化率摘要；严重级别导出包含总数和按来源拆分，避免导出结果只保留图表明细。
- CSV 使用 UTF-8 BOM；CSV 和 Excel 会忽略前导空格、制表符、回车和换行检查设备文本，检测到首个有效字符为 `=`、`+`、`-`、`@` 时给原文本添加单引号前缀，防止表格软件将设备名称或故障消息解释为公式。
- 页面容量、性能页签分别把当前页映射为 `capacity`、`latency`；故障页签可分别导出 `severity` 和 `faults`，三个页签都可导出 `all` 完整报告。
- 页面查询和导出调用同一分析服务，统计口径保持一致；本版本不归档报告，也不定时发送报告邮件。

## 降级与不支持状态

- PowerScale 必须存在包含 `path` 的 performance dataset；每个需要展示的 Directory Quota 路径必须固定为 workload。缺失 dataset 或未固定路径时不降级为节点延迟，避免把节点指标误标为“卷延迟”。
- NetApp 或 PowerScale 从未成功写入性能指标时，性能接口返回 `supported=false` 和空数据；页面提示检查采集任务和设备 API 权限，不把“未采集”误写为“设备不支持”或零延迟。
- PowerScale 采集账号必须能够登录 OneFS `platform` 服务，并具备 `ISI_PRIV_STATISTICS`、`ISI_PRIV_PERFORMANCE` 和事件只读权限；登录或接口返回 `401/403` 时不会生成虚构的空告警或零指标。
- 设备响应缺少可识别事件 ID、时间或严重级别时，不将该响应计入健康分析，并在服务端保留不含凭据的诊断日志。
- 时间范围内没有容量采样、告警或事件时，相应板块显示带时间范围和采集权限提示的空态，其他板块仍可正常使用。

## 测试与验证边界

自动化验证覆盖厂商响应解析、PowerScale 资源版本、path dataset、workload 映射、延迟/IOPS/吞吐量统一映射、NetApp 延迟单位和嵌套指标转换、性能条数上限与多指标筛选、系统本地事件时间与 UTC `since`、来源白名单、严重级别映射、事件去重、系统事件先过滤后分页、可读事件对象、统计口径、180 天参数校验、导出摘要与公式转义，以及前端搜索、翻页、空态和不支持状态。

真实 NetApp、PowerScale、PostgreSQL、MySQL、QuestDB 和登录浏览器的冒烟仍需在部署环境执行，重点确认设备权限、实际资源版本、事件字段、对象名称、延迟单位、指标可用性、QuestDB TTL、数据库迁移和浏览器下载行为。在这些验证完成前，不能把外部系统兼容性描述为已验证。

## Dell 官方参考

- [Performance datasets API resource](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference/performance-datasets-resource?guid=guid-f036e2e1-edff-43a6-b422-c27b6fe9d938&lang=en-us)
- [查看 dataset workload 统计](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_administration_guide_cli/view-statistics?guid=guid-e5c06c8f-3d35-4374-b2fb-4e0cfac1fd38&lang=en-us)
- [固定 performance workload](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs-pub-91100-cli-command-reference/isi-performance-workloads-pin?guid=guid-4b577f82-c008-49b9-b81a-fa5a74bf681d&lang=en-us)
