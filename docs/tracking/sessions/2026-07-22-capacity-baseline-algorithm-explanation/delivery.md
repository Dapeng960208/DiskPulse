# 容量基线算法说明交付记录

## 范围

- 在预测治理管理页为“Theil-Sen 趋势与残差分位”增加通俗、可访问的 Tooltip。
- 在容量预测专题文档中说明稳健趋势、残差分位、未来范围和耗尽日期的计算原理与适用限制。

## 已完成

- 预测治理页为“Theil-Sen 趋势与残差分位”增加通俗算法 Tooltip。
- Tooltip 使用 Element Plus 原生 `hover` 与 `focus` 触发，图标可通过键盘聚焦，并限制浮层宽度以保证长文本可读。
- 专题文档补充日数据整理、Theil-Sen 中位斜率、残差分位、未来范围、耗尽日期和适用限制。
- 当前能力与前端展示契约已同步。

## 验证

- RED：`pnpm exec vitest run test/unit/forecast-governance-page.test.js --coverage.enabled=false`，新增 Tooltip 契约用例按预期失败，原有 9 项通过。
- GREEN：`pnpm exec vitest run test/unit/forecast-governance-page.test.js --coverage.enabled=false`，11 项全部通过。
- `pnpm exec eslint src/pages/admin/forecast-governance/ForecastGovernancePage.vue`：通过。
- `pnpm run build:prod`：通过；保留仓库既有大 chunk 警告。
- 应用内浏览器：`http://127.0.0.1:5173/admin/forecast-governance` 页面标题与内容正确；从未聚焦状态点击问号图标后焦点进入触发器，Tooltip 可见，浮层最大宽度为 `440px`，无框架错误遮罩。

## 未验证范围与风险

- 未运行前端全量测试与全量覆盖率；本次改动限定在单个治理页面、对应聚焦测试和文档。
- 浏览器控制台仍有仓库既有的 `ICarbonUserFilled` 组件解析警告，与本次 Tooltip 无关。
