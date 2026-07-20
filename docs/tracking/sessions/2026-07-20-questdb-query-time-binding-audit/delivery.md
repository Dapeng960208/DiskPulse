# 2026-07-20 QuestDB 查询时间绑定审计

## 范围

- 复查所有通过 `QuestDBSession` 执行的查询，排除将带时区 Python `datetime` 直接绑定到 QuestDB PGWire 的同类风险。

## 审计与修复结果

- 已修复容量预测 `_quest_capacity_points`：容量预测的 45 天窗口截止时间改为 UTC RFC 3339 `Z` 字符串。
- 已修复 `dashboardCrud.get_capacity_trend`：全局与项目范围趋势查询均先转换时间参数；带时区输入统一转为 UTC `Z` 字符串，无时区输入保留本地墙上时间语义并序列化为文本。
- 已复查质量统计、性能异常、资源监控、健康分析、通用趋势和告警统计查询：这些路径已绑定字符串时间参数，或只使用无时区采集时间写入，不存在本次 `timestamptz` 查询根因。

## 验证

- RED：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test/test_forecast_incident_center.py test/test_dashboard_overview.py --basetemp <temp>`：容量预测与 Dashboard 全局/项目路径的 3 个新增断言失败，实际捕获到带时区 `datetime`。
- GREEN：同一命令：39 passed。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m compileall celery_tasks/tasks/forecast_incidents.py crud/dashboardCrud.py`：通过。

## 未验证范围与风险

- 未直接对运行中的 QuestDB 执行全部查询；回归通过替身验证绑定参数类型，真实执行仍依赖 QuestDB PGWire 对既有 RFC 3339 `Z` 文本的支持。
- 未改动 QuestDB 写入路径：它们使用无时区采集时间，未出现 `timestamptz` 读取错误。
