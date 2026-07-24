# 交付记录

## 范围

- [完成] 新增 `TimeRangePicker` 统一全站日期时间范围选择器，并提供 1 天、3 天、1 周、1 个月、3 个月、6 个月和 1 年快捷范围。
- [完成] 替换实时监控、存储集群健康分析、存储空间监控和操作审计的范围查询入口；维护窗口等单点时间输入保持原行为。
- [完成] 将快捷范围收敛到 `utils/time-range.js`，移除页面级重复配置和“8小时内”快捷项。

## 验证

- RED：`pnpm exec vitest run test/unit/utils/time-range.test.js --coverage.enabled=false` 按预期失败，原快捷项仅 5 项；新增组件与覆盖测试也因组件和页面引用尚不存在而按预期失败。
- GREEN：`pnpm exec vitest run test/unit/utils/time-range.test.js test/unit/components/time-range-picker.test.js test/unit/time-range-picker-coverage.test.js test/unit/components/query-form.test.js test/unit/page-coverage-gaps.test.js test/unit/volume-monitoring-page.test.js test/unit/incident-and-audit-list-layout.test.js --coverage.enabled=false`，31 项断言全部通过。
- GREEN：`pnpm exec vitest run test/unit/pages/storage-cluster-health-analytics.test.js --coverage.enabled=false -t "shows storage distribution beside capacity|renders the shared time filter|loads performance and fault data lazily"`，3 项范围相关断言通过。
- 通过：`pnpm exec eslint src/components/form/TimeRangePicker.vue src/utils/time-range.js src/pages/common/RealTimePage.vue src/pages/admin/storage-cluster/StorageClusterDetailPage.vue src/pages/admin/volume/VolumeMonitoringPage.vue src/pages/admin/audit/AuditEventListPage.vue`。
- 通过：`pnpm run build:test`。
- 通过：`git diff --check`；检索确认唯一的 `datetimerange` 位于 `TimeRangePicker`，其余 `ElDatePicker` 均为单点时间输入。
- 未通过（既有）：`pnpm run lint` 被 `IncidentAiSettingsDialog.vue:28` 的未改动属性换行规则错误阻断，已记录在本会话错误记录。
- 未通过（既有）：完整存储集群健康分析套件有两项事件表格断言与页面当前实现不一致，已记录在本会话错误记录。

## 未验证范围与风险

- 未运行完整 `pnpm test` 与覆盖率门禁：本次为范围选择器的聚焦改动，且已确认存在无关的前端基线失败。
- 未在真实登录态浏览器中逐页打开 Element Plus 弹出层；测试构建已验证组件可编译，实际视觉表现仍建议在部署环境复核。
- 月度与年度快捷范围沿用现有产品约定，分别按 30、90、180 和 365 天回溯，不按自然月边界计算。
