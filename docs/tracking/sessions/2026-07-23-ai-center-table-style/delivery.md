# AI 中心表格样式统一交付记录

- 会话：`2026-07-23-ai-center-table-style`
- 状态：已完成聚焦验证
- 范围：统一“系统管理 → AI 中心”的模型和审计列表、筛选与分页样式。

## 改动

- 模型和审计列表改为复用共享 `DataTable`，移除页面直接使用的 `ElTable` 与 `ElPagination`。
- 审计分页通过 `DataTable` 的 `update:pagination` 契约更新页码和每页数量后重新加载。
- 审计状态筛选改为复用 `QueryForm`；查询和重置均回到第一页。
- 审计详情改为右侧固定的显式“查看”操作，继续进入原有隐藏详情路由。
- 删除页面自建工具栏和分页局部样式。
- 新增静态架构与组件交互测试，覆盖共享表格、分页、筛选重置和详情导航。

## 验证

- RED：AI 页面聚焦测试共 25 条，新增 4 条因缺少 `DataTable`、`QueryForm`、共享分页契约和显式详情操作而失败，其余 21 条通过。
- GREEN：`cd frontend && pnpm exec vitest run test/unit/ai-pages.test.js --coverage.enabled=false`，25 条测试全部通过。
- `cd frontend && pnpm exec eslint src/pages/admin/ai/AiCenterPage.vue test/unit/ai-pages.test.js`：通过，无错误或警告。
- `git diff --check`：通过。

## 未验证范围和风险

- 尚未执行全量前端测试、生产构建和真实浏览器窄屏验证。
- 审计请求失败状态仍沿用既有处理方式，本次未扩展错误展示。
