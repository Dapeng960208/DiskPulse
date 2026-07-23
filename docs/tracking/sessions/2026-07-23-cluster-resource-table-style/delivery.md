# 存储集群资源表格样式交付

- 会话：`2026-07-23-cluster-resource-table-style`
- 状态：已完成
- 范围：移除存储集群详情资源页签对共享表格滚动和单元格样式的局部覆盖。

## 已完成

- 删除资源页签对共享 `.table-wrapper` 滚动行为的覆盖。
- 删除资源页签对 Element Plus 表格内部滚动区域和单元格换行的深层覆盖。
- 保留资源页签根容器及 `.data-table-card` 的 flex、`min-height` 和高度布局，确保底部分页可达。
- 更新滚动架构回归测试，明确共享 `DataTable` 负责内容区横纵滚动。
- 同步存储集群功能事实文档。

## 验证

- `cd frontend && pnpm exec vitest run test/unit/storage-cluster-resource-tab-scroll.test.js test/unit/pages/cluster-resource-list-tab.test.js --coverage.enabled=false`：2 个测试文件、8 条用例通过。
- `cd frontend && pnpm exec eslint src/pages/admin/storage-cluster/components/ClusterResourceListTab.vue test/unit/storage-cluster-resource-tab-scroll.test.js test/unit/pages/cluster-resource-list-tab.test.js`：0 个错误；资源页签测试文件保留 5 条既有的单文件多组件警告。
- `git diff --check -- frontend/src/pages/admin/storage-cluster/components/ClusterResourceListTab.vue frontend/test/unit/storage-cluster-resource-tab-scroll.test.js docs/features/storage/cluster/overview.md docs/tracking/sessions/2026-07-23-cluster-resource-table-style/delivery.md docs/tracking/sessions/2026-07-23-cluster-resource-table-style/errors.md`：通过。

## 未验证范围和风险

- 未执行全量前端测试、覆盖率、生产构建或真实登录浏览器验证。
- 删除强制换行后，超长内容按共享 `DataTable` 和列级 `show-overflow-tooltip` 行为展示；仍需浏览器窄屏视觉复核。
