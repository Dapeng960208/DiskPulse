# 遥测新鲜度与平台可观测实施复盘

## 实施范围

实现由以下边界组成：

1. Alembic `000000000008`、ORM、CRUD 和生命周期服务建立独立运行账本。
2. 容量、厂商事件、性能任务按集群写入开始/结束状态，锁冲突仅写 scheduler 跳过。
3. 增加健康、就绪、指标和只读运行查询 Router；探针在常规数据库 session middleware 前短路。
4. 增加配置样例、运行说明、90 天清理任务和 Beat 调度；不提交真实 Token、CIDR 或 scrape/告警模板。

容量任务从活跃集群快照分组，因此即使集群没有启用监控的项目组，也会进入集群级账本。性能任务只在 QuestDB 事务提交后完成成功账本；容量任务的 QuestDB 历史写入保持尽力执行，不改变容量成功语义。

## 复查发现与 TDD 修复

复查期间发现 `/metrics` 路由把应用级 `SessionLocal` 传给 `render_metrics`。这会让指标抓取复用业务 PostgreSQL 连接池，偏离“探针与指标使用专用 `pool_size=1` 连接”的设计边界。

处理过程：

| 阶段 | 证据 | 本地提交 |
| --- | --- | --- |
| RED | 新增路由用例断言 `render_metrics()` 不接收应用 session factory，执行后得到实际调用带 `SessionLocal` 的失败。 | `067cdaa` |
| RED 补充 | 新增专用 engine、session factory 与 `dispose()` 生命周期用例，执行后因尚未导入 `sessionmaker` 失败。 | `e9e8879` |
| GREEN | 移除 Router 对 `SessionLocal` 的导入；`render_metrics()` 默认创建 `_probe_engine(..., pool_size=1)`、绑定专用 `sessionmaker`，并在 finally 中 dispose；保留显式 factory 注入以便测试。 | `cf77c77` |

GREEN 后，遥测聚焦测试为 `32 passed`，完整后端测试为 `442 passed`。修复不改变设备 API 调用、业务域表写入、任务周期或 API 认证范围。

## 关键实现决策

| 决策 | 原因 |
| --- | --- |
| 最新成功采用数据库窗口函数 | 每个组件/集群只获取一条最新成功记录，避免把历史成功行全部载入后在 Python 中猜测。 |
| 账本独立短事务 | 状态可用时提供可观测性；不可用时不把状态失败伪装成采集失败。 |
| 常量时间文件 Token 比对 | 保护机器指标端点，不把 Token、地址或异常暴露给响应与指标标签。 |
| 依赖 probe engine 每次释放 | 避免探针长期占用业务连接池或泄漏专用连接。 |
| 外部化 scrape/CIDR/告警 | 仓库不持有部署网段和监控平台配置，保持环境职责边界。 |

## 代码和迁移审查结果

本轮 CodeGraph 复查确认：

- 账本模型和 `000000000008` 的唯一键、状态检查、UTC 时间、`ON DELETE SET NULL`、索引及单一迁移 head 一致。
- 三类采集在数据面提交后才记录成功，失败/不支持/零样本/锁冲突均有独立语义；追踪 ID 经 UUID 校验或安全生成。
- `healthz`、`readyz`、`metrics` 都绕过常规 API session middleware；`readyz` 使用每项 1 秒的专用 PostgreSQL、Redis、QuestDB 检查，`metrics` 经本次修复使用专用 PostgreSQL session。
- `/telemetry-runs` 的权限、UTC 时间筛选、数据库分页、删除集群历史回查和响应脱敏符合约定。
- 清理任务使用 90 天阈值、1,000 条批处理、30 分钟锁和无敏感飞书失败通知，Beat 在当前时区 03:17 调度。

## 已知部署前提

真实 PostgreSQL、Redis、QuestDB、Celery Beat/Worker、飞书、Token 文件权限、监控网段限制和 100 次已认证 `/metrics` 抓取 P95 尚未在本地独立 worktree 中连接验证。worktree 不复制未跟踪的 `backend/config.yml`，以避免复制真实运行时凭据；这些检查必须由部署环境在暗运行期完成。
