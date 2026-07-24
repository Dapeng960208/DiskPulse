# AI 工具失败诊断与配置修复交付

## 范围

- 修复 AI 对话工具轮次配置键未生效的问题。
- 将内部工具 HTTP 5xx 以经脱敏、可行动的原因展示给模型和用户；不暴露异常文本、堆栈或凭据。
- 明确 AI 对话的超时、工具轮次和限流配置不属于事件审计配置。

## 已完成

- 工具循环改为读取 `ai.chat_tool_max_iterations`。
- 500–599（502、503、504 除外）工具响应会显示参数已通过接口校验、不能通过调整参数修复的安全提示。
- 已更新 AI 对话配置与失败展示的事实文档。
- 以相同的用户目录查询参数在当前本地服务和完整内部 ASGI 工具链上验证成功；响应分别为 HTTP 200 和 `ok: true`。

## 验证

- `cd backend; ..\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_services.py::test_tool_registry_provider_shapes_and_failure_responses test\\test_ai_services.py::test_tool_iteration_limit_completes_as_degraded_and_persists_recovery_metadata -q`

## 未验证范围与风险

- 当前运行中的 Uvicorn 进程尚未重载本次源码；部署或重启后才会使用新的失败文案与配置键。
- 截图对应的历史 HTTP 500 没有保留可读取的服务端异常日志；当前以完全相同的筛选参数已成功，无法从截图反推当时的底层异常。
