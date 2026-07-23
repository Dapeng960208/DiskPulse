# QuestDB UTC 修复与迁移执行记录

执行日期：2026-07-23  
目标 PostgreSQL：`10.0.91.37:5432/diskpulse`  
目标 QuestDB：`10.0.91.37:8812/qdb`

## 1. 停写与静态审计

Celery 控制面探测没有节点回复，因此不能把 `inspect` 结果当作任务空闲证明：

```powershell
..\.venv\Scripts\celery.exe -A celery_worker:diskpulse_app inspect active --timeout=5
..\.venv\Scripts\celery.exe -A celery_worker:diskpulse_app inspect reserved --timeout=5
..\.venv\Scripts\celery.exe -A celery_worker:diskpulse_app inspect scheduled --timeout=5
```

按可执行文件、启动参数和进程树确认后停止本地 Beat/Worker，再连续审计两次：

```powershell
Stop-Process -Id 9028,9704,26828,23824,26460,12972 -Force
..\.venv\Scripts\python.exe -m scripts.repair_questdb_timestamps
Start-Sleep -Seconds 5
..\.venv\Scripts\python.exe -m scripts.repair_questdb_timestamps
```

第二轮稳定快照行数为 5,490、10,951、389,212、0、5,654、17,247、951,008、0、158,768；两次行数和最大时间一致。

## 2. PostgreSQL 性能数据备份与迁移

使用 `CREATE TABLE ... AS SELECT ...` 建立定向备份：

```sql
CREATE TABLE backup_anomaly_observations_20260723141953 AS
SELECT * FROM anomaly_observations WHERE source = 'questdb_performance';

CREATE TABLE backup_incident_evidence_20260723141953 AS
SELECT evidence.*
FROM incident_evidence evidence
JOIN anomaly_observations anomaly
  ON evidence.source = 'anomaly_observation'
 AND evidence.source_ref = 'anomaly:' || anomaly.id::text
WHERE anomaly.source = 'questdb_performance';

CREATE TABLE backup_incidents_20260723141953 AS
SELECT incident.*
FROM incidents incident
WHERE EXISTS (
  SELECT 1 FROM incident_evidence evidence
  JOIN anomaly_observations anomaly
    ON evidence.source = 'anomaly_observation'
   AND evidence.source_ref = 'anomaly:' || anomaly.id::text
  WHERE evidence.incident_id = incident.id
    AND anomaly.source = 'questdb_performance'
);
```

首次升级因即时唯一键冲突回滚；加入临时时间桶后重试成功：

```powershell
..\.venv\Scripts\alembic.exe current
..\.venv\Scripts\alembic.exe upgrade 000000000019
..\.venv\Scripts\alembic.exe current
```

结果：`000000000019 (head)`；性能异常、证据和事件未来行均为 0，最终时间桶重复为 0。

## 3. QuestDB 九表重建

主执行命令：

```powershell
..\.venv\Scripts\python.exe -m scripts.repair_questdb_timestamps `
  --apply `
  --confirm-writes-stopped `
  --confirm-all-rows-are-legacy-local-time `
  --suffix 20260723141953
```

第一次在 DDL 前因纯数字后缀校验失败。修复后第二次完成前七表，在 `user_storage_usages.limit` 保留字处停止。引用保留字后只续跑剩余两表：

```powershell
..\.venv\Scripts\python.exe -m scripts.repair_questdb_timestamps `
  --apply `
  --confirm-writes-stopped `
  --confirm-all-rows-are-legacy-local-time `
  --suffix 20260723141953 `
  --table user_storage_usages `
  --table storage_performance_metrics
```

完成后执行：

```powershell
..\.venv\Scripts\python.exe -m scripts.repair_questdb_timestamps
```

结果：九表 `future_count=0`；当前表与 `__local_time_backup_20260723141953` 行数逐表一致；遗留 `__utc_repair` 表数为 0。

## 4. DiskPulse 容量事件迁移

先建立 10 行源告警、10 行证据、10 行事件定向备份：

```sql
CREATE TABLE backup_diskpulse_storage_alerts_202607231432 AS
SELECT alert.* FROM storage_alerts alert
WHERE EXISTS (
  SELECT 1 FROM incident_evidence evidence
  WHERE evidence.source = 'diskpulse_alert'
    AND evidence.source_ref = 'diskpulse:' || alert.id::text
);

CREATE TABLE backup_diskpulse_alert_evidence_202607231432 AS
SELECT * FROM incident_evidence WHERE source = 'diskpulse_alert';

CREATE TABLE backup_diskpulse_capacity_incidents_202607231432 AS
SELECT incident.* FROM incidents incident
WHERE EXISTS (
  SELECT 1 FROM incident_evidence evidence
  WHERE evidence.incident_id = incident.id
    AND evidence.source = 'diskpulse_alert'
);
```

执行历史修复：

```powershell
..\.venv\Scripts\alembic.exe upgrade 000000000020
..\.venv\Scripts\alembic.exe current
```

结果：`000000000020 (head)`；DiskPulse 告警证据与 `storage_alerts.updated_at AT TIME ZONE 'Asia/Shanghai'` 的不一致数为 0，所有事件未来行数为 0。

## 5. 恢复与验收

使用隐藏窗口恢复原启动方式：

```powershell
$celeryExe = 'D:\dev\DiskPulse\.venv\Scripts\celery.exe'
$workingDir = 'D:\dev\DiskPulse\backend'
Start-Process -FilePath $celeryExe `
  -ArgumentList @('-A','celery_worker:diskpulse_app','beat','--loglevel=INFO') `
  -WorkingDirectory $workingDir -WindowStyle Hidden
Start-Process -FilePath $celeryExe `
  -ArgumentList @('-A','celery_worker:diskpulse_app','worker','--loglevel=INFO','--pool=solo') `
  -WorkingDirectory $workingDir -WindowStyle Hidden
```

首次恢复后审计，`storage_usages` 新增 71 行，最大时间为 `2026-07-23 06:30:10 UTC`，未来行仍为 0。执行第二条 PostgreSQL 迁移并最终恢复后，容量表最大时间继续推进到 `06:41:29 UTC`，性能表推进到 `06:39:25 UTC`，九表未来行仍为 0。

聚焦测试：

```powershell
..\.venv\Scripts\python.exe -m pytest `
  test/test_forecast_incident_center.py `
  test/test_backend_schema_contract.py `
  test/test_questdb_migrations.py `
  test/test_questdb_timestamp_repair.py `
  test/test_vendor_event_definitions_migration.py `
  test/test_vendor_event_definitions_official_expansion_migration.py -q
```

结果：78 passed。浏览器刷新 `/admin/incidents` 后，SPA3608 为 14:15，原未来容量事件为 12:08。
