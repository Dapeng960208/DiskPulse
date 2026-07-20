# 2026-07-20 QuestDB 性能扫描时间参数修复

## 范围

- 修复 `performance_anomaly_scan_task` 查询 QuestDB 时因 `timestamptz` 参数绑定失败的问题。
- 保持性能异常任务失败不影响原始采集的既有隔离语义。

## 已实现

- `_performance_rows` 先将截止时间规范化为 UTC，再以 RFC 3339 `Z` 字符串传给 QuestDB PGWire。
- 新增回归测试，防止性能异常扫描重新传入带时区的 Python `datetime`。
- 已扩展 QuestDB 参数绑定错误事实记录并更新事件中心任务约束。

## 验证

- RED：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test/test_forecast_incident_center.py --basetemp <temp>`：新增参数绑定断言失败，实际捕获到带时区 `datetime`。
- GREEN：同一命令：31 passed。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m compileall celery_tasks/tasks/forecast_incidents.py`：通过。

## 未验证范围与风险

- 未直接对运行中的 QuestDB 实例执行性能异常扫描；本次回归验证参数类型，实际生产执行仍依赖 QuestDB PGWire 对 RFC 3339 `Z` 字符串的既有支持（质量统计路径已使用同一绑定方式）。
