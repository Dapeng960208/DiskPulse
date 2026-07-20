# 可复现错误总表

AI 在每次记录可复现错误后自动维护本表。出现次数必须等于对应错误事实文档“备注”中的出现记录数；按次数降序，次数相同时按最近一次出现时间降序。

| 错误标题 | 链接 | 出现次数 |
| --- | --- | ---: |
| 预测发布开关错误阻断关联事件 | [错误详情](./backend/prediction-toggle-blocks-related-incidents.md) | 1 |
| 前端全量与覆盖率保留既有失败 | [错误详情](./frontend/baseline-test-debt.md) | 1 |
| 并发分页旧响应覆盖当前页 | [错误详情](./frontend/stale-pagination-response.md) | 1 |
| 最终预测使用历史项目快照授权 | [错误详情](./backend/final-prediction-historical-project-authorization.md) | 1 |
| 懒加载路由测试缺少页面 Mock | [错误详情](./frontend/lazy-route-test-mock-missing.md) | 1 |
| 前端 Vitest 从仓库根目录运行 | [错误详情](./frontend/vitest-working-directory.md) | 1 |
| 系统 Python 或 pytest 命令不可用 | [错误详情](./environment/python-test-command.md) | 1 |
| 将本地自动化等同于外部集成验收 | [错误详情](./integration/external-verification.md) | 1 |
| 使用前端 Mock 代替授权验证 | [错误详情](./frontend/mock-not-authorization.md) | 1 |
