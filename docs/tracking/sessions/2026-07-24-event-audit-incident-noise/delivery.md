# 交付记录：事件审计研判与 Incident 降噪

## 范围

- 统一审计只读 AI 工具、不可覆盖的审计研判提示与审计页面跳转草稿。
- 同一资产和类别的 4 小时滚动 Incident 关联状态、已解决窗口内重开与并发幂等。
- 仅持续正向 P95 延迟退化可建立性能争用 Incident；IOPS/吞吐保留诊断观察。

## 已完成

- 已完成实现、迁移、配置示例和事实文档更新。

## 验证

- `cd backend; ..\\..\\..\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_services.py test\\test_ai_platform.py test\\test_forecast_incident_center.py test\\test_incident_admission.py test\\test_questdb_time_contract_guard.py test\\test_datetime_utils.py -q`：126 passed。
- `cd backend; ..\\..\\..\\.venv\\Scripts\\alembic.exe -c alembic.ini heads`：`000000000023 (head)`。
- `cd frontend; pnpm exec vitest run test/unit/ai-pages.test.js test/unit/incident-and-audit-list-layout.test.js test/unit/project-detail-table-scroll.test.js`：36 passed。
- `cd frontend; pnpm exec eslint src/pages/ai/AiChatPage.vue src/pages/admin/audit/AuditEventListPage.vue src/pages/admin/audit/AuditEventDetailPage.vue src/pages/admin/audit/components/AuditEventDetailDrawer.vue src/pages/project/components/ProjectAuditTab.vue src/pages/incident/components/IncidentDetailDrawer.vue`：通过。
- `cd frontend; pnpm run build:test`：通过；仅有既有环境变量和大体积 bundle 警告。
- `git diff --check`：交付前执行。

## 未覆盖与风险

- 真实 Provider、Celery/Redis、QuestDB 运行时和生产数据库迁移仍须在隔离环境验收。
- 扩展前端矩阵中的 `content-spacing-contract.test.js` 存在既有 3 项基线失败，已按规范记录；本次聚焦用例和构建均通过。
