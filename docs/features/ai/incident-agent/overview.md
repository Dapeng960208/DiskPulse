# 事件 AI 处置 Agent

## 目标与边界

事件 AI 处置 Agent 是事件中心的受限异步研判能力。它针对已派生的 Incident 生成独立 AI 紧急度、分类、依据、排查步骤、解决建议和有限状态建议，帮助解释性能异常是否只是正常短时波动。它不读取原始厂商日志、路径、凭据或跨项目数据，不调用设备、数据或调度器写接口，也不覆盖确定性 `severity` 或人工处置。

## 配置和模型

`IncidentAiSettings` 为全局单例：包含启用开关、有序候选 `model_ids`、IOPS 绝对下限和 IOPS 基线比例。默认门槛为 `max(10 IOPS, 基线 × 5%)`。仅超级管理员能读取或修改设置；启用时至少要有一个全局已启用模型。候选顺序是失败回退顺序，当前绑定的模型不能删除。

设置与模型关系、每次运行均落 PostgreSQL。运行只保存触发类型、候选尝试的安全结果、模型快照、受限输入快照、结构化评估、状态与脱敏错误码；不会保存原始 prompt、密钥、完整厂商日志或人工评论。

## 输出与自动推进

模型必须返回精确 JSON：

- `classification`：`actionable`、`normal_fluctuation` 或 `insufficient_evidence`。
- `urgency`：`low`、`medium`、`high` 或 `critical`，它独立于确定性严重度。
- `summary`、`evidence_basis`、`investigation_steps`、`resolution_steps`、可选的 `proposed_next_status` 和 `transition_reason`。

`normal_fluctuation` 必须有明确的低负载、短时波动或证据不足依据；`actionable` 必须同时提供排查和解决建议。服务端拒绝未知字段、跳级状态和无效结构。状态建议只能保持当前状态或推进一个相邻步骤，写入前再次验证事件状态和最后证据时间；每次运行最多推进一步。成功运行追加 `ai_analysis` 评论，发生推进时追加 `ai_status_changed`，两者固定显示操作人为“AI 处置 Agent”。

## 生命周期

事件新建、系统重开或新增关联证据后，只有 `critical` 且最近 60 分钟仍有证据的事件才会即时触发研判；`warning` 事件进入定时候选池。未解决事件每 30 分钟复评，单轮只选择最近 60 分钟内最多 5 条事件，依次优先确定性严重度、尚未审查或已有新证据、最近证据时间。Redis 锁和事件快照/时间桶幂等键防止并发与重复运行。模型失败、输出无效、配置关闭或证据快照已变化时，任务不写 AI 评论、不改事件状态；候选移除或关闭设置后不会发起新的运行。

IOPS 降噪属于确定性检测，始终生效而不依赖 Agent；其详细算法和事件中心行为见[事件中心专题](../../storage/incident-center/overview.md)。
