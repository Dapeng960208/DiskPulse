# 事件 AI 设置调用已移除 API 方法

## 错误内容

事件中心打开 AI 处置设置时，`useIncidentAiSettings` 调用 `incidentApi.fetchIncidentAiSettings`；保存时调用 `updateIncidentAiSettings`。`IncidentApi` 的实际公开方法是 `fetchAiSettings` 和 `updateAiSettings`，导致运行时抛出 `is not a function`。

## 解决方案

调用方必须使用 `IncidentApi` 已公开的 `fetchAiSettings` 和 `updateAiSettings`。事件中心回归测试只模拟这两个真实方法名，并断言加载与保存均通过该契约调用。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次与最近出现：2026-07-23 事件 AI 设置 API 契约会话
- 出现记录：`sessions/2026-07-23-incident-ai-settings-api-contract/errors.md`
