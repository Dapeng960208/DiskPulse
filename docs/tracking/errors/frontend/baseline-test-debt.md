# 前端全量与覆盖率保留既有失败

## 错误内容

`pnpm test` 和 `pnpm run test:coverage` 保留 11 条已在 `main` 复现的失败：操作按钮测试桩 8 条、LDAP 旧入口断言 2 条、AI Chat 缺 active Pinia 1 条。覆盖率命令因此不输出最终汇总。

## 解决方案

当前功能使用聚焦测试、lint、生产构建和浏览器验收确认无新增失败；11 条基线债务由独立任务修复后重新运行全量与覆盖率门禁，不在无关功能提交中顺带改写。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次与最近出现：2026-07-20 导航信息架构会话
- 出现记录：`sessions/2026-07-20-navigation-information-architecture/errors.md`
