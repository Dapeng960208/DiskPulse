# 开发交付：QuestDB 遥测质量时间参数

- 会话：`2026-07-20-questdb-telemetry-quality-timestamp`
- 状态：已交付
- 范围：修复 `telemetry_quality_snapshot_task` 读取 QuestDB 原始遥测点时的带时区时间参数兼容性。

## 已完成

- 为性能和容量使用原始点查询添加回归测试，覆盖 QuestDB 必须接收 UTC RFC 3339 `Z` 字符串下限的契约。
- `_raw_point_count` 统一将窗口下限规范化为 UTC `Z` 字符串后再绑定，避免 SQLAlchemy/psycopg2 注入 QuestDB 不支持的 `timestamptz` 类型。
- 记录该可复现错误、出现次数和遥测可观测性专题中的兼容性约束。

## 验证与风险

- RED：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test\test_forecast_incident_center.py -q -k telemetry_quality_raw_point_query_binds_questdb_time_as_utc_string --basetemp=<task-temp>`，2 个用例按预期失败，证明修复前仍传递带时区 `datetime`。
- GREEN：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test\test_forecast_incident_center.py test\test_telemetry_observability.py -q --basetemp=<task-temp>`，66 个用例通过；`D:\dev\DiskPulse\.venv\Scripts\python.exe -m compileall -q celery_tasks\tasks\forecast_incidents.py` 通过。
- 使用同一组测试显式统计 `forecast_incidents.py` 时，既有 448 语句任务模块覆盖率为 30%；本次新增的两个生产语句均有执行标记。未为与本错误无关的容量预测、异常检测和事件关联路径补充覆盖率。
- 已用配置的 QuestDB 对 `performance` 与 `storage_usage` 执行 `_raw_point_count(0, ..., started_at=<当前 UTC 时间>)`；两条只读查询均成功返回空结果，确认字符串绑定可被当前实例接受。
- 未启动真实 Celery 调度周期，也未对含真实集群 ID 的生产遥测数据执行全链路快照；部署后应观察下一次质量快照任务日志。
