# 存储集群健康分析

## 目标与入口

存储集群详情用于查看当前集群的存储分布，以及在一个时间范围内查看已用容量变化、按严重级别汇总的错误、存储空间性能指标和重复设备故障，并按需导出健康分析结果。

入口只保留在“系统管理 → 存储集群”列表最后一列的“详情”按钮，不再提供独立“存储健康”或“存储一览”菜单和集群选择器。页签顺序为“容量趋势”“存储分布”“容量池”“存储空间”“Qtree（NetApp）”“性能分析”“故障分析”“关联事件”；存储分布、资源表、性能、故障和关联事件数据在相应页签首次打开时加载，普通页签往返复用已加载数据。容量、性能和故障分析共用页面时间范围，筛选工具栏分别位于对应页签内容区的顶部；存储分布不使用时间范围或健康报告导出，关联事件在自身页签内按状态和事件类型筛选。存储分布以页签内容区全高渲染。详情页内的资源、性能、重复故障、系统事件和关联事件列表统一使用共享 `DataTable`，不在页面内覆盖表格或分页样式；窄宽度隐藏次要列，避免页面横向滚动。页面不重复展示集群名称、描述、API 用户名、端口和 TLS 等集群配置字段。

## 数据来源与统计口径

| 能力 | 数据来源 | 统计口径 |
| --- | --- | --- |
| 存储分布 | PostgreSQL 中当前集群的存储资源 | 按当前 `storage_cluster_id` 返回存储空间/Qtree（NetApp）容量树；不使用健康分析时间范围。 |
| 容量变化 | QuestDB `storage_cluster_storage_usages` | 所选范围最后一个已用容量减去第一个已用容量；期初为零时变化率为 `null`。 |
| 严重级别统计 | PostgreSQL `storage_alerts` | 仅统计可归属当前集群的 NetApp/Isilon 原生事件，按 `critical`、`error`、`warning`、`info` 汇总；与系统事件表保持同一来源和时间范围。 |
| 存储空间性能 | QuestDB `storage_performance_metrics` | 按 P95 延迟降序返回最多 100 个已关联存储空间，页面可选择 10、20、50、100 条；返回 P95、平均、最大、读、写延迟，以及平均 IOPS、平均吞吐量和样本数。NetApp 使用 Volume UUID；PowerScale 使用已固定的 path workload，并映射为对应 Directory Quota quota ID。 |
| 重复故障 | PostgreSQL `storage_alerts` + `vendor_event_definitions` | 仅统计 `source=netapp` 或 `source=isilon`、目录定义已启用且已审核、关联类型为 `fault_log` 的设备事件；同一 `fingerprint` 在所选范围出现至少两次时计为重复故障。返回事件代码、中文含义、日志摘要和可打开的示例事件 ID，不把指纹本身当作故障结论。 |
| 系统事件 | PostgreSQL `storage_alerts` + `vendor_event_definitions` | 按当前集群、时间范围、关键字和日志等级查询 NetApp/Isilon 原生事件；数据库分页默认每页 20 条，并关联事件类型、中文标题和说明。目录缺失、停用或待审核时统一显示“未分类厂商事件”；待审核候选内容只留在管理目录。 |

DiskPulse 既有容量告警使用 `source=diskpulse`，严重级别映射为 `high→critical`、`medium→warning`、`low→info`。原“告警”页面只查询 `source=diskpulse`，NetApp/Isilon 原生事件归类为“系统事件”并仅在存储健康中展示，不再与容量、周报或扩容记录混排。严重级别统计、重复故障和系统事件都只接受 `netapp`、`isilon` 来源；其他来源即使写入 `storage_alerts` 也不进入故障分析。无法唯一归属到存储集群的项目级容量告警保留在原告警范围内，不进入集群健康分析。

设备事件指纹由厂商、事件代码、对象类型和对象 ID 组成，不使用可能包含动态内容的完整消息。指纹只是稳定的重复归组键，不能单独推断系统问题。页面仅使用[厂商事件关联目录](../event-association/overview.md)中已启用且已审核的“事件代码 + 中文含义 + 关联类型 + 日志摘要 + 推荐解决方案”作为正式信息；其他定义按未分类处理。系统事件列表直接展示事件代码、中文含义和单个关联类型标签，不在关联类型列重复展示审核状态；鼠标悬浮关联类型时展示关联说明与建议措施。管理员点击重复故障或系统事件后读取具体事件详情，查看规范化日志正文、对象、发生时间、审核状态和推荐解决方案；待审核项固定显示“暂无可核验官方方案”，不输出候选诊断结论。原始厂商载荷不由详情接口返回。

NetApp 事件来自 ONTAP EMS，性能来自 Volume `metric`。ONTAP 返回的 Volume 总、读、写延迟以微秒为单位，采集器统一除以 `1000` 转为毫秒后写入 QuestDB；`iops.total` 和 `throughput.total` 分别按 IOPS、B/s 写入统一字段。字段名必须使用 ONTAP REST 返回的单数 `metric`，请求不存在的 `metrics` 会返回 `400`。

