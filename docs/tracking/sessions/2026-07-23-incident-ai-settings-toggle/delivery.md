# 交付记录：事件 AI 设置开关

## 范围

- 修复事件 AI 设置对话框关闭 Agent 后未将状态写回父页面的问题。

## 完成项

- 事件中心监听 `IncidentAiSettingsDialog` 的 `update:settings` 事件，并更新 AI 设置草稿。
- 增加关闭 Agent 并保存 `enabled: false` 的回归测试。

## 验证

- RED：`cd frontend; pnpm exec vitest run test/unit/IncidentCenterPage.test.js --coverage.enabled=false`：关闭开关后 `enabled` 仍为 `true`。
- GREEN：`cd frontend; pnpm exec vitest run test/unit/IncidentCenterPage.test.js test/unit/api/modules.test.js --coverage.enabled=false`：9 passed。
- `cd frontend; pnpm exec eslint src/pages/incident/IncidentCenterPage.vue`：通过。
- `git diff --check`：通过。

## 未验证范围与风险

- 未运行全量前端测试、覆盖率、构建或真实后端联调；仅修复前端草稿状态回写，既有 API、权限和服务端启用校验不变。
