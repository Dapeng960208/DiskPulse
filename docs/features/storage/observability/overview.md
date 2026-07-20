# 遥测新鲜度与平台可观测

## 运行账本

`telemetry_collection_runs` 是容量、厂商事件和性能采集最后成功时间的唯一来源。每次执行记录范围、组件、关联 ID、开始/结束时间、结果、数据状态和写入数量；不持久化原始异常、设备响应或敏感配置。

- 容量成功表示 PostgreSQL 当前态已提交；厂商事件成功表示事件已落库；性能成功表示 QuestDB 已提交。
- `empty` 仍表示本轮成功且数据新鲜；失败、跳过和从未成功分别保留不同状态。
- 容量和厂商事件在最后成功 150 秒内为 `fresh`，性能在 630 秒内为 `fresh`；超过阈值为 `stale`。

## 健康、指标与权限

| 入口 | 访问边界 | 作用 |
| --- | --- | --- |
| `GET /storage-pulse/api/v1/healthz` | 无认证 | 进程存活检查。 |
| `GET /storage-pulse/api/v1/readyz` | 无认证 | PostgreSQL、Redis 与 QuestDB 的就绪/降级状态。 |
| `GET /storage-pulse/api/v1/metrics` | `X-Metrics-Token` | Prometheus 指标；令牌失败统一拒绝。 |
| `GET /storage-pulse/api/v1/telemetry-runs` | 超级管理员 | 按集群、组件、时间范围和分页查询运行账本。 |

指标不包含设备地址、原始异常或高基数字段。Celery 队列深度和 Worker 心跳仍由专用 exporter 负责，API 不通过 `celery inspect` 推断运行状态。

## 部署边界

指标令牌文件由部署系统以最小权限挂载，反向代理或防火墙限制抓取来源。账本清理和告警通知依赖 Celery、Redis 与通知配置；真实 Token 文件权限、外部依赖和告警投递必须在部署环境验证。
