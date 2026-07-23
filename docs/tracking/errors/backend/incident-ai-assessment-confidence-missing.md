# 历史事件 AI 研判缺少置信度导致响应序列化失败

## 错误内容

`GET /storage-pulse/api/v1/incidents` 读取在 `confidence` 字段上线前写入的 `ai_assessment` JSON 时，`IncidentOut` 嵌套校验报出 `ai_assessment.confidence Field required`，使列表接口返回 HTTP 500。

## 解决方案

在 `IncidentOut` 的响应 schema 边界为缺少 `confidence` 的历史 JSON 补充保守值 `low`。新 Agent 输出仍必须提供该字段；兼容逻辑不回写历史数据，也不将历史记录标记为已发生紧急度降级。

## 备注

- 首次出现：2026-07-23，`2026-07-23-incident-ai-confidence` 会话。
- 最近出现：2026-07-23，`2026-07-23-incident-ai-confidence` 会话。
- 出现次数：1。
