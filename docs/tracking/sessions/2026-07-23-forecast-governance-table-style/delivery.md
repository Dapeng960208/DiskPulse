# 预测治理表格样式统一交付记录

- 会话：`2026-07-23-forecast-governance-table-style`
- 状态：已完成聚焦验证
- 范围：统一“系统管理 → 预测治理”的候选模型和跨资源滚动回测评估表格样式。

## 改动

- 两张业务表改为复用共享 `DataTable`，不再直接使用 `ElTable`。
- 表格区移除页面级卡片视觉，避免与 `DataTable` 自带卡片重复嵌套。
- 跨资源滚动回测评估继续使用“暂无完成的 30 天评估窗口”专用空态。
- 候选模型操作列固定在右侧，并复用全局 `.list-row-actions`。
- 新增静态架构测试，限制页面直接使用 Element Plus 表格、分页和页面级表格样式覆盖。

## 验证

- RED：聚焦测试共 12 条，新增架构测试因页面未使用 `DataTable` 失败，其余 11 条通过。
- GREEN：`cd frontend && pnpm exec vitest run test/unit/forecast-governance-page.test.js --coverage.enabled=false`，12 条测试全部通过。
- `cd frontend && pnpm exec eslint src/pages/admin/forecast-governance/ForecastGovernancePage.vue test/unit/forecast-governance-page.test.js`：通过。
- `git diff --check`：通过。

## 未验证范围和风险

- 尚未执行全量前端测试、生产构建和真实浏览器窄屏验证。
- 候选模型表改用共享组件后使用其默认空态文案；评估表仍保留业务专用空态。
