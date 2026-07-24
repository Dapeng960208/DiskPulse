# 标题

AI 对话工具轮次配置键不匹配

## 错误内容

AI 对话循环读取 `ai.max_tool_iterations`，而部署配置和示例配置定义的是 `ai.chat_tool_max_iterations`。因此已配置的轮次上限不生效，代码始终回退到默认值 4。

## 解决方案

工具循环统一读取 `ai.chat_tool_max_iterations`，并以回归测试验证该键可将循环限制为一轮。`request_timeout_seconds` 和 `chat_rate_limit_per_minute` 保持各自的 Provider 超时与聊天入口限流职责，不与事件审计配置混用。

## 备注

- 出现次数：1
- 2026-07-24：用户配置 `chat_tool_max_iterations: 60` 后对话仍在四轮停止；已用聚焦回归测试复现并修复。
