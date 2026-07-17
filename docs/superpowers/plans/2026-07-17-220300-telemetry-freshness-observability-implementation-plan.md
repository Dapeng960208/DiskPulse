# 遥测新鲜度与平台可观测实施计划

- 依据：[实施计划索引](./2026-07-17-220000-enterprise-ai-storage-implementation-index.md)
- 状态：待实施。
- 前置条件：PostgreSQL Alembic 迁移、Prometheus、受保护指标 Token 与监控网段策略可用。

## 目标与边界

- 将容量、厂商事件、性能三条采集链路的最后结果和新鲜度持久化，不再从 `StorageCluster.updated_at` 或日志猜测采集状态。
- 新增进程存活、依赖就绪、Prometheus 指标端点；不新增任何设备 API 调用，不阻塞现有采集，也不写入现有业务域表（本计划的运行账本除外）。
- 本工作包不引入 OTel 全链路追踪、日志平台、预测/RCA 或前端大屏；告警仍使用既有通知体系。

## 数据、探针与指标契约

- Alembic 新增 `telemetry_collection_runs`：`id(UUID run_id)`、`task_id`、`attempt`、`scope_type(cluster|scheduler)`、非空 `scope_key`、nullable `storage_cluster_id`、`component(capacity|vendor_events|performance)`、`started_at`、`finished_at`、`outcome(success|failed|skipped)`、`data_state(data|empty|unsupported)`、`records_written`、`error_code`、`created_at`。任务开始插入一行、结束更新同一 `run_id`；同一 Celery 重试使用新的 `run_id` 并递增 `attempt`，不覆盖历史。唯一约束 `(task_id,attempt,component,scope_key)`，集群运行索引 `(component,storage_cluster_id,finished_at DESC)`；任务级锁冲突以 `scope_type=scheduler`、`scope_key=scheduler` 记录。所有时间为 UTC；集群删除时保留历史记录并将外键置空。每日清理任务以单例锁删除超过 90 天记录，失败只告警且下次重试。
- `error_code` 只允许标准分类：`vendor_auth`、`vendor_timeout`、`postgres`、`questdb`、`unknown`；不得记录设备地址、路径、用户名、原始异常或凭据。
- 活跃集群新鲜度固定：容量和厂商事件 `<=150s`，性能 `<=630s`，即 `2 × beat 周期 + 30s`；从未成功为 `unknown`，超阈值为 `stale`，`empty` 仍是新鲜但标注无样本。
- 每类数据面独立写状态：容量 PostgreSQL 成功才记 `capacity=success`；事件落库成功才记 `vendor_events=success`；QuestDB 性能写入成功才记 `performance=success`。Redis 锁未取得仅以 `scope_type=scheduler` 记任务级 `skipped`，不覆盖任何集群最后成功时间。
- 新增根级探针（不执行常规数据库中间件）：
  - `GET /storage-pulse/api/v1/healthz` 始终返回 `200 {"status":"ok"}`，只证明进程响应。
  - `GET /storage-pulse/api/v1/readyz` 使用专用 `pool_size=1`、1 秒超时连接检查 PostgreSQL、Redis、QuestDB；返回无依赖地址/异常文本的稳定体 `{"status":"ready|degraded|not_ready"}`。PostgreSQL/Redis 失败为 `503 not_ready`，QuestDB 失败为 `200 degraded`。
  - `GET /storage-pulse/api/v1/metrics` 输出 Prometheus 文本，要求 `X-Metrics-Token` 与 `observability.metrics_token_file` 常量时间比对；缺失或错误 Token 固定返回 `403`，网络层仅允许监控网段。
- 新增受 `super_admin` 保护的只读 `GET /storage-pulse/api/v1/telemetry-runs`，可按 `cluster_id`、`component`、时间和分页查询运行结果；其查询先完成作用域校验，返回 `outcome`、`data_state`、`records_written`、标准 `error_code` 和 UTC 时间，不返回敏感细节。
- 指标固定包括 `diskpulse_http_requests_total`（Counter）、`diskpulse_http_request_duration_seconds`（Histogram）、`diskpulse_dependency_ready`（Gauge）、`diskpulse_telemetry_freshness_seconds`（Gauge）、`diskpulse_telemetry_status`（Gauge）和 `diskpulse_telemetry_last_success_timestamp_seconds`（Gauge）；标签只允许方法、模板路由、状态码、组件和集群 ID，禁止用户名、路径、设备名、查询参数和异常文本。Celery 队列深度/Worker 心跳由独立 `celery-exporter` 采集，API 不调用 Celery inspect。
- 高吞吐的 `telemetry_collection_runs` 属于系统运行账本，不逐行写统一 `AuditEvent`；任务必须带 `trace_id`，由聚合指标、账本和任务日志提供追溯，避免把采集频率放大成审计噪声。

## 实施步骤

1. 先写采集运行账本、新鲜度边界和探针 RED 测试，新增 Alembic/ORM/CRUD/纯函数。
2. 将容量、事件、性能任务改为带 `task_id`、`run_id`、`attempt` 和 `trace_id` 的集群级状态写入；状态账本使用独立短事务，状态写失败不得掩盖采集异常。
3. 实现健康 service、Pydantic schema、根级 Router、专用探针连接和指标注册；确保 `healthz` 在 DB session middleware 前短路。
4. 增加配置样例、metrics token 文件约定、Prometheus scrape job、至少对依赖未就绪/遥测陈旧的告警规则、运行结果 API、功能/API/配置说明和 `docs/tracking/current-release.md`；在测试集群暗运行一周后启用新鲜度告警。

## 验证与验收

- 单元：成功/失败/跳过、任务重试、任务级锁冲突、零样本、QuestDB 单独失败、`150s/630s` 边界、状态写失败不改变采集结果、清理锁/失败重试。
- API：`healthz` 不访问数据库；`readyz` 覆盖 ready/degraded/503 及稳定响应体且无敏感细节；`metrics` 覆盖 `403` Token 拒绝、固定指标名、Prometheus 格式和标签约束；`telemetry-runs` 覆盖授权、分页和脱敏结果。
- 集成：停止 QuestDB 时 API 为 `degraded`；停止 PostgreSQL 或 Redis 时为 `503`；停止 Worker 后活跃集群在两个周期后变为 `stale`。
- 验收：所有活跃集群三类遥测均可通过 `telemetry-runs` 查询最后结果；指标抓取 P95 小于 1 秒；不产生额外设备调用或现有业务域表写入。
