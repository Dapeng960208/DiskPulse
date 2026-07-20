# 前端函数覆盖率低于全局门禁

## 错误内容

全量 624 个 Vitest 用例通过，但 `pnpm run test:coverage` 的 Functions 为 `78.95%`，低于全局 `80%` 阈值并以状态码 1 退出。缺口集中在 API 包装方法、路由访问策略、审计展示和表单交互函数。

## 解决方案

补充面向行为的 API 路由映射、权限策略、审计格式化、表单状态、配额对账和 v-model 测试，不降低阈值。修复后 629 个用例通过，Functions 为 `81.38%`。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次出现：2026-07-20 近三日代码审查修复会话
- 出现记录：`sessions/2026-07-20-recent-code-review-remediation/errors.md`
