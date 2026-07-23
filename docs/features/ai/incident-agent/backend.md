# 事件 AI 处置 Agent：后端事实

## 接口和授权

- `GET /storage-pulse/api/v1/admin/incident-ai-settings`
- `PATCH /storage-pulse/api/v1/admin/incident-ai-settings`

两条接口均要求 `super_admin`。PATCH 接收完整设置：`enabled`、有序且不重复的 `model_ids`、`iops_absolute_floor` 和 `iops_baseline_ratio`。候选只能引用全局启用模型，且启用 Agent 时候选不能为空。

`IncidentOut` 和 `IncidentDetailOut` 额外返回 `ai_urgency`、`ai_urgency_reason`、`ai_analyzed_at`、`ai_assessment`、`ai_review`；后者返回最近一次审查的触发类型、状态、开始/完成时间和安全错误码。`ai_review` 只反映已由 worker 开始持久化的运行，`running` 表示模型审查仍在进行。`ai_assessment` 额外包含必填 `confidence`、模型原始紧急度 `model_urgency` 与 `urgency_downgraded`；低置信度时 `ai_urgency` 是降一级后的保守结果，确定性 `severity` 不变。历史记录若尚未保存 `confidence`，响应层补为保守的 `low`，不回写历史 JSON，也不将其标记为已发生紧急度降级。

## 持久化和任务

迁移 `000000000021_incident_ai_agent.py` 为 `incidents` 添加 AI 结果列，并创建：

- `incident_ai_settings`：设置单例；
- `incident_ai_model_bindings`：候选模型和稳定优先级；
- `incident_ai_runs`：幂等运行和脱敏审计记录。

`celery_tasks.tasks.incident_ai_agent.review_incident_ai_task` 使用事件锁和生命周期快照键；`review_due_incidents_ai_task` 按 30 分钟时间桶复评，并在最近 60 分钟的有效事件中最多选择 5 条。候选排序为 `critical`、未审查或证据更新、最近证据时间；只有最近 60 分钟的 `critical` 生命周期事件会在事务提交后立即投递，其他事件等待定时批次。任务只调用 `services.ai_client.chat_completion(..., tools=[])`，未注册设备或数据写工具。

任务日志使用 `incident`、`trigger`、`task_id`（投递时）、`run_id`、最终 `status`、`model_id` 和安全 `error_code` 标识一次审查的投递、开始、跳过和结束；异常日志保留调用栈，不记录 prompt、凭据或原始厂商日志。

## 降噪

`_performance_findings` 保留原有三连续 5 分钟桶和鲁棒 Z 分数规则。对 IOPS 且最近三点 MAD 均为零的序列，只有三点都不超过动态门槛才抑制；资源至少需要 12 个近 28 天样本，否则回退同集群至少 12 个样本的中位数，仍不足时只用绝对下限。抑制发生在 `AnomalyObservation` 写入之前，所以不会产生关联 Incident 或通知。
