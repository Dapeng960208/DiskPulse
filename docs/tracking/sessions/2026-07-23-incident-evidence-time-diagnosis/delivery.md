# 事件中心最近证据时间诊断

- 会话：`2026-07-23-incident-evidence-time-diagnosis`
- 状态：诊断完成，尚未修复
- 范围：定位 `/admin/incidents` 中性能争用事件“最近证据”晚于当前时间的问题。

## 诊断结论

- 性能采集把设备时间转换为 `Asia/Shanghai` 本地墙上时间，并以无时区 `datetime` 写入 QuestDB。
- 性能异常任务读取 QuestDB 的无时区 `collected_at` 后，直接补为 UTC；事件与证据因此保存为比真实瞬时晚 8 小时的 UTC 时间。
- 前端按浏览器本地时区格式化带 UTC 偏移的 API 时间，继续显示为上海时间，所以真实的 `12:15` 最终显示为 `20:15`。
- 诊断时数据库中共有 53 条性能争用 Incident 的 `last_evidence_at` 晚于当前 UTC，说明问题不是单条前端展示异常。

## 验证

- 已在浏览器复现事件中心列表显示未来时间。
- 已只读查询 PostgreSQL 中目标 Incident、IncidentEvidence 与 AnomalyObservation 的时间值。
- 已只读查询 QuestDB 中目标对象的 `collected_at`，确认其为无时区本地墙上时间。
- 已核对性能采集、异常分析、Incident 关联与前端格式化调用链。

## 未验证范围与风险

- 本会话只诊断，未修改历史 QuestDB、AnomalyObservation、Incident 或 IncidentEvidence 数据。
- 尚未验证修复策略对容量趋势、性能图表、质量快照和历史数据回填的兼容性。
- 当前环境没有可用的 `docker` 命令，数据库检查改用仓库 Python 连接配置完成。
