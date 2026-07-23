# 存储集群关联事件表格样式交付

- 会话：`2026-07-23-cluster-incidents-table-style`
- 状态：已完成
- 范围：统一存储集群详情“关联事件”页签的表格、分页与操作列样式。

## 已完成

- 关联事件列表改用共享 `DataTable`，统一加载状态、数据展示和底部分页。
- 保留服务端分页语义；切换每页条数时回到第一页。
- 操作列继续固定在右侧，并复用全局 `.list-row-actions` 布局。
- 删除页面内的分页样式及 Element Plus 表格深层覆盖。
- 增加共享表格、分页事件、操作列和样式边界的回归测试。
- 同步存储集群健康分析事实文档。

## 验证

- `cd frontend && pnpm exec vitest run test/unit/ClusterIncidentsTab.test.js --coverage.enabled=false`：8 条用例通过。
- `cd frontend && pnpm exec eslint src/pages/admin/storage-cluster/components/ClusterIncidentsTab.vue test/unit/ClusterIncidentsTab.test.js`：0 个错误；测试文件保留 3 条既有的单文件多组件警告。
- `git diff --check -- frontend/src/pages/admin/storage-cluster/components/ClusterIncidentsTab.vue frontend/test/unit/ClusterIncidentsTab.test.js docs/features/storage/cluster/health-analytics.md docs/tracking/sessions/2026-07-23-cluster-incidents-table-style/delivery.md docs/tracking/sessions/2026-07-23-cluster-incidents-table-style/errors.md`：通过。

## 未验证范围和风险

- 未执行全量前端测试、覆盖率、生产构建或真实登录浏览器验证。
- 共享 `DataTable` 使用全局默认空态文案；本次不扩展共享组件的专用空态能力。