PowerScale 事件来自 event group/list。逐存储空间性能先通过 `/platform/latest` 发现资源版本，再从 `/{version}/performance/datasets` 选择包含 `path` 识别维度的 dataset，读取 `/{version}/performance/datasets/{id}/workloads` 建立 workload ID 到完整路径的映射，最后使用 dataset 的 `statkey` 请求 `/{version}/statistics/current`。每条 workload 的 `latency_read`、`latency_write` 和 `latency_other` 按 `sum/count` 求平均，OneFS 该计数使用微秒口径，写入 QuestDB 前统一除以 `1000` 转为毫秒；综合延迟使用三类请求的加权平均，`protocol_ops`（兼容 `ops`）映射到 IOPS，`bytes_in + bytes_out` 映射到吞吐量，`time` Unix 时间戳作为设备采集时间。不能用节点磁盘延迟替代目录延迟，也不能按容量或 IOPS 推算未返回路径的延迟。

容量采集会把 NetApp Volume UUID、PowerScale Directory Quota ID（设备未返回 ID 时使用 quota 路径）写入 PostgreSQL `Volume.performance_object_id`。性能采集只为当前集群中已存在该稳定身份的 `Volume` 写入 `object_type=volume` 样本；PowerScale workload 仍以完整路径匹配 Directory Quota，但 QuestDB `object_id` 统一写入关联后的 quota ID，`object_name` 保留路径用于展示。父目录、节点指标和其他未关联 workload 即使存在性能数据，也不会误标成 DiskPulse Volume。

存储集群性能分析和存储空间性能监控都按同一个 `Volume.performance_object_id` 查询。缺少稳定身份或采集记录无法关联时不做名称猜测，对应卷性能返回空数据；容量趋势仍可独立展示。部署迁移后需要先成功执行一次容量采集，现有 `Volume` 才会补齐厂商身份。

OneFS event list 外层记录中的 `events[]` 按单条设备事件展开；event group 使用 `last_event`（缺失时使用 `time_noticed`）作为发生时间，并从 `causes` 取得事件代码和描述。OneFS 整数 Unix 时间戳统一换算为 DiskPulse 应用时区 `Asia/Shanghai` 的 naive 墙上时间后入库，不跟随 worker 或 CI runner 的操作系统时区。

“事件对象”表示厂商事件关联的节点，而不是日志正文摘要。NetApp EMS 的原始对象 ID 通常是 ONTAP 节点 UUID，看起来像哈希但实际是设备提供的稳定节点标识；页面优先从原始事件的 `node.name` 显示节点名称，名称缺失时才回退 UUID。Isilon/PowerScale 的数字来自 OneFS 事件 `devid`（或 `specifier.devid`），表示事件所属节点/设备编号，页面显示为“节点 N”。原始 ID 仅在有明确排障用途的技术信息中保留，便于与厂商日志核对。

## 采集与保留边界

- 设备事件每分钟采集；首次回看 24 小时，之后回看最近 5 分钟，并按厂商事件 ID 去重。
- `storage_alerts.updated_at` 沿用 DiskPulse 应用时区 `Asia/Shanghai` 的 naive 墙上时间口径；厂商事件携带时区时先显式换算到该时区再去除时区信息，不能使用无参数 `astimezone()` 或 `datetime.fromtimestamp()` 隐式继承宿主机时区。派生 Incident 前必须把该墙上时间按 `Asia/Shanghai` 解释并转换为 UTC，不能直接附加 UTC 时区，否则事件中心会多显示 8 小时。NetApp 增量查询的 `since` 单独换算为 UTC `Z` 格式，不能据此把事件入库时间描述为 UTC。
- 性能指标每 5 分钟采集，从功能启用后开始累计，不回灌设备历史性能。
- `storage_performance_metrics` 保留 180 天；所有分析查询和导出时间范围最多 180 天。
- 本功能不新增 `storage_alerts` 清理任务，其既有历史数据仍按系统原有策略保留，但超过 180 天不能通过健康分析接口查询。
- 单个集群采集失败只记录服务端日志，不影响其他集群，也不写入虚构的零值。

## API

下列完整接口路径均要求有效的 `Authorization: Bearer <token>`。本功能沿用存储集群详情的登录用户访问边界，不新增权限或角色。

| 能力 | 路径 |
| --- | --- |
| 存储分布 | `GET /storage-pulse/api/aggregates/storage-trees/?storage_cluster_id={storage_cluster_id}` |
| 容量变化 | `GET /storage-pulse/api/storage-clusters/{storage_cluster_id}/analytics/capacity-change` |
| 严重级别统计 | `GET /storage-pulse/api/storage-clusters/{storage_cluster_id}/analytics/error-severity` |
| 存储空间性能 | `GET /storage-pulse/api/storage-clusters/{storage_cluster_id}/analytics/top-latency` |
| 重复故障 | `GET /storage-pulse/api/storage-clusters/{storage_cluster_id}/analytics/repeated-faults` |
| 系统事件 | `GET /storage-pulse/api/storage-clusters/{storage_cluster_id}/analytics/system-events` |
| 系统事件详情 | `GET /storage-pulse/api/storage-clusters/{storage_cluster_id}/analytics/system-events/{event_id}` |
| 导出 | `GET /storage-pulse/api/storage-clusters/{storage_cluster_id}/analytics/export` |

