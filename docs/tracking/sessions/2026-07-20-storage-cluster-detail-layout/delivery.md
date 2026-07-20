# 存储集群详情布局修复交付

## 范围

- 移除“系统管理 → 存储集群”的三级导航栏目，将菜单改为直接打开集群列表。
- 修复集群详情筛选栏、图表和表格的内容区布局，以及详情页子栏目表格的滚动行为。

## 已完成

- 保留现有容量池、存储空间和 Qtree 路由与深链，但从侧栏隐藏。
- 将共享时间筛选栏移出 `ElTabs` 内容区，避免与页签内容争夺 flex 可用空间。
- 存储分布图按内容区高度渲染；容量趋势、性能分析、故障分析和关联事件可正常显示。
- 详情页和资源子栏目表格禁用横向滚动；窄宽度按共享响应式策略隐藏次要列。

## 验证

- `cd frontend && pnpm exec vitest run test/unit/pages/storage-cluster-health-analytics.test.js test/unit/storage-cluster-resource-tab-scroll.test.js test/unit/router/routes.test.js test/unit/pages/cluster-resource-list-tab.test.js test/unit/ClusterIncidentsTab.test.js --coverage.enabled=false`
- `cd frontend && pnpm exec eslint src/router/routes.js src/pages/admin/storage-cluster/StorageClusterDetailPage.vue src/pages/admin/storage-cluster/components/ClusterResourceListTab.vue src/pages/admin/storage-cluster/components/ClusterIncidentsTab.vue`
- `cd frontend && pnpm run build:test`
- mock 浏览器验证 `http://localhost:5174/admin/storage-cluster/1`：侧栏、容量趋势、存储分布、性能分析、故障分析、关联事件及三类资源表均已检查。

## 未验证范围与风险

- 未使用真实 LDAP 会话和生产存储数据；真实 API 返回的长文本需在部署环境继续观察。
- 390px 视口下现有应用外层侧栏仍占用较多宽度，属于全局 AppLayout 的既有响应式行为，本次未扩展修改其范围。
