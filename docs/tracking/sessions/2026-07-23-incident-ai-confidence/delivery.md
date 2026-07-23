# 事件 AI 审查置信度

## 范围

- 为 AI 研判添加必填置信度，并在低置信度时下调 AI 紧急度。

## 已完成

- `low` 置信度将 AI 紧急度下调一级，最低为 `low`。
- 不修改确定性 Incident `severity`；审查快照保留模型原始紧急度、置信度和降级标记。
- 详情抽屉显示置信度与低置信度降级说明。

## 验证

- `cd backend; ..\\.venv\\Scripts\\python.exe -m pytest test\\test_incident_ai_agent.py test\\test_forecast_incident_center.py -q`：59 passed。
- `cd frontend; pnpm exec vitest run test/unit/IncidentDetailDrawer.test.js test/unit/IncidentCenterPage.test.js --coverage.enabled=false`：17 passed。

## 未验证范围与风险

- 未运行完整前后端测试、构建或真实模型端到端调用；上线后需观察不同模型对 `confidence` 枚举的遵循情况。
