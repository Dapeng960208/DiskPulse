# 用户目录详情容量趋势布局交付

## 范围

- 修复用户目录详情“容量趋势”页签的图表和告警表延伸至应用页脚的问题。

## 已完成

- 为用户目录详情建立受限的标签页和容量趋势 flex 高度链。
- 启用实时组件填充模式，使趋势图和告警表只占据内容区剩余高度。
- 增加布局回归测试，防止页脚溢出再次出现。

## 验证

- RED：`cd frontend && npx vitest run test/unit/usage-detail-realtime-layout.test.js --coverage.enabled=false`，缺少布局链时按预期失败。
- GREEN：`cd frontend && npx vitest run test/unit/usage-detail-realtime-layout.test.js test/unit/usage-related-data.test.js --coverage.enabled=false`，9 项通过。
- ESLint：`cd frontend && npx eslint src/pages/usage/UsageDetailPage.vue test/unit/usage-detail-realtime-layout.test.js`，通过。
- 生产构建：`cd frontend && npm run build:prod`，通过；仅保留既有的 ECharts 产物体积告警。

## 未验证范围与风险

- Mock 用户目录详情因权限响应弹出提示，未能用真实趋势样本完成浏览器视觉复测；布局测试已覆盖高度链契约。
- 未运行全量 Vitest 与覆盖率门禁。
