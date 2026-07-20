# 开发跟踪记录：登录页演示账户 Mock 可见性

- 会话：`2026-07-20-login-demo-accounts-mock-visibility`
- 状态：已交付
- 范围：登录页演示账户快捷入口的 Mock 模式可见性。

已完成能力见[当前能力](../../../overview/product/current-capabilities.md)。

## 已完成

- 修复 `LoginPage.vue` 将 `mockEnabled` 函数对象作为条件的问题，改为调用 `mockEnabled()`。
- 真实 API 模式不再渲染演示账户区域；`pnpm mock` 的 Mock 模式继续显示四个演示账户快捷入口并填充对应演示凭据。
- 新增组件回归测试，覆盖真实 API 模式隐藏与 Mock 模式显示。

## 验证

- TDD RED：`pnpm exec vitest run test/unit/auth-login.test.js --coverage.enabled=false` 在修复前按预期失败，断言真实 API 模式仍错误显示演示账户。
- TDD GREEN：`pnpm exec vitest run test/unit/auth-login.test.js test/unit/mock-runtime.test.js --coverage.enabled=false`，`23 passed`。
- `pnpm run lint` 通过。
- `pnpm run build:test` 通过；仅保留既有大 chunk 警告。
- 内置 Browser 分别验证真实 API 模式 `http://127.0.0.1:5175/` 与 Mock 模式 `http://127.0.0.1:5174/`：前者只显示登录控件，后者显示四个演示账户；点击“演示只读成员”后用户名为 `demo-reader`，两页控制台均无相关 warning 或 error。

## 未验证范围与风险

- 未提交真实 LDAP 凭据或连接真实后端执行登录；本次不改变认证请求或服务端授权。
- 未运行前端全量测试与全量覆盖率命令，遵循小型前端修复的聚焦验证策略；未覆盖页面的既有回归仍不在本次范围。
