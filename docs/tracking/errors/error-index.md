# 可复现错误总表

AI 在每次记录可复现错误后自动维护本表。出现次数必须等于对应错误事实文档“备注”中的出现记录数；按次数降序，次数相同时按最近一次出现时间降序。

| 错误标题 | 链接 | 出现次数 |
| --- | --- | ---: |
| 前端全量与覆盖率曾保留既有失败 | [错误详情](./frontend/baseline-test-debt.md) | 8 |
| 独立后端检查在 worktree 缺少默认配置 | [错误详情](./backend/worktree-config-yml-missing.md) | 4 |
| 项目负责人配额能力测试混淆资源授权边界 | [错误详情](./backend/group-owner-quota-capability.md) | 3 |
| 存储集群实时趋势测试仍按 GB 断言 | [错误详情](./backend/storage-cluster-realtime-unit-assertion.md) | 3 |
| 时间转换隐式依赖或误解释应用时区 | [错误详情](./backend/host-timezone-dependent-datetime-normalization.md) | 2 |
| 项目资源实时页签未传递完整内容高度 | [错误详情](./frontend/project-realtime-tab-content-height.md) | 2 |
| 项目详情表格纵向滚动被隐藏导致分页不可达 | [错误详情](./frontend/project-detail-table-pagination-scroll-trap.md) | 2 |
| QuestDB 派生监控任务使用 `timestamptz` 绑定参数 | [错误详情](./backend/questdb-timestamptz-parameter-binding.md) | 2 |
| 静态源码换行断言与 Windows CRLF 不兼容 | [错误详情](./frontend/static-source-line-ending-assertion.md) | 2 |
| Mock 未将 `/v1/admin` 资源纳入超级管理员边界 | [错误详情](./frontend/mock-v1-admin-authorization.md) | 1 |
| Vue 模板属性未按仓库 ESLint 换行规则书写 | [错误详情](./frontend/vue-attribute-line-lint.md) | 1 |
| PostgreSQL 对含 JSON 的整行执行 DISTINCT 失败 | [错误详情](./backend/postgresql-json-row-distinct-unsupported.md) | 1 |
| QuestDB 重建 SQL 未引用保留字列名 | [错误详情](./backend/questdb-repair-reserved-column-unquoted.md) | 1 |
| QuestDB 修复脚本拒绝纯数字时间后缀 | [错误详情](./backend/questdb-repair-numeric-suffix-rejected.md) | 1 |
| 批量平移事件时间桶触发即时唯一键冲突 | [错误详情](./backend/incident-bucket-shift-immediate-unique-collision.md) | 1 |
| Celery 控制命令没有收到节点回复 | [错误详情](./backend/celery-control-no-node-reply.md) | 1 |
| 后端脚本按文件路径启动时无法导入项目模块 | [错误详情](./backend/python-script-direct-entrypoint-import-path.md) | 1 |
| QuestDB 不支持 PostgreSQL 聚合 `FILTER` 语法 | [错误详情](./backend/questdb-filter-aggregate-unsupported.md) | 1 |
| 已审核厂商事件测试夹具缺少必填处置方案 | [错误详情](./backend/reviewed-vendor-event-fixture-missing-solution.md) | 1 |
| 当前开发环境缺少 Docker CLI | [错误详情](./environment/docker-cli-unavailable.md) | 1 |
| Celery 任务被覆盖率配置排除 | [错误详情](./backend/celery-task-coverage-excluded.md) | 1 |
| 聚焦 Vitest 覆盖率套用全局阈值 | [错误详情](./frontend/focused-vitest-global-coverage-threshold.md) | 1 |
| PostgreSQL 显式 ID 种子后序列未同步 | [错误详情](./backend/postgresql-sequence-after-explicit-seed.md) | 1 |
| Tooltip 同时使用 focus 与 click 导致点击后立即关闭 | [错误详情](./frontend/tooltip-focus-click-trigger-conflict.md) | 1 |
| CI 混用前端包管理器与过期锁文件 | [错误详情](./frontend/ci-package-manager-lockfile-drift.md) | 1 |
| 横切 API 与迁移契约变化后测试预期未同步 | [错误详情](./backend/cross-cutting-contract-test-drift.md) | 1 |
| 前端函数覆盖率低于全局门禁 | [错误详情](./frontend/function-coverage-threshold.md) | 1 |
| lodash 安全 override 缺少 fromPairs 内部导入 | [错误详情](./frontend/secure-lodash-override-import-regression.md) | 1 |
| 镜像仓库缺少 pnpm 安全审计端点 | [错误详情](./frontend/dependency-audit-registry-endpoint.md) | 1 |
| 统一审计时间原样展示且请求/触发方与摘要不明确 | [错误详情](./frontend/audit-event-presentation-context.md) | 1 |
| 事件中心按编辑时间排序且技术关联上下文缺失 | [错误详情](./frontend/incident-event-chronology-and-technical-context.md) | 1 |
| 项目组编辑回传只读响应字段导致 422 | [错误详情](./frontend/group-update-read-only-payload-validation.md) | 1 |
| AI 工具编排重复请求已成功结果 | [错误详情](./backend/ai-tool-orchestration-repeats-success.md) | 1 |
| 资源表单测触发请求层与路由循环依赖 | [错误详情](./frontend/resource-tab-test-router-cycle.md) | 1 |
| AI 流式异常未写入服务端日志 | [错误详情](./backend/ai-stream-exception-not-logged.md) | 1 |
| AI 流式空 choices 状态帧导致对话失败 | [错误详情](./backend/ai-stream-empty-choices-frame.md) | 1 |
| 用户目录容量趋势延伸到页脚 | [错误详情](./frontend/usage-detail-realtime-footer-overflow.md) | 1 |
| 普通 CSS 中的嵌套规则未生效 | [错误详情](./frontend/plain-css-nesting-not-compiled.md) | 1 |
| 存储树图可见阈值隐藏常规容量 | [错误详情](./frontend/storage-treemap-visibility-threshold.md) | 1 |
| Mock 项目存储树响应未覆盖分布图契约 | [错误详情](./frontend/mock-project-storage-tree-contract.md) | 1 |
| 当前 Vitest 断言扩展不支持单次组合调用 | [错误详情](./frontend/vitest-single-call-matcher-unavailable.md) | 1 |
| 项目趋势未写入 QuestDB | [错误详情](./backend/project-trend-not-written-to-questdb.md) | 1 |
| 前端构建脚本名不一致 | [错误详情](./frontend/frontend-build-script-name.md) | 1 |
| AI 历史回复缺少范围标记导致超级管理员被隐藏 | [错误详情](./backend/ai-legacy-history-superadmin-hidden.md) | 1 |
| 审计事件资源 ID 响应类型不一致 | [错误详情](./backend/audit-event-resource-id-response-type.md) | 1 |
| Mock 模式开关函数引用导致演示账户泄漏 | [错误详情](./frontend/mock-login-visibility-function-reference.md) | 1 |
| 预测发布开关错误阻断关联事件 | [错误详情](./backend/prediction-toggle-blocks-related-incidents.md) | 1 |
| 并发分页旧响应覆盖当前页 | [错误详情](./frontend/stale-pagination-response.md) | 1 |
| 最终预测使用历史项目快照授权 | [错误详情](./backend/final-prediction-historical-project-authorization.md) | 1 |
| 懒加载路由测试缺少页面 Mock | [错误详情](./frontend/lazy-route-test-mock-missing.md) | 1 |
| 前端 Vitest 从仓库根目录运行 | [错误详情](./frontend/vitest-working-directory.md) | 1 |
| 系统 Python 或 pytest 命令不可用 | [错误详情](./environment/python-test-command.md) | 1 |
| 将本地自动化等同于外部集成验收 | [错误详情](./integration/external-verification.md) | 1 |
| 使用前端 Mock 代替授权验证 | [错误详情](./frontend/mock-not-authorization.md) | 1 |
