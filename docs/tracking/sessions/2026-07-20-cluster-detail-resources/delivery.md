# 集群详情资源页签交付记录

## 范围

- 在存储集群详情页增加当前集群的容量池、存储空间和 Qtree（NetApp）页签。
- 保持容量池、存储空间和 Qtree 的独立列表页组件、路由和管理入口不变。

## 已完成

- 新增按需加载的集群资源表，所有请求固定传递当前 `storage_cluster_id`。
- Isilon 集群不显示且不请求 Qtree。
- 资源表沿用 `QueryForm`、`DataTable`、资源详情链接、字段级容量单位和友好失败态；Qtree 可按所属存储空间筛选。
- 沿用集群详情的动态面包屑标题；资源筛选、受限内容区与底部分页结构参考现有项目详情页签实现。

## 验证

- `pnpm exec vitest run test/unit/StorageClusterDetailPage.test.js test/unit/pages/cluster-resource-list-tab.test.js test/unit/pages/storage-cluster-health-analytics.test.js test/unit/content-spacing-contract.test.js test/unit/components/query-form.test.js --coverage.enabled=false`：36 项通过。
- `pnpm run lint`：通过。
- `pnpm run build:prod`：通过；仅保留既有 `%VITE_APP_TITLE%` 未定义与大体积 chunk 警告。

## 未验证范围与风险

- 尚未连接真实 NetApp 或 Isilon 设备；本次仅复用既有资源 API，无后端或数据契约改动。
- 应用内浏览器无法连接本机 Vite 端口，未能完成截图与交互级渲染验证；聚焦单测、lint 和生产构建均已通过。
