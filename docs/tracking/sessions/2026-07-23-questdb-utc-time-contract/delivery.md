# QuestDB UTC 时间契约整体修复

- 会话：`2026-07-23-questdb-utc-time-contract`
- 状态：代码、PostgreSQL 迁移、QuestDB 九表修复、Worker 恢复和页面验收均已完成
- 范围：修复事件中心最近证据未来 8 小时，并审计、统一全部 QuestDB 生产写入和读取边界。
- 执行明细：[修复与迁移执行记录](./execution.md)

## 假设与成功标准

- DiskPulse 业务本地墙上时间固定为 `Asia/Shanghai`；QuestDB 连接固定为 `timezone=UTC`。
- QuestDB designated timestamp 统一表示 UTC 瞬时，驱动写入使用 UTC naive 值，查询边界使用 UTC RFC 3339 `Z`。
- 9 张生产时序表全部遵守同一契约；面向用户的图表时间在 API 边界转换为上海时间，派生分析保持 UTC-aware。
- 历史修复必须停写、显式确认、逐表核对并保留原表备份。

## 已完成

- 修复容量、项目、用户和性能采集的全部 9 张 QuestDB 表写入路径与相应读取边界。
- 执行 Alembic `000000000019`，修复 1,273 条性能异常、926 条性能证据和 501 个性能事件；未来时间和关联桶重复均为 0。
- 修正迁移批量平移时的即时唯一键冲突，使用唯一临时时间桶后再写入最终桶。
- 执行 QuestDB 九表重建与换名；当前表和 `__local_time_backup_20260723141953` 备份表行数逐表一致，全部 `future_count=0`，无遗留 `__utc_repair` 表。
- 修正修复脚本对纯数字时间后缀的错误拒绝，并为 `user_storage_usages.limit` 使用 QuestDB 保留字引用。
- 修复 DiskPulse 容量告警把上海本地 naive 时间误标为 UTC 的摄取路径。
- 执行 Alembic `000000000020`，以 `storage_alerts.updated_at` 为权威时间修复 10 条容量证据和 10 个容量事件。
- 恢复 Celery Beat 与 solo Worker；最终审计时容量表最大时间为 `2026-07-23 06:41:29 UTC`、性能表最大时间为 `06:39:25 UTC`，九表 `future_count` 仍为 0。
- 浏览器刷新事件中心后，`IC_design_project_SPA3608` 最近证据为 `2026-07-23 14:15:00`；原 `20:08:19` 容量事件修正为 `12:08:19`。

## 数据备份

- PostgreSQL 性能派生数据：
  - `backup_anomaly_observations_20260723141953`：1,260 行
  - `backup_incident_evidence_20260723141953`：915 行
  - `backup_incidents_20260723141953`：497 行
- PostgreSQL DiskPulse 容量告警派生数据：
  - `backup_diskpulse_storage_alerts_202607231432`：10 行
  - `backup_diskpulse_alert_evidence_202607231432`：10 行
  - `backup_diskpulse_capacity_incidents_202607231432`：10 行
- QuestDB：9 张原表均保留为 `<table>__local_time_backup_20260723141953`。

## 验证

- `..\.venv\Scripts\python.exe -m pytest test/test_forecast_incident_center.py test/test_backend_schema_contract.py test/test_questdb_migrations.py test/test_questdb_timestamp_repair.py test/test_vendor_event_definitions_migration.py test/test_vendor_event_definitions_official_expansion_migration.py -q`
  - 结果：78 passed。
- `..\.venv\Scripts\alembic.exe current`
  - 结果：`000000000020 (head)`。
- `..\.venv\Scripts\python.exe -m scripts.repair_questdb_timestamps`
  - 结果：9 张表 `future_count=0`。
- PostgreSQL 校验：
  - 性能和 DiskPulse 告警证据未来行均为 0。
  - 所有 Incident 的 `last_evidence_at > now()` 计数为 0。
  - `(correlation_key, correlation_bucket_at)` 重复组为 0。
- 页面校验：
  - SPA3608 首条最近证据为 14:15。
  - 事件中心首屏没有晚于当前时间的最近证据。

## 未验证范围与风险

- 容量预测和遥测质量的历史派生结果未在本会话批量重算；后续按业务保留策略决定是否从修复后的 QuestDB 原始点重建。
- QuestDB 九张原表备份和六张 PostgreSQL 定向备份均有意保留，未执行删除；删除必须经过独立审批。
- QuestDB 换名不是跨表原子事务。本次第八张表前曾中断，但已依据逐表审计续跑剩余两表并完成一致性核对。
