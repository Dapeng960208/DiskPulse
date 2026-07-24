# Main 分支代码审查问题修复

- 会话：`2026-07-24-code-review-fixes`
- 状态：六项代码审查问题均已修复、验证并独立提交
- 范围：修复相较 `origin/main` 的代码审查问题，并为每项修复补充回归测试、约束注释和独立提交。

## 假设与成功标准

- 保持现有 API、事件关联、AI 调用和时间选择器的公开行为兼容。
- 每项修复先验证回归测试失败，再实现最小修复并验证通过。
- 每项修复独立提交到 `main`，不混入无关重构。

## 已完成

- 恢复备份记录和大文件生产 API 路由，并增加真实 `main.app` 路由契约测试。
- 为滚动事件关联状态迁移回填每个关联键的最新历史 Incident，并覆盖同时间证据按 ID 稳定决胜。
- 为 Claude Code SDK 输出队列应用统一请求超时，超时后取消客户端并释放流式工作线程。
- 阻止窗口外迟到证据覆盖前向关联游标，保留历史事件的同时确保后续实时证据继续归入最新事件。
- 为共享时间选择器增加页面级最大天数，并将集群健康分析快捷范围限制为后端支持的 180 天。
- 将 Claude Code 取消协程的创建移动到事件循环线程，消除循环关闭或不再调度时的未等待协程泄漏。

## 验证

- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_main_route_contract.py test/test_core_api.py test/test_project_scope_authorization.py -q`
  - 结果：36 passed。
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_forecast_incident_center.py test/test_backend_schema_contract.py -q`
  - 结果：56 passed。
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_claude_code_adapter.py test/test_ai_reasoning_effort_red.py test/test_ai_platform.py -q`
  - 结果：162 passed，存在 1 条待后续修复的取消协程未等待警告。
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_forecast_incident_center.py -q`
  - 结果：48 passed。
- `cd frontend; pnpm exec vitest run test/unit/components/time-range-picker.test.js --coverage.enabled=false`
  - 结果：2 passed。
- `cd frontend; pnpm exec vitest run test/unit/pages/storage-cluster-health-analytics.test.js -t "renders the shared time filter inside each time-based analysis tab content" --coverage.enabled=false`
  - 结果：1 passed，17 skipped。
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_main_route_contract.py test/test_core_api.py test/test_project_scope_authorization.py test/test_forecast_incident_center.py test/test_backend_schema_contract.py test/test_claude_code_adapter.py test/test_ai_reasoning_effort_red.py test/test_ai_platform.py -q`
  - 汇总结果：256 passed。
- `cd frontend; pnpm exec vitest run test/unit/ai-api-stream.test.js test/unit/ai-pages.test.js test/unit/ai-reasoning-pages.test.js test/unit/IncidentCenterPage.test.js test/unit/IncidentDetailDrawer.test.js test/unit/components/time-range-picker.test.js test/unit/router/routes.test.js --coverage.enabled=false`
  - 汇总结果：87 passed。
- `cd frontend; pnpm exec eslint src/utils/time-range.js src/components/form/TimeRangePicker.vue src/pages/admin/storage-cluster/StorageClusterDetailPage.vue test/unit/components/time-range-picker.test.js test/unit/pages/storage-cluster-health-analytics.test.js`
  - 结果：0 errors，14 条既有测试文件多组件 warning。

## 未验证范围与风险

- `storage-cluster-health-analytics.test.js` 全文件仍有 2 条既有表格断言失败，与本次时间范围修复无关，已登记到错误事实库。
- AI 联合回归在 `-W error` 下被 3 个既有未关闭 SQLite 连接阻断；常规模式 163 项通过，且不再出现 Claude Code 取消协程警告。
- 本会话未运行完整前后端全量测试、浏览器 E2E 或真实 Claude Agent SDK 集成验证。