除存储分布外，所有健康分析列表接口要求 `start_time` 和 `end_time`，开始时间必须早于结束时间，范围不得超过 180 天。性能接口支持对象类型和 `limit` 参数，数量默认 10、最多 100；页面提供 10、20、50、100 四档，并可多选 P95、平均、最大、读、写延迟、IOPS 和吞吐量，默认只选 P95。页面还提供“对象”多选，用于在当前已返回的 Top-N 存储空间内本地对比；未选对象时显示全部返回结果，选择对象后图表与表格同步收窄，不增加接口参数或跨 Top-N 查询。性能图对长对象名截断横轴标签并保留悬停提示，图表标题与标签区域保留独立空间。系统事件接口支持 `keyword`（事件代码、对象标识/名称或内容）、`severity=critical|error|warning|info`、`page` 和 `page_size`；默认 `page=1&page_size=20`，单页最多 100 条，返回 `data`、`total`、`page`、`page_size`。过滤条件在数据库分页和 `total` 统计前生效。事件详情接口同时校验事件属于路径中的集群，并只返回规范化日志和关联目录的安全字段。无数据时返回空集合和可空汇总值，不把无数据表示成故障。

容量变化接口遵守[容量单位 API 契约](../../../standards/backend/capacity-unit-contract.md)中的存储集群健康分析单位规则。

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

自动化验证覆盖厂商响应解析、PowerScale 资源版本、path dataset、workload 映射、延迟/IOPS/吞吐量统一映射、NetApp 延迟单位和嵌套指标转换、性能条数上限、多指标与本地多对象筛选、图表长横轴标签布局、`Asia/Shanghai` 事件时间与 UTC `since` 的宿主机时区无关转换、派生 Incident 的 UTC 转换、来源白名单、严重级别映射、事件去重、只有已启用且已审核目录影响业务、未知/待审核代码回退、重复故障分类过滤、系统事件先过滤后分页、事件详情、可读事件对象、统计口径、180 天参数校验、导出摘要与公式转义，以及前端搜索、翻页、空态和不支持状态。

真实 NetApp、PowerScale、PostgreSQL、MySQL、QuestDB 和登录浏览器的冒烟仍需在部署环境执行，重点确认设备权限、实际资源版本、事件字段、对象名称、延迟单位、指标可用性、QuestDB TTL、数据库迁移和浏览器下载行为。在这些验证完成前，不能把外部系统兼容性描述为已验证。

## 派生预测与关联事件

集群详情新增懒加载“关联事件”页签。该页签只读取项目作用域内的派生 Incident、容量预测数和性能异常数；打开后才请求 `GET /storage-pulse/api/v1/incidents`、`GET /storage-pulse/api/v1/forecasts` 和 `GET /storage-pulse/api/v1/anomalies`。关联事件列表可按状态和事件类型筛选。点击事件可查看不可变证据引用、确定性诊断与操作时间线。详情抽屉标题和“事件主题”明确区分容量告警、容量预测、系统故障事件、性能异常和监控异常；每条证据直接展示“关联类型”和“关联内容”。只有已明确关联为 `fault_log` 的厂商证据称为“系统故障事件”，未分类的严重厂商事件继续显示“设备健康风险”。历史时间线中泛化的“关联事件证据”说明按当前 Incident 主题改为可读摘要，并引导查看上方明确的证据类型、内容和影响范围。

该页签不改变本页的“故障分析”与“系统事件”语义：厂商原始事件仍来自 `storage_alerts` 的 `netapp`/`isilon` 记录，既有告警页仍只显示 `source=diskpulse`。派生分析侧的 `asset_mapping_missing` 显示为“资产映射不完整”，表示事件至少已归属集群，但节点/卷/Qtree/项目的稳定映射链路不完整；已有稳定节点身份的厂商事件不产生该缺口。它不会修改或隐藏厂商原始记录，也不表示事件代码或日志缺失。

## Dell 官方参考

- [Performance datasets API resource](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference/performance-datasets-resource?guid=guid-f036e2e1-edff-43a6-b422-c27b6fe9d938&lang=en-us)
- [查看 dataset workload 统计](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_administration_guide_cli/view-statistics?guid=guid-e5c06c8f-3d35-4374-b2fb-4e0cfac1fd38&lang=en-us)
- [固定 performance workload](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs-pub-91100-cli-command-reference/isi-performance-workloads-pin?guid=guid-4b577f82-c008-49b9-b81a-fa5a74bf681d&lang=en-us)
