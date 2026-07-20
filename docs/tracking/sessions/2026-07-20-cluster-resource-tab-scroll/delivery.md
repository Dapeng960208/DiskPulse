# 集群详情资源页签滚动修复交付记录

## 范围

修复集群详情中容量池、存储空间和 Qtree（NetApp）资源页签的表格正文无法滚动、底部分页不可达的问题。不改变资源 API、筛选条件、独立列表页或 Isilon 的 Qtree 边界。

## 已完成

- 为集群详情卡片、页签、页签内容和页签面板建立可收缩的纵向 flex 高度链。
- 保持资源页签既有 `DataTable` 表格包装层滚动和底部分页结构，使表格正文在剩余内容区滚动。
- 增加静态布局契约测试，防止父级页签高度链再次缺失。

## 验证

- RED：`pnpm exec vitest run test/unit/storage-cluster-resource-tab-scroll.test.js --coverage.enabled=false`，新增布局契约因缺少卡片和页签高度链失败。
- GREEN：同一命令通过（1 个文件、1 项测试）。
- 基线：`pnpm exec vitest run test/unit/pages/cluster-resource-list-tab.test.js test/unit/StorageClusterDetailPage.test.js --coverage.enabled=false` 通过（2 个文件、9 项测试）。
- 聚焦回归：`pnpm exec vitest run test/unit/storage-cluster-resource-tab-scroll.test.js test/unit/pages/cluster-resource-list-tab.test.js test/unit/StorageClusterDetailPage.test.js test/unit/pages/storage-cluster-health-analytics.test.js test/unit/realtime-page-height-contract.test.js test/unit/project-detail-table-scroll.test.js --coverage.enabled=false` 通过（6 个文件、25 项测试）。
- 质量检查：`pnpm run lint` 与 `pnpm run build:prod` 通过；构建仅保留既有的 `%VITE_APP_TITLE%` 缺失与大 chunk 警告。
- Mock 页面检查：登录演示超级管理员后打开 `/admin/storage-cluster/1` 的“存储空间”页签；页签内容区与表格包装器均为受限高度且 `overflow-y: auto`。Mock 仅一条存储空间记录，`hideOnSinglePage` 按预期隐藏分页。

## 未验证范围与风险

- 未执行多页真实数据下的滚轮与分页点击：Mock 仅一条存储空间记录，分页按设计隐藏；高度链和分页脱离滚动包装器由布局契约测试覆盖。
- 尚未执行全量 Vitest；本次未改动 API、Mock、权限或数据模型。
