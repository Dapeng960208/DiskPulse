# 存储集群

`StorageCluster` 是 NetApp、PowerScale 等存储系统的连接与采集边界。容量池、存储空间、Qtree（NetApp）、项目组和用户目录均关联到具体集群。

## API 与连接边界

核心接口位于 `/storage-pulse/api/storage-clusters`，支持集群列表、创建、详情、更新、删除和实时趋势。设备协议由集群的 `protocol` 决定，`tls_verify` 只适用于 HTTPS；HTTP 仅应在可信隔离网络中使用。

容量类资源响应在保留原始 GB 数值兼容字段的同时，使用 `capacity.{field}={ value, unit }` 明确显示单位。容量池、存储空间、Qtree、项目、项目组和集群实时容量曲线使用 `data_unit=TB`；树节点的容量和当前值分别以 `capacity_unit`、`value_unit` 标识，避免把利用率与容量混淆。

创建、启用或更新已启用集群后会异步触发采集，保存请求不等待设备响应。采集失败保留已有资源数据并记录安全诊断日志，不输出设备地址、账号或密码。

前端入口位于“系统管理 → 存储集群”。“存储集群”是无页面组件的菜单分组，二级栏目为“集群列表、容量池、存储空间、Qtree（NetApp）”；现有 `/admin/storage-clusters`、`/admin/aggregates`、`/admin/volumes`、`/admin/qtrees` 以及各详情深链均保持不变。

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
| [健康分析](./health-analytics.md) | 容量变化、性能、故障和导出。 |
| [性能与事件排障](../../../guides/storage/performance-event-troubleshooting.md) | 部署前检查、排障和真机验收。 |

字段、迁移和版本链以当前代码和迁移目录为准；不得手工伪造数据库版本或依赖历史 revision 编号。
