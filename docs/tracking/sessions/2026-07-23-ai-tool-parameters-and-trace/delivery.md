# AI 工具参数与执行轨迹交付记录

## 范围

- 修复动态 AI 工具遗漏 `Depends` 依赖 Query 参数的问题。
- 为存储集群健康分析的缺省时间范围提供最近 24 小时默认值。
- 将聊天中的工具展示改为可审计执行轨迹，并仅展示安全、可读的失败原因。
- 要求 AI 在目标不明确时先澄清，再调用工具执行明确目标。

## 当前状态

已完成：动态工具依赖参数、健康分析默认时间范围、脱敏执行轨迹、失败原因展示和先澄清后执行策略均已实现。

## 验证

- RED：`cd backend; ..\.venv\Scripts\python.exe -m pytest test\test_ai_platform.py::test_cluster_analysis_tools_are_super_admin_only_at_registration_and_execution test\test_storage_health_analytics.py::test_storage_health_endpoint_defaults_to_the_previous_24_hours test\test_ai_services.py::test_tool_trace_keeps_only_safe_failure_reasons_visible -q`，3 项按预期失败。
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test\test_ai_platform.py test\test_ai_services.py -q`，56 passed。
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test\test_storage_health_analytics.py -q`，98 passed。
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test\test_questdb_time_contract_guard.py test\test_datetime_utils.py -q`，15 passed。
- `cd frontend; pnpm exec vitest run test/unit/ai-pages.test.js --coverage.enabled=false`，26 passed。
- `cd frontend; pnpm exec eslint src/pages/ai/AiChatPage.vue test/unit/ai-pages.test.js`，通过。
- `git diff --check`，通过。

## 风险与未验证范围

- 原始 Provider 思维链仍不保存、不展示；页面只展示脱敏执行轨迹和助手的可读澄清/执行说明。
- 真实 Provider、Redis 和浏览器端 SSE 体验需在部署环境用超级管理员账户验收。
