# 容量预测面板表格样式交付

## 范围

- 将完整容量预测兼容面板中的预测曲线和关联事件列表接入共享 `DataTable`。
- 保留整面板既有加载、错误、预测无结果空态和容量展示语义。
- 不改变资源详情只展示轻量耗尽风险的产品边界。

## 已完成

- 两张异步表统一使用共享 `DataTable` 的紧凑密度，并绑定同一加载状态。
- 保留现有 `ElTableColumn` 字段、容量格式化和关联事件回退文案。
- 新增静态架构与运行时数据、重新加载状态回归测试。
- 同步容量预测前端事实文档。

## 验证

- `cd frontend && pnpm exec vitest run test/unit/capacity-prediction-panel.test.js test/unit/capacity-prediction-detail-contract.test.js --coverage.enabled=false`：13 项通过。
- `cd frontend && pnpm exec eslint src/pages/capacity-prediction/CapacityPredictionPanel.vue test/unit/capacity-prediction-panel.test.js`：通过，无错误或警告。
- `git diff --check -- frontend/src/pages/capacity-prediction/CapacityPredictionPanel.vue frontend/test/unit/capacity-prediction-panel.test.js docs/features/ai/capacity-prediction/frontend.md docs/tracking/sessions/2026-07-23-capacity-prediction-panel-table-style/delivery.md docs/tracking/sessions/2026-07-23-capacity-prediction-panel-table-style/errors.md`：通过。

## 未验证范围与风险

- 未运行前端全量测试、全量覆盖率、生产构建或真实浏览器窄屏验证。
- `DataTable` 会为每张表提供统一卡片与内边距，兼容面板的纵向占用可能略有增加；当前无公开资源详情入口展示完整面板。
- 表内空数据提示改为共享 `DataTable` 的统一空态文案；面板级“暂无可用容量预测”空态保持不变。
