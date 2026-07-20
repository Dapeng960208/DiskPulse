# 可复现错误总表

AI 在每次记录可复现错误后自动维护本表。出现次数必须等于对应错误事实文档“备注”中的出现记录数；按次数降序，次数相同时按最近一次出现时间降序。

| 错误标题 | 链接 | 出现次数 |
| --- | --- | ---: |
| 前端全量与覆盖率保留既有失败 | [错误详情](./frontend/baseline-test-debt.md) | 3 |
| 项目详情表格纵向滚动被隐藏导致分页不可达 | [错误详情](./frontend/project-detail-table-pagination-scroll-trap.md) | 2 |
| QuestDB 派生监控任务使用 `timestamptz` 绑定参数 | [错误详情](./backend/questdb-timestamptz-parameter-binding.md) | 2 |
| 静态源码换行断言与 Windows CRLF 不兼容 | [错误详情](./frontend/static-source-line-ending-assertion.md) | 2 |
| 存储集群实时趋势测试仍按 GB 断言 | [错误详情](./backend/storage-cluster-realtime-unit-assertion.md) | 1 |
| 项目负责人未获得项目组配额调整能力 | [错误详情](./backend/group-owner-quota-capability.md) | 1 |
| 项目组编辑回传只读响应字段导致 422 | [错误详情](./frontend/group-update-read-only-payload-validation.md) | 1 |
| AI 工具编排重复请求已成功结果 | [错误详情](./backend/ai-tool-orchestration-repeats-success.md) | 1 |
| 资源表单测触发请求层与路由循环依赖 | [错误详情](./frontend/resource-tab-test-router-cycle.md) | 1 |
| AI 流式异常未写入服务端日志 | [错误详情](./backend/ai-stream-exception-not-logged.md) | 1 |
| AI 流式空 choices 状态帧导致对话失败 | [错误详情](./backend/ai-stream-empty-choices-frame.md) | 1 |
| 用户目录容量趋势延伸到页脚 | [错误详情](./frontend/usage-detail-realtime-footer-overflow.md) | 1 |
| 项目实时使用页签未传递完整内容高度 | [错误详情](./frontend/project-realtime-tab-content-height.md) | 1 |
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
