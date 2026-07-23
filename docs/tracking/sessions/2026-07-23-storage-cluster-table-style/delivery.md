# 存储集群详情表格样式交付

## 范围

- 将存储集群详情页自有的性能、重复故障和系统事件列表接入共享 `DataTable`。
- 移除页面级表格容器、Element Plus 表格深层覆盖和独立分页样式。
- 保留业务布局、响应式列、固定操作列和系统事件服务端分页行为。

## 已完成

- 新增静态架构回归测试，约束页面表格必须使用共享组件且不得恢复页面级表格样式覆盖。
- 系统事件分页改为通过 `DataTable` 的 `update:pagination` 事件刷新数据。
- 同步存储集群功能事实文档。

## 验证

- `cd frontend && pnpm exec vitest run test/unit/pages/storage-cluster-health-analytics.test.js --coverage.enabled=false`：18 项通过。
- `cd frontend && pnpm exec eslint src/pages/admin/storage-cluster/StorageClusterDetailPage.vue test/unit/pages/storage-cluster-health-analytics.test.js`：通过，测试文件保留 14 条既有单文件多组件警告，无错误。
- `cd frontend && pnpm run build:prod`：通过；保留既有大 chunk 提示。
- `cd frontend && pnpm exec vitest run test/unit/pages/storage-cluster-health-analytics.test.js --coverage`：18 项通过，目标页面 Statements/Lines 97.32%、Functions 84.09%、Branches 69.34%；命令因未执行的全局源文件计为 0% 而未通过全局 80% 阈值。

## 未验证范围与风险

- 未运行前端全量测试或全量覆盖率；本次按小范围样式修复执行聚焦验证。
- 未执行部署环境浏览器冒烟。
- 未连接真实 NetApp 或 PowerScale；本次不改变 API、采集或数据口径。
