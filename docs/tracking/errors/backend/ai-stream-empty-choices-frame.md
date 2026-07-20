# AI 流式空 choices 状态帧导致对话失败

## 错误内容

OpenAI 兼容 Provider 在 SSE 流中发送 `choices: []` 的状态或用量帧时，客户端直接访问 `choices[0]`，触发 `IndexError`，使本可继续的流式对话错误结束。

## 解决方案

解析 OpenAI 兼容 SSE 帧时，空 `choices` 数组视为不含文本或工具调用的状态帧并忽略；保留后续正常 `choices` 帧的文本和工具调用解析。缺失或非法结构仍按照既有 Provider 响应格式错误路径处理。

## 备注

- 分类：`backend`
- 出现次数：1
- 首次与最近出现：2026-07-20，`2026-07-20-ai-empty-choice-stream-frame` 会话。
- 运行证据：Trace ID `0527b6d7-6596-4eea-adab-fbe69892e054` 的日志显示 `_openai_stream()` 在读取空数组时抛出 `IndexError`。
