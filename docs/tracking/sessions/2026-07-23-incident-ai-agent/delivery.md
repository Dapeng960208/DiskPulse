# 交付记录：事件 AI 处置 Agent

## 范围

- 事件中心 AI 设置、候选模型回退、运行审计和受限状态推进。
- IOPS 零 MAD 连续三桶的确定性降噪与资源/集群基线回退。
- 事件中心 AI 设置、列表紧急度和详情建议展示。

## 验证

- `cd backend; ..\..\..\.venv\Scripts\python.exe -m pytest test/test_forecast_incident_center.py test/test_incident_ai_agent.py test/test_ai_platform.py test/test_scheduled_user_tasks.py -q`：89 passed。
- `cd backend; ..\..\..\.venv\Scripts\python.exe -m compileall -q services celery_tasks routers schemas crud migrate\versions\000000000021_incident_ai_agent.py`：通过。
- `cd frontend; pnpm vitest run test/unit/IncidentCenterPage.test.js test/unit/IncidentDetailDrawer.test.js test/unit/api/request-modules.test.js test/unit/api/modules.test.js test/unit/mock-capacity-prediction.test.js`：19 passed。
- `cd frontend; pnpm lint`：通过。
- `cd frontend; pnpm build:test`：通过；保留既有 `%VITE_APP_TITLE%` 未定义和产物 chunk 大小警告。

真实模型供应商、Celery/Redis、QuestDB 和生产通知通道未在本地测试替身中执行；运行时依赖隔离环境验证。
