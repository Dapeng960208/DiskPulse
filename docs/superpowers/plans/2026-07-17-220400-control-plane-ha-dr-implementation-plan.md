# 控制面 HA/DR 与备份恢复基线实施计划

- 依据：[实施计划索引](./2026-07-17-220000-enterprise-ai-storage-implementation-index.md)
- 状态：待实施。
- 前置条件：遥测新鲜度、`readyz` 和指标已上线；具备双应用节点、高可用 L7 LB、PostgreSQL HA、Redis Sentinel、对象存储/KMS、DNS/TLS、DBA 和故障演练窗口。用于备份的 KMS/凭据要么已由第 02 工作包提供，要么作为经验证的外部前置条件。

## 目标与边界

- 对 PostgreSQL 控制面数据实现 `RPO <= 5 分钟`、`RTO <= 30 分钟`：用户、项目、集群配置、配额、告警、审计和策略均纳入该目标。
- 将 API、Worker、Beat Leader 分离部署，去除当前单宿主机 API/Beat/Worker 共同故障域。
- QuestDB 本期仅为 best-effort：schema 可由现有前向迁移恢复，原始性能时序尽力重新采集；当前没有可验证的日备/恢复链路，故不承诺正式 RPO/RTO，更不得将其误表述为与 PostgreSQL 同等级保证。若需 SLA，必须另立项验证备份与恢复方案。
- 本期不做跨地域多活、阵列数据面复制、全局 exactly-once 或 QuestDB 高可用。

## 目标拓扑与运行规则

- PostgreSQL：Patroni 主备 + HAProxy 写入口，应用只连接 `postgres-rw`；pgBackRest 连续 WAL 归档，`archive_timeout=60s`，每周全量、每日差异、35 天在线保留、月度不可变副本 12 个月，备份对象存储使用 KMS 加密和访问审计。
- Redis：三 Sentinel、主从复制、AOF `everysec`；统一 Redis 工厂使用 broker `5`、result `6`、auth `7`、scheduler `8`、locks `9`，支持 Sentinel、TLS、密码文件。配置契约固定为 Sentinel master 名称、节点列表、TLS CA/证书引用、密码文件、DB 映射和唯一节点 ID；移除含混的单值 `session_db`。认证在 Redis 故障时继续 fail-closed。
- 应用：两台 `diskpulse-api` 节点放在高可用 L7 LB 后，LB 使用 `/readyz`；两台 Worker 使用唯一 hostname；两台 Beat Leader 用 Redis owner-token 租约选主，TTL 30 秒、每 10 秒续约，失租立即终止 Beat。租约只能降低重复调度，不能承诺 exactly-once；每个周期任务必须保持锁、数据库幂等和通知去重。
- 生产迁移：禁用 `database.create_tables=true`；发布作业在 PostgreSQL advisory lock 下仅执行一次 `alembic upgrade head` 和 QuestDB 前向升级，API/Worker 副本启动不得迁移。
- 锁：以可 compare-and-renew 的 owner-token lease 替换普通 Redis 锁；任务锁 TTL 至少是 hard time limit + 60 秒，并支持续租。`retry_storage_alerts_task` 也要单例锁。
- 数据库失主时，直接替换现有 DB 中间件的 `DisconnectionError` 后 `call_next` 重试路径：连接失效一律返回 `503 + Retry-After`，绝不重放 POST/PATCH/DELETE；安全重试的只读请求也必须由显式、独立逻辑处理。
- Worker 消息语义固定为至少一次：容量、性能和厂商事件任务采用 late ack，失败重入队或由下一周期补采；所有写入以任务锁、数据库唯一键/幂等和告警最终投递去重保护，不将消息确认误称为 exactly-once。

## 实施步骤

1. 抽取 Redis 配置和客户端工厂，先为 Sentinel/TLS/DB 映射、租约获取/续租/失租写 RED 测试。
2. 改造 Celery/认证/锁客户端，完成任务锁、数据库幂等、告警最终投递去重和 Beat Leader 租约；在预生产先以单节点角色化运行。
3. 编写 API、Worker、Beat Leader、Exporter 四类独立 systemd unit；固定非 root 服务账号、`Restart` 策略、依赖顺序和 secret 文件权限。将旧 `start.sh` 降为开发入口，停用生产一体化 unit。
4. 部署 PostgreSQL HA、Redis Sentinel、LB、备份对象存储和最小网络策略；接入 `readyz`/metrics 作为切换观察信号。
5. 依次执行 API、Worker、Beat 主节点、PostgreSQL 主库和 Redis 主库故障演练；建立月度恢复和季度完整 DR 演练，同步部署、配置、恢复 Runbook、故障演练记录和 `docs/tracking/current-release.md`。

## 验证与验收

- 单元/集成：租约 owner 校验、续租、失租停止、非 owner 不可释放；Sentinel 切换；双 Beat 的重复投递不产生重复业务副作用或重复最终通知；连接失效写请求只返回 `503`。
- 部署：`systemd-analyze verify`、高可用 LB 探针、API 节点切换；Beat 租约接管不超过 40 秒，首次可观察的下一次调度投递不超过 90 秒。
- DR：恢复到隔离环境，验证 PostgreSQL 数据、Alembic head、QuestDB revision、`readyz`、关键登录和一次只读采集；PostgreSQL 全程小于 30 分钟，恢复点不超过 5 分钟。QuestDB 仅验证 schema 可恢复和尽力补采，不作为该 RPO/RTO 验收对象。
- 安全：备份、日志、指标和恢复报告不得回显密钥、Token、路径或原始设备响应。
