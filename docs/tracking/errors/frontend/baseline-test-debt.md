# 前端全量与覆盖率保留既有失败

## 错误内容

`pnpm test` 和扩展前端测试保留既有失败：操作按钮测试桩、LDAP 旧入口断言、AI Chat 缺 active Pinia、授权 mock 缺少 `getToken`，以及对 Windows CRLF 敏感的静态断言。覆盖率命令因此可能无法输出最终汇总。

## 解决方案

当前功能使用聚焦测试、lint、生产构建和浏览器验收确认无新增失败；11 条基线债务由独立任务修复后重新运行全量与覆盖率门禁，不在无关功能提交中顺带改写。

## 备注

- 分类：`frontend`
- 出现次数：3
- 首次出现：2026-07-20 导航信息架构会话
- 最近出现：2026-07-20 实时页面布局复查会话
- 出现记录：`sessions/2026-07-20-navigation-information-architecture/errors.md`
- 出现记录：`sessions/2026-07-20-project-usage-reader-default/errors.md`
- 出现记录：`sessions/2026-07-20-realtime-layout-audit/errors.md`；`detail-capacity-prediction-navigation.test.js` 在收集阶段经由 `AppHeader.vue -> users-api.js` 报 `CrudApi` 基类为 `undefined`，与本次实时布局变更无关。
