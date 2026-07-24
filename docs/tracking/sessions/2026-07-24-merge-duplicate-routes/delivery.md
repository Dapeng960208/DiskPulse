# 前端路由重复定义合并

- 会话：`2026-07-24-merge-duplicate-routes`
- 状态：已交付
- 范围：合并 `frontend/src/router/routes.js` 中重复的根路径 `AppLayout` 路由记录，不改变既有路由的公开行为。

## 已完成

- 将 6 个 `path: '/'` 且使用 `AppLayout` 的根路由记录合并为 1 个记录；其子路由保留原有顺序、名称、路径、重定向、元数据、权限策略和懒加载页面。
- 新增路由配置契约：所有工作区页面必须位于同一个根布局记录下，防止重复定义回归。
- TDD 检查点：`d0476c9`（RED，用例确认原配置包含 6 个根布局记录）与 `064009b`（GREEN，聚焦路由测试通过）。

## 验证

- `cd frontend; pnpm exec vitest run test/unit/router/routes.test.js test/unit/router/routes-dynamic-import.test.js --coverage.enabled=false`
  - 结果：2 个文件、15 项测试通过。
- `cd frontend; pnpm run build:test`
  - 结果：通过；仅保留现有大体积 chunk 警告。
- `git diff --check`
  - 结果：通过。

## 未验证范围与风险

- `pnpm run lint` 被 `src/pages/incident/components/IncidentAiSettingsDialog.vue:28` 的既有 `vue/first-attribute-linebreak` 错误阻断；该文件未在本会话修改。
- `pnpm run test:coverage` 仍被既有全量测试债务阻断；路由相关聚焦测试与构建已通过。详见[前端全量与覆盖率曾保留既有失败](../../errors/frontend/baseline-test-debt.md)。
- 未执行浏览器 E2E 或真实后端鉴权联调；本次只重组等价路由配置，未改动 URL、权限或接口。
