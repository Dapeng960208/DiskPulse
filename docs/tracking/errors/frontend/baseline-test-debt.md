# 前端全量与覆盖率曾保留既有失败

## 错误内容

`pnpm test` 和扩展前端测试曾保留既有失败：操作按钮测试桩、LDAP 旧入口断言、AI Chat 缺 active Pinia、授权 mock 缺少 `getToken`，以及对 Windows CRLF 敏感的静态断言。共享契约变化后没有同步测试替身，使全量测试无法稳定充当回归门禁。

## 解决方案

同步公共组件 stub、Pinia 插件、认证 mock、排序预期和行为断言；删除对已废弃入口及源码形态的依赖。修复后必须重新运行全量测试与覆盖率，不能只依赖聚焦测试。

## 备注

- 分类：`frontend`
- 出现次数：5
- 首次出现：2026-07-20 导航信息架构会话
- 最近出现：2026-07-20 近三日代码审查修复会话
- 出现记录：`sessions/2026-07-20-navigation-information-architecture/errors.md`
- 出现记录：`sessions/2026-07-20-project-usage-reader-default/errors.md`
- 出现记录：`sessions/2026-07-20-realtime-layout-audit/errors.md`；`detail-capacity-prediction-navigation.test.js` 在收集阶段经由 `AppHeader.vue -> users-api.js` 报 `CrudApi` 基类为 `undefined`，与本次实时布局变更无关。
- 出现记录：`sessions/2026-07-20-recent-code-review-remediation/errors.md`；本次统一修复过时 stub、Pinia 和认证 mock 后，全量测试恢复通过。
- 出现记录：`sessions/2026-07-23-system-event-association-guidance/errors.md`；覆盖率全量门禁再次出现列表权限源码契约、页面矩阵数量契约等既有失败，并在并行收集阶段再次出现 `CrudApi` 基类为 `undefined`，与本次系统事件关联提示改动无关。
