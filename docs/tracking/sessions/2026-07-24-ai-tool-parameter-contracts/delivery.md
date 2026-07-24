# AI 工具参数契约与失败重试交付

## 范围

- 审计全部 `ai_exposed` 路由的顶层参数类型、可空默认值与 JSON Schema。
- 修复用户目录查询中用户名和数字 `user_id` 混用导致的 HTTP 500。
- 修正服务端 5xx 的 AI 工具错误语义，并阻止当前回合继续猜参重试。

## 已完成

- 扫描 55 个 AI 工具、211 个顶层参数；全部字段均有 JSON Schema 类型信号，定位并修复 2 个工具中的 3 个歧义字段：`list_storage_usages.user_id`、`list_projects.prop`、`list_projects.order`。
- `list_storage_usages.user_id` 现为数字 ID 或 `null`；新增 `rd_username` 精确筛选，且与 `user_id` 互斥。历史空字符串仍转换为 `null`，非数字字符串返回 `422`。
- 5xx 不再声称“参数已通过校验”，而是返回 `error_type=server_error`、`retryable=false`；同一批重复调用只执行一次，下一次 Provider 调用不再提供工具。
- 新增全量 AI 工具 Schema 契约测试，持续拒绝无类型、互不兼容的标量联合和默认 `null` 但 Schema 不可空的字段。
- 同步 AI 对话事实文档与可复现错误台账。

## 验证

- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_ai_platform.py::test_all_ai_exposed_route_parameter_schemas_are_unambiguous test/test_ai_services.py::test_tool_registry_provider_shapes_and_failure_responses test/test_ai_services.py::test_stream_disables_tools_after_non_retryable_server_error test/test_ai_services.py::test_stream_reuses_successful_tool_results_and_repairs_failed_calls test/test_core_api.py::TestCoreApi::test_storage_usage_create_list_update_backup_and_export_contracts -q`
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_ai_services.py test/test_ai_platform.py test/test_core_api.py::TestCoreApi::test_storage_usage_create_list_update_backup_and_export_contracts test/test_coverage_gaps.py::test_project_and_storage_usage_crud_gaps -q`（75 passed）

## 未验证范围与风险

- 尚未使用真实外部 Provider 验证 5xx 后的最终自然语言回答；服务端已经通过回归测试强制清空下一轮工具列表。
- 未运行全量后端测试；按小范围修复策略仅运行 AI 工具、对话编排和用户目录接口的聚焦回归。
- 查询新增的 `rd_username` 使用现有用户关系条件；未新增索引或迁移，性能依赖现有 `users.rd_username` 与外键查询计划。
