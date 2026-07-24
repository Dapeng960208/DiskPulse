# Incident 关联任务假定会话适配器存在 `info`

## 错误内容

`process_vendor_event_evidence` 在事务提交后直接调用 `db.info.pop("incident_ai_review_ids", set())`。轻量会话适配器或测试替身没有 SQLAlchemy `Session.info` 时，即使厂商事件关联和提交已经成功，finally 块仍抛出 `AttributeError`，使任务调用表现为失败。

## 解决方案

集中使用 `_drain_incident_ai_review_ids(db)`：只有 `info` 是字典时读取并清空排队的 AI 审查 ID，否则返回空集合。真实 SQLAlchemy 会话维持既有投递行为，非 ORM 适配器不会因提交后的可选 AI 审查队列而失败。

## 备注

- 首次出现：2026-07-24，`2026-07-24-event-audit-incident-noise` 会话。
- 最近出现：2026-07-24，`2026-07-24-event-audit-incident-noise` 会话。
- 出现次数：1。
