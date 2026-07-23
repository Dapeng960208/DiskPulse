# 事件 AI 审查可见性

## 范围

- 补充 Incident AI 审查任务的结构化日志。
- 在事件 API 和详情抽屉展示 AI 审查状态。

## 已完成

- `IncidentOut`/`IncidentDetailOut` 返回最近一次 AI 审查的安全状态与时间；详情抽屉和事件列表可识别“AI 审查中”。
- AI 审查投递、开始、跳过、完成和异常日志包含事件、触发来源和最终结果上下文。

## 验证

- `cd backend; ..\\.venv\\Scripts\\python.exe -m pytest test\\test_incident_ai_agent.py -q`：12 passed。
- `cd frontend; pnpm exec vitest run test/unit/IncidentDetailDrawer.test.js --coverage.enabled=false`：9 passed。

## 风险与未验证范围

- 未运行完整前后端测试、构建或连接实际 Celery worker 的端到端验证；线上队列尚未实测日志字段。
