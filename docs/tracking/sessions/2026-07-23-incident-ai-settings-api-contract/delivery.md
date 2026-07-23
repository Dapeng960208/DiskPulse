# 交付记录：事件 AI 设置 API 契约

## 范围

- 修复事件中心“AI 处置设置”调用不存在 API 方法导致的运行时错误。
- 为真实 `IncidentApi` 方法名补充回归覆盖。

## 完成项

- `useIncidentAiSettings` 改为调用 `fetchAiSettings` 与 `updateAiSettings`。
- 事件中心测试改为仅暴露 API 客户端真实方法名，覆盖加载与保存设置。

## 验证

- RED：`cd frontend; pnpm exec vitest run test/unit/IncidentCenterPage.test.js --coverage.enabled=false`：1 项预期失败，真实 API 方法未被调用。
- GREEN：`cd frontend; pnpm exec vitest run test/unit/IncidentCenterPage.test.js test/unit/api/modules.test.js --coverage.enabled=false`：8 passed。
- `cd frontend; pnpm exec eslint src/composables/useIncidentAiSettings.js`：通过。
- `git diff --check`：通过。

## 未验证范围与风险

- 未运行全量前端测试、覆盖率、构建或真实后端联调；本次仅更正前端内部方法名，接口路径和权限边界未改变。
