# 项目详情表格分页与滚动交付

## 范围

- 项目详情的用户目录、项目组、成员与权限和项目审计页签。
- 数据超过 20 条时，筛选区和底部分页固定，只有表格内容区域滚动。

## 已完成

- 共享 `DataTable` 恢复纵向滚动，并使表格包装层在 flex 内容区内可收缩。
- 四个目标页签建立受限内容高度链；成员与权限改为复用 `DataTable` 并按筛选结果分页。
- 同步项目 RBAC 前端事实文档、当前能力说明和可复用错误记录。

## 验证

- RED：`cd frontend && npx vitest run test/unit/project-members-tab.test.js test/unit/project-detail-table-scroll.test.js --coverage.enabled=false`，新增分页、受限表格区和纵向滚动契约均按预期失败。
- GREEN：`cd frontend && npx vitest run test/unit/project-members-tab.test.js test/unit/project-detail-table-scroll.test.js test/unit/project-context-tabs.test.js --coverage.enabled=false`，17 项通过。
- Lint：`cd frontend && npx eslint src/components/data/DataTable.vue src/pages/project/ProjectDetailPage.vue src/pages/project/components/ProjectGroupsTab.vue src/pages/project/components/ProjectUsagesTab.vue src/pages/project/components/ProjectMembersTab.vue src/pages/project/components/ProjectAuditTab.vue test/unit/project-members-tab.test.js test/unit/project-detail-table-scroll.test.js`，通过。
- 构建：`cd frontend && npm run build:prod`，通过；仅保留现有大 chunk 警告。
- 浏览器：Mock 模式 `http://localhost:5174/project/1` 使用演示超级管理员逐一进入“项目组、用户目录、成员与权限、项目审计”；四个页签均渲染表格，表格包装层计算样式为 `overflow-y: auto`，内容根节点为 flex 且 `min-height: 0`。390px 窄屏下页面不产生外层横向滚动，宽表保留在表格容器中横向滚动。

## 未验证范围与风险

- 未连接真实后端验证超过 20 条的服务端分页；聚焦单测覆盖了成员 21 条数据和四个页签的布局契约。
- 未运行全量 Vitest 和覆盖率门禁；本次为小范围前端布局修复，已运行受影响的聚焦测试。
