# 存储集群健康分析

## 目标与入口

存储集群健康分析用于在一个时间范围内查看已用容量变化、按严重级别汇总的错误、Top 10 高延迟对象和重复设备故障，并按需导出结果。

所有登录用户可从一级菜单“存储健康”选择集群查看；管理员仍可从“系统管理 → 存储集群 → 存储集群详情”进入同一分析页。容量、性能和故障分析共用页面时间范围；性能和故障数据在相应页签首次打开时加载。业务入口不展示 API 用户名、端口和 TLS 等管理字段。

## 数据来源与统计口径

| 能力 | 数据来源 | 统计口径 |
| --- | --- | --- |
| 容量变化 | QuestDB `storage_cluster_storage_usages` | 所选范围最后一个已用容量减去第一个已用容量；期初为零时变化率为 `null`。 |
| 严重级别统计 | PostgreSQL `storage_alerts` | 合并可归属当前集群的 DiskPulse 容量告警与 NetApp/Isilon 设备事件，按 `critical`、`error`、`warning`、`info` 汇总。 |
| Top 10 高延迟对象 | QuestDB `storage_performance_metrics` | 按 P95 延迟降序返回最多 10 个对象，同时返回平均值、最大值和样本数。NetApp 使用 Volume；PowerScale 优先使用 workload，缺失时降级为节点。 |
| 重复故障 | PostgreSQL `storage_alerts` | 仅统计 `source=netapp` 或 `source=isilon` 的设备事件；同一 `fingerprint` 在所选范围出现至少两次时计为重复故障。 |
| 系统事件 | PostgreSQL `storage_alerts` | 展示当前集群和时间范围内最近 100 条 NetApp/Isilon 原生事件，包含来源、严重级别、事件代码、对象、内容和发生时间。 |

DiskPulse 既有容量告警使用 `source=diskpulse`，严重级别映射为 `high→critical`、`medium→warning`、`low→info`。原“告警”页面只查询 `source=diskpulse`，NetApp/Isilon 原生事件归类为“系统事件”并仅在存储健康中展示，不再与容量、周报或扩容记录混排。严重级别统计只接受 `diskpulse`、`netapp`、`isilon` 来源，重复故障和系统事件只接受 `netapp`、`isilon`；其他来源即使写入 `storage_alerts` 也不进入对应分析。无法唯一归属到存储集群的项目级容量告警保留在原告警范围内，不进入集群健康分析。设备故障指纹由厂商、事件代码、对象类型和对象 ID 组成，不使用可能包含动态内容的完整消息。

NetApp 事件来自 ONTAP EMS，性能来自集群和 Volume metrics。ONTAP 返回的 Volume 总、读、写延迟以微秒为单位，采集器统一除以 `1000` 转为毫秒后写入 QuestDB，Top 10、页面和导出均使用毫秒口径。

PowerScale 事件来自 event group/list，性能来自 statistics API。客户端先通过 `/platform/latest` 发现资源版本，再读取 `/{version}/statistics/keys`：优先选择包含 workload 的延迟键，没有时选择节点延迟键，最后使用所选键请求 `/{version}/statistics/current`。统计键的 `units`/`unit` 元数据会传递给采集器；微秒转换为毫秒，毫秒原样保留，单位缺失或无法识别时跳过该指标。不能把 OneFS 主版本直接作为 API 资源版本，也不能根据键名臆造返回对象维度。

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
| 容量变化 | `GET /storage-clusters/{storage_cluster_id}/analytics/capacity-change` |
| 严重级别统计 | `GET /storage-clusters/{storage_cluster_id}/analytics/error-severity` |
| Top 10 高延迟对象 | `GET /storage-clusters/{storage_cluster_id}/analytics/top-latency` |
| 重复故障 | `GET /storage-clusters/{storage_cluster_id}/analytics/repeated-faults` |
| 系统事件 | `GET /storage-clusters/{storage_cluster_id}/analytics/system-events` |
| 导出 | `GET /storage-clusters/{storage_cluster_id}/analytics/export` |

所有接口要求 `start_time` 和 `end_time`，开始时间必须早于结束时间，范围不得超过 180 天。Top 10 接口支持对象类型和数量参数，数量默认且最多为 10；系统事件接口的 `limit` 默认为 100、最多为 200。无数据时返回空集合和可空汇总值，不把无数据表示成故障。

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

- PowerScale 没有 workload 延迟指标时自动尝试节点延迟指标。
- NetApp 或 PowerScale 完全没有可用延迟指标时，性能接口返回 `supported=false` 和空数据，页面显示“不支持性能分析”，不得展示零延迟。
- 设备响应缺少可识别事件 ID、时间或严重级别时，不将该响应计入健康分析，并在服务端保留不含凭据的诊断日志。
- 时间范围内没有容量采样、告警或事件时，相应板块显示空态，其他板块仍可正常使用。

## 测试与验证边界

自动化验证覆盖厂商响应解析、PowerScale 资源版本/统计键/单位发现、NetApp 延迟单位转换、系统本地事件时间与 UTC `since`、来源白名单、严重级别映射、事件去重、统计口径、180 天参数校验、导出摘要与公式转义，以及前端空态/不支持状态。

真实 NetApp、PowerScale、PostgreSQL、MySQL、QuestDB 和登录浏览器的冒烟仍需在部署环境执行，重点确认设备权限、实际资源版本、事件字段、对象名称、延迟单位、指标可用性、QuestDB TTL、数据库迁移和浏览器下载行为。在这些验证完成前，不能把外部系统兼容性描述为已验证。
