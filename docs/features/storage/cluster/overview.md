# 存储集群

`StorageCluster` 是 NetApp、PowerScale 等存储系统的连接与采集边界。容量池、存储空间、Qtree（NetApp）、项目组和用户目录均关联到具体集群。

## API 与连接边界

核心接口位于 `/storage-pulse/api/storage-clusters`，支持集群列表、创建、详情、更新、删除和实时趋势。设备协议由集群的 `protocol` 决定，`tls_verify` 只适用于 HTTPS；HTTP 仅应在可信隔离网络中使用。

## 容量查询利用率筛选

所有返回当前容量对象集合的查询均支持可选的 `use_ratio_min` 与 `use_ratio_max`。两者使用 0--100 的百分比口径并按闭区间筛选；省略任一边界时不限制该边界，最小值大于最大值或任一值超出范围时返回 `422`。现有认证、项目隔离、名称筛选、资源归属筛选、排序和分页语义保持不变。

- 分页资源列表：`GET /storage-clusters/`、`/aggregates/`、`/volumes/`、`/qtrees/`、`/groups/`、`/storage-usages/` 和 `/projects/`。
- 容量集合及导出：`GET /storage-usages/export/`、`/dashboard/capacity-items`、`/aggregates/storage-trees/`、`/aggregates/{aggregate_id}/storage-tree`、`/projects/storage/summary`、`/projects/storage/groups`、`/projects/{project_id}/storage-tree` 和 `/storage-alerts/`。告警按其 `avg_use_ratio` 筛选，其余接口按当前对象的 `use_ratio` 筛选。

存储树会保留命中节点所需的父级路径，并移除不命中的叶节点；因此作为结构上下文保留的父节点可能不在指定区间。单资源详情、实时或历史趋势、Dashboard 汇总/趋势/Top 用户、遥测运行记录以及容量预测不提供这些参数：它们返回单一对象、时间序列、汇总值或不含当前利用率，不能把区间筛选伪造成同一语义。

容量类资源响应、实时曲线和容量树遵守[容量单位 API 契约](../../../standards/backend/capacity-unit-contract.md)，避免把利用率与容量混淆。

创建、启用或更新已启用集群后会异步触发采集，保存请求不等待设备响应。采集失败保留已有资源数据并记录安全诊断日志，不输出设备地址、账号或密码。

前端入口位于“系统管理 → 存储集群”，该菜单直接打开集群列表，不再展开“集群列表、容量池、存储空间、Qtree（NetApp）”三级栏目。现有 `/admin/storage-clusters`、`/admin/aggregates`、`/admin/volumes`、`/admin/qtrees` 以及各详情深链均保持不变；后三个独立列表路由改为隐藏入口，仍可由既有链接访问。集群详情页按需加载当前集群范围的“容量池”“存储空间”和“Qtree（NetApp）”资源表；资源表使用 `QueryForm` 名称筛选，Qtree 额外可按所属存储空间筛选。详情页的资源、性能和事件表统一使用共享 `DataTable`；表格只在内容区滚动，窄宽度会隐藏次要容量列以避免页面横向滚动，底部分页始终可达。Isilon 集群不显示且不请求 Qtree。

集群详情提供仅超级管理员可见的“耗尽风险”页签，具体预测和分级口径见[四维容量耗尽风险](../../ai/capacity-prediction/overview.md)。

## PowerScale 会话与权限

PowerScale 集群可选择不缓存、本地文件或 Redis Session 缓存。数据库不保存 Cookie；缓存读取或写入失败时安全注销 OneFS Session。含认证材料的文件和 Redis 必须由部署环境限制访问。

采集使用 System Zone 的 OneFS 本地服务账号和最小权限角色，不使用个人 NIS、LDAP 或 AD 账号。读取集群、容量池、配额、性能和系统事件需要相应只读权限；调整目录或用户配额额外需要 Quota 与 Quota Management 写权限。逐 Directory Quota 延迟要求 OneFS 以 `path` 作为性能识别维度并固定需要监控的路径，不能把节点总延迟推算为目录延迟。

## 采集与用户快照

- 全量存储采集按既有调度更新设备数据、PostgreSQL 当前态和 QuestDB 明细。
- 用户小时快照按非空 `user_id` 汇总当前 `StorageUsage`，独立写入 `user_storage_usages`；空数据是成功空结果，QuestDB 提交失败必须作为任务失败处理。
- 两类任务使用独立数据库会话和 Redis 非阻塞锁，互不改变对方的事务结果。

## 关联文档

| 文档 | 说明 |
| --- | --- |
| [资源映射](./resource-mapping.md) | NetApp/PowerScale 统一术语、采集映射和项目组绑定。 |
| [厂商契约](./vendor-api-contracts.md) | 设备接口、字段映射和 DiskPulse 分析 API。 |
| [性能与事件](./performance-event-collection.md) | 性能与厂商事件采集的数据流。 |
| [健康分析](./health-analytics.md) | 容量变化、性能、厂商事件语义、故障日志和导出。 |
| [厂商事件关联](../event-association/overview.md) | NetApp/PowerScale 事件代码、中文含义、关联类型和管理入口。 |
| [性能与事件排障](../../../guides/storage/performance-event-troubleshooting.md) | 部署前检查、排障和真机验收。 |

字段、迁移和版本链以当前代码和迁移目录为准；不得手工伪造数据库版本或依赖历史 revision 编号。
