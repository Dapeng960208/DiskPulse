# QuestDB UTC 时间契约整体修复

- 会话：`2026-07-23-questdb-utc-time-contract`
- 状态：代码与修复工具完成；当前连接数据仅执行只读审计，未执行破坏性表换名
- 范围：修复事件中心最近证据未来 8 小时，并审计、统一全部 QuestDB 生产写入和读取边界。

## 假设与成功标准

- DiskPulse 业务本地墙上时间固定为 `Asia/Shanghai`；QuestDB 连接固定为 `timezone=UTC`。
- QuestDB designated timestamp 统一表示 UTC 瞬时，驱动写入使用 UTC naive 值，查询边界使用 UTC RFC 3339 `Z`。
- 9 张生产时序表全部遵守同一契约；面向用户的图表时间在 API 边界转换为上海时间，派生分析保持 UTC-aware。
- 历史修复必须可审计、默认只读、停写后显式确认，并保留原表备份。

## 已完成

- 在 `utils.datetime_utils` 增加 QuestDB UTC 写入、读取和本地展示转换函数。
- 修复容量、项目、用户和性能采集的全部 9 张 QuestDB 表写入路径。
- 修复 Dashboard、容量趋势、存储详情、性能监控和健康分析查询的 UTC `Z` 参数与返回时间转换。
- 性能异常任务将 QuestDB naive timestamp 按 UTC 解释，避免再次产生未来 Incident。
- 新增 Alembic `000000000019`，修复既有性能异常、IncidentEvidence 和性能争用 Incident 的 +8 小时派生时间，并重算关联桶。
- 新增默认只读的 `scripts.repair_questdb_timestamps`，覆盖 9 张表的审计、停写确认、重建、行数/时间边界核对、换名与原表备份保留。
- 同步数据库规范、趋势、性能采集、健康分析和历史修复运维文档。

## 只读数据审计

审计时间为 2026-07-23（UTC 当前时间由工具实时绑定）。非空表均发现未来行，确认不是单一性能表问题：

| 表 | 行数 | 未来行 |
| --- | ---: | ---: |
| `storage_cluster_storage_usages` | 5,480 | 234 |
| `aggregate_storage_usages` | 10,931 | 468 |
| `volume_storage_usages` | 388,502 | 16,613 |
| `qtree_storage_usages` | 0 | 0 |
| `project_storage_usages` | 5,629 | 561 |
| `group_storage_usages` | 17,212 | 815 |
| `storage_usages` | 948,473 | 57,352 |
| `user_storage_usages` | 0 | 0 |
| `storage_performance_metrics` | 158,378 | 6,937 |

## 验证

- TDD RED：新增 UTC 契约测试首先因缺少转换函数而导入失败；历史修复测试首先因缺少脚本/迁移而失败。
- `..\.venv\Scripts\python.exe -m pytest test/test_datetime_utils.py test/test_storage_health_analytics.py test/test_scheduled_user_tasks.py test/test_storage_resource_mapping.py test/test_storage_soft_quota.py test/test_dashboard_overview.py test/test_forecast_incident_center.py -q`
- `..\.venv\Scripts\python.exe -m pytest test/test_questdb_timestamp_repair.py -q`
- `..\.venv\Scripts\python.exe -m scripts.repair_questdb_timestamps`

## 未验证范围与风险

- 未对当前 `10.0.91.37` QuestDB 执行 `--apply`；该操作会重建并交换生产时序表名，必须先停写和建立可恢复备份。
- 未在当前 PostgreSQL 执行 Alembic `000000000019`，只验证了迁移契约，未做真实数据写入。
- QuestDB 表换名不是跨表原子事务；中断时必须依据保留的修复表和备份表人工恢复。
- 容量预测与遥测质量历史结果需在原始 QuestDB 修复后重算，不能通过统一减 8 小时保证日桶和覆盖率正确。
- 真实 worker 重启后的新写入、登录态浏览器和生产规模查询仍需在隔离维护窗口复验。
