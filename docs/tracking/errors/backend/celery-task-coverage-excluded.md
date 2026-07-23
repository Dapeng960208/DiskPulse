# Celery 任务被覆盖率配置排除

## 错误内容

对 `backend/celery_tasks/` 中的聚焦测试执行覆盖率统计时，仓库 `.coveragerc` 将 `backend/celery_tasks/*` 整体列入 `omit`。测试全部通过，但 `coverage.py` 不采集目标任务模块并报告 `No data was collected` 和 `0%`；当前环境也未安装提供 Pytest `--cov` 参数的 `pytest-cov` 插件。

## 解决方案

日常修改仍执行对应 Celery 任务的聚焦行为测试，不把被配置排除后的 `0%` 当作真实代码覆盖率。需要量化 Celery 任务覆盖率时，应在独立治理任务中明确调整权威 `.coveragerc` 排除策略并验证全量门禁，或提供不改变仓库门禁口径的专用覆盖率配置；不得临时把无数据结果描述为覆盖率通过。

## 备注

- 分类：`backend`
- 出现次数：1
- 首次出现：2026-07-23 飞书告警利用率颜色会话
- 最近出现：2026-07-23 飞书告警利用率颜色会话
- 出现记录：`sessions/2026-07-23-feishu-alert-utilization-colors/errors.md`
