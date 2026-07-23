# 事件 AI 审查优先级

## 范围

- 限制事件 AI 审查的即时触发、时效窗口和定时批次规模。

## 已完成

- 生命周期仅投递最近 60 分钟内的 `critical` 事件。
- 定时审查按严重度、审查/证据状态和最近证据排序，每轮最多 5 条。

## 验证

- `cd backend; ..\\.venv\\Scripts\\python.exe -m pytest test\\test_incident_ai_agent.py test\\test_forecast_incident_center.py -q`：56 passed。
- 导入 `celery_tasks.tasks.forecast_incidents` 与 `celery_tasks.tasks.incident_ai_agent`：通过。

## 未验证范围与风险

- 未连接实际 Celery broker 验证突发事件的端到端队列行为；固定阈值与批次大小需根据线上模型容量持续观察。
