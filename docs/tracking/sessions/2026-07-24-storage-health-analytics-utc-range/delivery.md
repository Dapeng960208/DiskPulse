# 交付记录

## 范围

- [完成] 存储集群容量、性能、故障分析请求将用户时区的本地范围转换为 RFC 3339 UTC `Z` 边界。
- [完成] 健康分析报告导出使用同一时间范围转换，避免导出接口返回 422。
- [完成] 记录无时区时间范围导致健康分析 422 的根因与修复契约。

## 验证

- RED：`cd frontend; pnpm test -- test/unit/pages/storage-health-analytics-time-range.test.js`；修复前实际发送 `2026-07-24 08:27:54`，而测试要求 `2026-07-24T00:27:54Z`。
- GREEN：`cd frontend; pnpm test -- test/unit/pages/storage-health-analytics-time-range.test.js test/unit/composables/use-cluster-export.test.js`；2 个测试通过。
- 通过：`cd frontend; pnpm exec eslint src/pages/admin/storage-cluster/components/ClusterCapacityTab.vue src/pages/admin/storage-cluster/components/ClusterPerformanceTab.vue src/pages/admin/storage-cluster/components/ClusterFaultsTab.vue src/composables/useClusterExport.js test/unit/pages/storage-health-analytics-time-range.test.js test/unit/composables/use-cluster-export.test.js test/unit/pages/storage-cluster-health-analytics.test.js`；无错误，旧父页面测试产生 14 条已有组件数量警告。
- 通过：`cd frontend; pnpm run build:test`；Vite 测试构建成功。
- 未通过（既有）：`cd frontend; pnpm test -- test/unit/pages/storage-cluster-health-analytics.test.js`；旧父页面测试未挂载异步子页签，18 项中 15 项失败，已记录为前端测试基线债务。

## 未验证范围与风险

- 未运行完整前端测试、覆盖率或真实登录态浏览器回归；本次只覆盖健康分析与导出的聚焦时间参数契约。
- 既有的父页面健康分析测试仍需后续迁移为直接测试子页签，避免异步组件自动桩掩盖实际请求行为。
- 已保留工作区原有的 4 个后端未提交改动，未纳入本次前端修复。
