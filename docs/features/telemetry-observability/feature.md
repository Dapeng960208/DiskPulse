# 遥测新鲜度与平台可观测功能说明

## 面向运维人员的能力

该功能将三类遥测采集的最后结果持久化为可查询的运行账本，并向监控系统提供存活、依赖就绪与 Prometheus 指标。它不改变容量、厂商事件和性能任务原有的设备调用频率。

### 运行记录查询

超级管理员可读取：

```text
GET /storage-pulse/api/v1/telemetry-runs
```

支持参数：

| 参数 | 说明 |
| --- | --- |
| `cluster_id` | 集群 ID。即使集群已经删除，也通过保留的 `scope_key` 找回历史账本。 |
| `component` | `capacity`、`vendor_events` 或 `performance`。 |
| `started_at_from` / `started_at_to` | 必须携带 UTC 偏移；开始时间不得晚于结束时间。 |
| `page` / `size` | 数据库分页，页号从 1 开始，`size` 最大 100。 |

每条记录返回运行 ID、追踪 ID、作用域、集群 ID、组件、结果、数据状态、写入条数、标准错误码和 UTC 开始/结束时间。不会返回 Celery task ID、设备地址、设备名、路径、用户名、原始异常或凭据。

结果解释：

| 字段 | 含义 |
| --- | --- |
| `outcome=success` | 对应数据面的写入已经提交。 |
| `outcome=failed` | 集群采集失败；原始错误不对外暴露。 |
| `outcome=skipped` | 任务级 Redis 锁冲突；不改变任一集群最后成功时间。 |
| `data_state=data` | 成功且至少写入一条记录。 |
| `data_state=empty` | 成功但没有新样本，仍视为新鲜。 |
| `data_state=unsupported` | 明确不支持该设备类型或组件。 |

## 探针和指标

| 地址 | 调用方式 | 预期响应 |
| --- | --- | --- |
| `/storage-pulse/api/v1/healthz` | 无认证 | 恒定 `200 {"status":"ok"}`，表示进程可响应。 |
| `/storage-pulse/api/v1/readyz` | 无认证 | 全依赖可用为 `200 ready`；仅 QuestDB 不可用为 `200 degraded`；PostgreSQL 或 Redis 不可用为 `503 not_ready`。 |
| `/storage-pulse/api/v1/metrics` | `X-Metrics-Token` | Prometheus 文本；无效 Token 统一 `403`。 |

部署系统应在最小权限文件中写入单个 Token，例如：

```yaml
observability:
  metrics_token_file: /run/secrets/diskpulse-metrics-token
```

Token 文件不提交。反向代理或防火墙必须把 `/metrics` 限制在监控网段，Token 只作为第二道认证边界。

指标清单：

- `diskpulse_http_requests_total`
- `diskpulse_http_request_duration_seconds`
- `diskpulse_dependency_ready`
- `diskpulse_telemetry_freshness_seconds`
- `diskpulse_telemetry_status`
- `diskpulse_telemetry_last_success_timestamp_seconds`

`diskpulse_telemetry_status` 中 `unknown=0`、`fresh=1`、`stale=2`。从未成功时只输出状态；PostgreSQL 不可用时 `/metrics` 仍返回 `200` 和依赖状态，但省略不能读取的遥测序列。

## 新鲜度和告警使用建议

- 容量与厂商事件：最后成功不超过 150 秒为新鲜。
- 性能：最后成功不超过 630 秒为新鲜。
- `empty` 不是失败；应同时观察状态和最近成功时间，而不是把零样本直接告警。
- `/readyz` 反映当前依赖可用性，遥测 `stale` 反映成功采集的时间边界，两者需要分别告警。

建议先在测试集群暗运行 7 天，核对账本、`/telemetry-runs` 和指标对同一集群/组件的一致性，再由部署环境配置 Prometheus scrape、`not_ready` 与 `stale` 告警，并接入既有通知体系。
