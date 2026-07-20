# AI 流式失败日志交付记录

## 范围

- 为 AI 对话流式接口的未归类异常补充可关联的服务端异常日志。
- 保持 SSE 与审计中的用户可见错误安全，不回显内部细节。

## 完成项

- `stream_message()` 的失败边界现在记录 Trace ID、审计 ID、会话 ID、用户 ID、异常类型和完整异常栈。
- 前端收到的 `error` 事件仍为“AI 服务暂不可用”，现有失败审计仍只保存安全摘要。
- 新增回归测试，模拟工具注册异常并断言日志包含 Trace ID、异常类型和异常栈。

## 验证

- RED：新增测试在原实现下失败，原因是没有服务端日志记录。
- GREEN：`D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_platform.py -k "stream_setup_failure_logs_traceable_server_error or stream_setup_failure_still_emits_the_precreated_turn or provider_failure_persists_the_precreated_assistant_message" -q`，3 项通过。
- 回归：`D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_platform.py -q`，23 项通过；`python -m compileall -q services\\ai_chat_service.py` 通过。

## 风险与未验证范围

- 未向真实 Provider 发起新的付费请求；真实环境下一次失败可通过 SSE `accepted.trace_id` 与后端日志关联原始异常。
