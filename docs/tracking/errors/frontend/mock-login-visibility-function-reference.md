# Mock 模式开关函数引用导致演示账户泄漏

## 错误内容

登录页模板将 `mockEnabled` 函数本身作为 `v-if` 条件。函数对象恒为真，导致未启用 `VITE_USE_MOCKS=true` 的真实 API 模式仍显示演示账户入口。

## 解决方案

在模板中调用 `mockEnabled()` 取得布尔结果，并以组件测试同时覆盖真实 API 模式隐藏、Mock 模式显示两种状态。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次与最近出现：2026-07-20
- 出现记录：`sessions/2026-07-20-login-demo-accounts-mock-visibility/errors.md`
