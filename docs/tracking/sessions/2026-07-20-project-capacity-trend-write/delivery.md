# 项目容量趋势写入交付记录

## 范围

修复项目容量详情没有趋势数据的问题：将已完成的项目 PostgreSQL 汇总写入 QuestDB 的 `project_storage_usages`。

## 已完成

- 添加项目汇总后的 QuestDB 趋势写入回归测试。
- 在 PostgreSQL 项目汇总事务提交后写入项目时序数据，保持项目级时间戳一致。
- 项目存在跨集群项目组时，延续已有的全成功门槛，避免写入部分采集结果。

## 验证

- RED：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend\test\test_storage_resource_mapping.py -q --basetemp <临时目录>`，新增用例因 `write_project_usage_metrics` 缺失失败。
- GREEN：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend\test\test_storage_resource_mapping.py backend\test\test_storage_collection_trigger.py -q --basetemp <临时目录>`，`33 passed`。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m compileall -q backend` 通过。
- 重启本地 Celery worker/beat 后，分钟级采集在 `2026-07-20 13:03:24` 为 3 个项目写入首批趋势；随后受控补写当前聚合值，`project_storage_usages` 共 6 条记录。
- 通过项目接口同源查询验证，项目 `1`、`2`、`3` 在最近 8 小时各返回 2 个 `used` 趋势点。

## 风险

- QuestDB 不可用时，项目当前汇总仍保留在 PostgreSQL；项目趋势会延后到下一轮成功写入。
- 未执行浏览器端页面复查；已直接验证页面使用的后端查询链路。
