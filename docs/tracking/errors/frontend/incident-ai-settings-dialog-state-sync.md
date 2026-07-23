# 事件 AI 设置对话框变更未回写页面状态

## 错误内容

`IncidentAiSettingsDialog` 会发出 `update:settings`，但事件中心未监听该事件。用户关闭“启用 AI 代理”后，父页面的 `aiSettings.enabled` 仍为 `true`，保存请求无法关闭 Agent。

## 解决方案

事件中心必须监听 `update:settings`，并将对话框提供的设置合并回响应式 `aiSettings` 草稿。回归测试模拟关闭开关并断言保存请求携带 `enabled: false`。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次与最近出现：2026-07-23 事件 AI 设置开关会话
- 出现记录：`sessions/2026-07-23-incident-ai-settings-toggle/errors.md`
