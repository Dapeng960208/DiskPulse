# 用户目录额度调整与 AI 反馈交付记录

## 范围

- 用户目录详情不重复显示“调整额度”；项目详情“用户目录”页签的最右侧操作列按 `capabilities.adjust_quota` 提供该入口。
- 用户目录详情各页签横向撑满可用内容区，修复“配额历史”右侧留白；项目列表移除无意义的页签导航和“项目存储概览图”。
- 未指定软限额时默认使用硬限额的 90%；Isilon 默认使用 7 天软限额宽限期。
- AI 确认执行额度调整后显示设备执行成功或失败结果。

## 状态

已完成：

- 项目详情“用户目录”在拥有 `adjust_quota` 能力时于操作列显示“调整额度”操作，并复用现有调整对话框；用户目录详情不重复显示该入口。
- 项目列表直接显示项目表格；项目详情中的“项目使用实时”和“存储分布”保持不变。
- 服务端在支持软限额的目标未传软限额时补充硬限额的 90%；Isilon 软限额存在但未传宽限期时补充 7 天。
- AI 额度确认卡在确认、取消和失败后都显示明确结果。

## 验证与风险

- 后端：`backend/test/test_quota_adjustment.py`。
- 前端：配额调整、用户目录权限显示和 AI 确认反馈的定向 Vitest 用例。
- 前端布局：`pnpm exec vitest run test/unit/usage-detail-field-visibility.test.js test/unit/usage-detail-realtime-layout.test.js test/unit/project-context-tabs.test.js test/unit/realtime-page-height-contract.test.js --coverage.enabled=false`，通过。
- ESLint：`pnpm exec eslint src/pages/usage/UsageDetailPage.vue src/pages/project/ProjectListPage.vue src/pages/project/components/ProjectUsagesTab.vue test/unit/usage-detail-field-visibility.test.js test/unit/usage-detail-realtime-layout.test.js test/unit/project-context-tabs.test.js test/unit/realtime-page-height-contract.test.js`，通过。
- 构建：`pnpm run build:prod`，通过；仅有既有的 ECharts 产物大于 500 KB 警告。
- 浏览器：Mock 模式 `http://127.0.0.1:5174/projects` 确认项目页不再有页签导航；`/project/1` 的“用户目录”页签确认最右操作列“调整额度”可打开调整对话框。
- 真实 NetApp/Isilon 设备写入及 Provider 触发的 AI 确认卡仍需在隔离集成环境验证。
- Mock 中 `/usage/1` 没有配额调整能力，访问详情“配额历史”会返回预期的 403；横向撑满契约已由布局回归测试覆盖。
- 本会话代码变更已进入 `main`；本交付目录因当时存在无关暂存修改而延后记录，现经后续审查确认内容与当前实现一致后单独补交。
