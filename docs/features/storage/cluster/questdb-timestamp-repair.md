# QuestDB 时间修复指南

## 适用问题

历史容量与性能采集曾把 `Asia/Shanghai` 本地 naive 墙上时间直接写入固定为 UTC 的 QuestDB 连接。QuestDB 将该值解释为 UTC，派生任务再次按 UTC 处理，最终使事件中心、趋势和性能监控相对真实瞬时晚 8 小时。

受影响范围为以下 9 张生产时序表：

- `storage_cluster_storage_usages`
- `aggregate_storage_usages`
- `volume_storage_usages`
- `qtree_storage_usages`
- `project_storage_usages`
- `group_storage_usages`
- `storage_usages`
- `user_storage_usages`
- `storage_performance_metrics`

## 只读审计

在 `backend/` 目录执行：

```powershell
..\.venv\Scripts\python.exe -m scripts.repair_questdb_timestamps
```

命令默认只读，逐表输出行数、最早/最晚 timestamp 和相对当前 UTC 的未来行数。QuestDB 不支持 PostgreSQL 的聚合 `FILTER (WHERE ...)` 语法，工具使用独立 `count()` 查询统计未来行。

## 修复顺序

1. 停止全部会写 QuestDB 的 Celery worker 和定时任务，并确认没有手工采集。
2. 对 QuestDB 和 PostgreSQL 建立可恢复备份；确认所选 QuestDB 表尚未混入新 UTC 写入。
3. 先部署数据库迁移和新代码，但不要启动采集 worker。Alembic `000000000019` 会把既有性能异常、事件证据和性能争用 Incident 的派生时间减去 8 小时，并重算 30 分钟 UTC 归并桶。
4. 执行 QuestDB 表重建：

```powershell
..\.venv\Scripts\python.exe -m scripts.repair_questdb_timestamps `
  --apply `
  --confirm-writes-stopped `
  --confirm-all-rows-are-legacy-local-time
```

5. 工具对每张表建立 UTC 修复表，将 designated timestamp 通过 `dateadd('h', -8, timestamp)` 转换，核对行数和最小/最大时间，再交换表名。原表保留为带执行时间后缀的 `__local_time_backup_...` 备份，不会自动删除。
6. 再次运行只读审计，确认非空表的最大时间不晚于当前 UTC，随后启动采集 worker 并观察新写入。
7. 重跑容量预测和遥测质量派生任务。它们的历史结果不能仅靠平移保证日桶和覆盖率正确，必须从修复后的原始 QuestDB 点重新计算。

## 安全边界

- QuestDB designated timestamp 不能原地更新，所以修复使用“建新表、复制、验证、换名”，换名阶段不是跨表原子事务。
- 禁止对已经混有新 UTC 行和旧上海墙钟行的表执行整体平移；两类行在切换附近存在重叠时间，单靠 timestamp 无法可靠区分。
- 修复中断时不要删除任何 `__utc_repair_...` 或 `__local_time_backup_...` 表；先核对当前表名、行数与时间边界，再决定恢复或继续。
- 原表备份的删除属于独立、不可恢复的运维动作，必须在业务验收和备份保留期结束后另行审批。
