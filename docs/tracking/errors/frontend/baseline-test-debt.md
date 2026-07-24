# 前端全量与覆盖率曾保留既有失败

## 错误内容

`pnpm test` 和扩展前端测试曾保留既有失败：操作按钮测试桩、LDAP 旧入口断言、AI Chat 缺 active Pinia、授权 mock 缺少 `getToken`，以及对 Windows CRLF 敏感的静态断言。共享契约变化后没有同步测试替身，使全量测试无法稳定充当回归门禁。2026-07-24 的存储集群健康分析测试还使用会渲染全部 slot 的 `ElTabPane` stub，提前触发本应惰性加载的异步面板；卸载后该导入可能访问 `users-api.js`，导致并行全量运行偶发 `CrudApi extends BaseApi` 初始化错误。

## 解决方案

同步公共组件 stub、Pinia 插件、认证 mock、排序预期和行为断言；删除对已废弃入口及源码形态的依赖。对于 lazy tab，测试只应 stub 异步子面板而不应让测试用 pane 触发不活跃 tab 的导入。修复后必须重新运行全量测试与覆盖率，不能只依赖聚焦测试。

## 备注

- 分类：`frontend`
- 出现次数：12
- 首次出现：2026-07-20 导航信息架构会话
- 最近出现：2026-07-24 Main 分支代码审查问题修复会话
- 出现记录：`sessions/2026-07-20-navigation-information-architecture/errors.md`
- 出现记录：`sessions/2026-07-20-project-usage-reader-default/errors.md`
- 出现记录：`sessions/2026-07-20-realtime-layout-audit/errors.md`；`detail-capacity-prediction-navigation.test.js` 在收集阶段经由 `AppHeader.vue -> users-api.js` 报 `CrudApi` 基类为 `undefined`，与本次实时布局变更无关。
- 出现记录：`sessions/2026-07-20-recent-code-review-remediation/errors.md`；本次统一修复过时 stub、Pinia 和认证 mock 后，全量测试恢复通过。
- 出现记录：`sessions/2026-07-23-system-event-association-guidance/errors.md`；覆盖率全量门禁再次出现列表权限源码契约、页面矩阵数量契约等既有失败，并在并行收集阶段再次出现 `CrudApi` 基类为 `undefined`，与本次系统事件关联提示改动无关。
- 出现记录：`sessions/2026-07-23-incident-association-clarity/errors.md`；Incident 抽屉浏览器冒烟期间，Vite 热更新经 `users-api.js` 再次出现 `CrudApi` 初始化顺序错误，完整刷新后恢复。
- 出现记录：`sessions/2026-07-23-global-table-style-audit/errors.md`；全量 `pnpm test` 出现 10 项失败，其中 3 项表格迁移旧断言已修复并由 22 项聚焦测试验证，剩余 7 项为路由数量基线、列表操作权限断言及用户未提交的存储集群详情列宽与响应式类变更。
- 出现记录：`sessions/2026-07-23-ai-model-reasoning-effort/errors.md`；`pnpm run test:coverage` 再次被非 AI 基线失败阻断，包括页面矩阵 27/30、列表动作权限 4 个断言、存储集群健康分析 2 个断言，以及 `CrudApi extends BaseApi` 异步 rejection。
- 出现记录：`sessions/2026-07-24-unified-time-range-picker/errors.md`；`storage-cluster-health-analytics.test.js` 的两项既有断言仍与页面当前实现不一致：关联类型列最小宽度期望为 120、实际为 50，且系统事件低频列缺少期望的响应式 class。与统一时间范围选择器无关。
- 出现记录：`sessions/2026-07-24-event-audit-incident-noise/errors.md`；扩展 Vitest 的 `content-spacing-contract.test.js` 仍以既有页面矩阵 `27/30` 失败，审计研判跳转、项目滚动和布局用例均通过，与本次变更无关。
- 出现记录：`sessions/2026-07-24-code-review-fixes/errors.md`；时间范围 RED 验证同时运行存储集群健康分析全文件，既有的关联类型列宽和响应式 class 两项断言仍失败；时间范围组件及页面上限契约的精确测试均已通过。
- 出现记录：`sessions/2026-07-24-merge-duplicate-routes/errors.md`；`pnpm run test:coverage` 仍被页面矩阵 27/30、列表操作权限、AI 审计交互、存储集群健康分析断言及 `CrudApi extends BaseApi` 异步 rejection 阻断；路由聚焦测试与构建均通过。
- 出现记录：`sessions/2026-07-24-router-transactions-startup-security/errors.md`；全量 `pnpm test` 的页面矩阵、列表菜单、AI 表单与系统事件窄屏契约均已同步当前实现；另将 inactive lazy tab 显式 stub，消除卸载后的异步 API 导入，`pnpm test` 和 `pnpm test:coverage` 均恢复通过。
