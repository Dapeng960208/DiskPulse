# FastAPI 同步 yield 依赖跨线程重置 ContextVar 失败

## 标题

FastAPI 同步 `yield` 依赖的 `ContextVar` token 在退出时可能处于不同线程上下文，调用 `reset()` 会失败。

## 错误内容

在函数级数据库事务依赖中创建 token，路径函数完成后重置时出现：`ValueError: Token ... was created in a different Context`。异常会把原本成功或预期的 HTTP 响应转换为 500。

## 解决方案

不要用跨越同步 `yield` 依赖生命周期的 `ContextVar` token 保存 Router 事务状态。事务依赖直接对请求 session 提交或回滚；需要分段持久化的流程调用无状态的 `router_transaction` 检查点函数。

## 备注

- 出现次数：1。
- 2026-07-24，`2026-07-24-router-transactions-startup-security`：Router 事务重构期间，新增 `ContextVar` 事务状态在 FastAPI 同步依赖退出时触发该错误；改为无状态检查点适配器并通过 211 项聚焦回归验证。
