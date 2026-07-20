# 项目实时使用内容区填充交付

## 范围

- 修复项目详情“项目使用实时”页签的趋势图和告警表未撑满内容区问题。

## 已完成

- 为 `ProjectDiskUsage.vue` 建立显式全高 flex 根节点，并让实时组件占用其全部剩余空间。
- 增加布局回归测试，防止异步页签内容再次失去确定高度。

## 验证

- RED：`cd frontend && npx vitest run test/unit/project-realtime-fill-content.test.js --coverage.enabled=false`，在缺少全高根节点时按预期失败。
- GREEN：`cd frontend && npx vitest run test/unit/project-realtime-fill-content.test.js test/unit/project-context-tabs.test.js --coverage.enabled=false`，9 项通过。
- ESLint：`cd frontend && npx eslint src/pages/project/components/ProjectDiskUsage.vue test/unit/project-realtime-fill-content.test.js`，通过。
- 生产构建：`cd frontend && npm run build:prod`，通过；仅保留既有的 ECharts 产物体积告警。
- 浏览器：Mock 模式 `http://localhost:5174/project/1` 的 2048×730 视口确认“项目使用实时”页签根节点、实时组件和工作区高度连续；趋势图与告警表卡片填充剩余内容区。

## 未验证范围与风险

- 未运行全量前端覆盖率门禁。
- 未连接真实后端复核真实趋势数据；Mock 已覆盖正常趋势和空告警表。
