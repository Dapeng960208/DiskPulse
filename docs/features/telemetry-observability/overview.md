# 遥测新鲜度与平台可观测

## 专题导航

- [设计复盘](./design.md)：架构、数据契约、探针边界与运维取舍。
- [功能说明](./feature.md)：接口、指标、Token 和告警使用方式。
- [实施复盘](./implementation.md)：实现范围、TDD 修复、代码审查和部署前提。
- [验收复盘](./acceptance.md)：自动化验证结果、部署验收清单和剩余风险。

## 目标与边界

本功能将容量、厂商事件和性能采集的运行结果写入 `telemetry_collection_runs`，作为最后成功时间和新鲜度的唯一来源。它不新增设备 API 调用，不修改现有业务域表，不新增前端页面，也不逐条写入统一审计。

## 运行账本与新鲜度

- 每个集群、组件和 Celery 尝试使用独立 `run_id`，保存 `trace_id`、UTC 开始/结束时间、成功/失败/跳过结果以及成功时的样本状态和写入数。
- 容量成功仅表示 PostgreSQL 采集事务提交；厂商事件成功仅表示事件落库提交；性能成功仅表示 QuestDB 提交。容量的尽力 QuestDB 历史写入失败不改变容量成功结果。
- 成功写入 `records_written`：容量为 `StorageUsage + Group` 更新数，厂商事件为新增事件数，性能为 QuestDB 行数。`0` 为 `empty`，明确不支持为 `unsupported`。
- 失败和跳过不保存原始异常或错误细节；任务日志只记录标准错误类别，账本对应字段保持空值。
- 容量和厂商事件在最后成功后 150 秒内为 `fresh`，性能在 630 秒内为 `fresh`；超过阈值为 `stale`，从未成功为 `unknown`。`empty` 仍为新鲜。
- 集群删除后账本外键置空；集群 ID 的字符串保留在 `scope_key`，历史仍可筛选。

## API 与指标

| 入口 | 鉴权 | 契约 |
| --- | --- | --- |
| `GET /storage-pulse/api/v1/healthz` | 无 | 固定 `200 {"status":"ok"}`，不访问数据库。 |
| `GET /storage-pulse/api/v1/readyz` | 无 | PostgreSQL 或 Redis 不可用时 `503 not_ready`；仅 QuestDB 不可用时 `200 degraded`；不返回地址或异常。 |
| `GET /storage-pulse/api/v1/metrics` | `X-Metrics-Token` | 令牌文件以常量时间比较；缺失、空值、读取失败或不匹配固定 `403`。 |
| `GET /storage-pulse/api/v1/telemetry-runs` | `super_admin` | 支持 `cluster_id`、组件、带 UTC 偏移的时间范围、分页；不返回 Celery task ID、设备信息或原始异常。 |

指标固定为 `diskpulse_http_requests_total`、`diskpulse_http_request_duration_seconds`、`diskpulse_dependency_ready`、`diskpulse_telemetry_freshness_seconds`、`diskpulse_telemetry_status` 和 `diskpulse_telemetry_last_success_timestamp_seconds`。标签只使用 HTTP 方法、模板路由、状态码、组件与集群 ID。状态数值为 `unknown=0`、`fresh=1`、`stale=2`。

PostgreSQL 不可用时 `/metrics` 仍返回依赖指标，但省略无法查询的新鲜度序列。Celery 队列深度与 Worker 心跳继续由独立 `celery-exporter` 负责，API 不调用 Celery inspect。

## 配置、运维与告警

在运行时配置中设置：

```yaml
observability:
  metrics_token_file: /run/secrets/diskpulse-metrics-token
```

该文件由部署系统以最小权限挂载，内容为单个抓取令牌，不得提交到仓库。反向代理或防火墙必须限制 `/metrics` 仅允许监控网段访问；本仓库不维护具体 CIDR、scrape job 或部署环境告警文件。

每日 03:17（Celery 当前时区）清理一次 90 天前的账本记录，每批最多 1,000 条。采集任务的 Redis 锁冲突记录 scheduler 级跳过；清理任务的锁冲突只安全记录跳过执行。清理失败不写 `StorageAlerts`，而是向已配置的飞书 `cc_usernames` 直接发送无敏感摘要。无飞书配置时任务失败并记录安全日志，下一日重试。

上线后先暗运行 7 天，仅观察 `not_ready` 与 `stale`；确认基础设施、Token 文件和集群阈值稳定后再由部署环境启用告警通知。

## 验证与部署

1. 在 `backend/` 执行 `..\\.venv\\Scripts\\python.exe -m alembic -c alembic.ini upgrade head`。
2. 重启 FastAPI、Celery Worker 与 Celery Beat，使新路由、指标和清理调度生效。
3. 使用部署系统提供的 Token 从允许网段抓取 `/metrics`；确认 `readyz`、依赖 Gauge、活跃集群三类新鲜度和 `/telemetry-runs` 一致。
4. 在测试环境按计划停止 QuestDB、PostgreSQL、Redis 和 Worker，验证相应的降级与新鲜度变化。

本地自动化测试不替代真实 Redis、PostgreSQL、QuestDB、Celery Beat/Worker、飞书或网络策略的部署验收。

## 派生质量快照边界

事件中心的 `telemetry_quality_snapshots` 在原始容量、厂商事件和性能写入成功后由独立 Celery 任务派生。快照结合本账本成功运行数与 QuestDB/厂商事实覆盖率，保存资产、周期、最新点、覆盖率、质量状态和数据缺口；它不是也绝不会成为第二套“最后成功时间”权威来源。

质量任务使用独立 Redis 锁并在异常时只记录安全日志，不能回滚或阻塞原始采集。`telemetry_stale`、`coverage_insufficient` 与采集失败可作为派生 Incident 的证据，但静默和维护窗口不会删除运行账本、原始事实或质量快照。
