# 预测、RCA 与事件中心

## 目标与边界

本专题实现 `Forecast → Anomaly → Evidence → Incident → Diagnosis` 的派生分析闭环。QuestDB 容量/性能样本、`StorageAlerts` 和厂商系统事件仍是原始事实源；PostgreSQL 新表只保存分析版本、事件状态、时间线和不可变事实引用。

既有“告警”页继续只展示 `StorageAlerts.source="diskpulse"`；NetApp/PowerScale 厂商事件继续留在存储集群健康分析的“系统事件”页签。Incident 不删除、混排、替代或复制这些原始记录。

本专题不训练基础模型、不建设 RAG/向量库或通用 CMDB、不调用存储设备写 API，也不控制 Slurm、LSF 或 EDA 调度器。

## 数据与算法

- `telemetry_quality_snapshots` 从 `telemetry_collection_runs` 和 QuestDB 覆盖率派生，不会写回或替代账本中的最后成功时间。
- `capacity_forecasts` 保存存储集群、项目、卷、Qtree、项目组和用户目录的后台预测结果；面向用户的四维预测范围与基线算法以[四维容量耗尽风险](../../ai/capacity-prediction/overview.md)为准。卷和 Qtree 预测继续只作为内部分析事实，不增加详情风险入口。
- `anomaly_observations` 对 QuestDB 性能样本按 5 分钟桶计算 P95 延迟、IOPS、吞吐量；以过去 28 天同星期/小时中位数与 MAD 建模，绝对鲁棒 Z 分数至少 3.5 且连续三个相邻 5 分钟点才写入。零 MAD 只在数值不同于基线时使用有界高分，孤立尖峰或存在采样空档的三点均不写入。IOPS 的零 MAD 三桶还要经过独立降噪：连续三个 P95 均不超过 `max(绝对下限, 28 天 IOPS 基线 × 比例)` 时不写入异常观察；默认下限为 `10 IOPS`、比例为 `5%`。基线优先使用资源至少 12 个近 28 天样本的中位数，资源样本不足时使用所属集群至少 12 个样本的中位数，否则仅使用绝对下限。IOPS 与吞吐量偏离始终只作为异常观察和 AI 上下文，不单独建立 `performance_contention`。延迟也只有连续三点均为正向退化、每点鲁棒 Z 不低于 `3.5`、每点至少有 12 个季节性样本，且每点增加至少 `max(5 ms, 基线 × 50%)` 时才具备建单资格。该确定性规则不依赖 AI 是否启用。
- `incident_evidence` 的唯一键是 `(source, source_ref)`，只保存引用、类型、时间、缺口和哈希。回放或重算不覆盖原始事实；同算法版本的分析结果以各自唯一键幂等。
- 事件至少已归属存储集群、但节点/卷/Qtree/项目的稳定映射链路不完整时，使用当前可确认的 `AssetRef` 并记录 `asset_mapping_missing`。该代码的用户语义是“资产映射不完整”；厂商事件已有稳定节点身份时节点级归属已经完成，不记录该缺口。它不表示事件代码或厂商日志缺失，也不影响查看规范化日志和发生时间。

## 事件与诊断

`incident_correlation_states` 以 `storage_cluster + AssetRef + category` 保存部署后新证据的权威滚动关联游标；`incidents.correlation_bucket_at` 继续保留作历史兼容字段，但不再决定归并。新证据距该游标最近证据不超过 `incident_analytics.correlation_window_hours`（默认 `4`）小时则关联同一 Incident，跨越旧 30 分钟桶也不拆分；超过窗口才新建。已解决 Incident 仅在这个窗口内收到同类证据时由系统重开，不合并、删除、回算或自动关闭历史 Incident。游标行在事务内锁定并按关联键唯一，重复或并发投递在来源引用唯一键与游标锁的共同约束下保持幂等。人工状态只允许 `open → acknowledged → investigating → mitigated → resolved` 的相邻迁移。Incident 是紧急处置队列，而不是原始告警镜像：DiskPulse 容量告警仅在 `critical` 时准入；性能异常仅在满足上述延迟建单资格时准入；P90 容量耗尽日期仅在未来 7 天内准入；监控质量快照和采集失败不创建 Incident。

厂商事件还需同时考虑事件实例严重级别和目录语义：已启用且已审核的 `fault_log` 只在实例为 `critical` 时准入内部 `device_fault`；已启用且已审核的 `system_activity`、`performance_anomaly`、`capacity_threshold` 或 `telemetry_degradation` 不得因严重级别或指纹重复进入 `device_fault`。目录缺失、待审核或停用时，`critical` 原始事件可保守进入该内部类别，但用户可见名称统一为“设备健康风险”，关联类型仍是 `unknown`，不得表述为已确认故障。被拦截的记录仍完整保留在告警、系统事件、健康分析、预测和采集账本中。历史版本曾把非 `critical` 厂商系统运行事件或性能提示派生为 `device_fault`；兼容修复会幂等关闭这些旧 Incident，但保留原始事件、证据和诊断用于审计。

事件列表按最近证据发现时间倒序分页；同一发现时间再按事件创建时间和 ID 稳定排序，人工编辑不会改变处置队列的事件先后。事件详情将关联证据按处置语义展示：先汇总同类依据，再逐项给出异常结论、影响范围和发现时间；证据与时间线也均按发生时间由近到远展示。性能异常证据通过 `anomaly:<id>` 回查 `anomaly_observations`，明确返回指标名称与单位、连续异常时间窗、窗口末点 P95、季节基线、正常参考范围和鲁棒 Z 分数；正常参考范围使用告警阈值 `3.5 × MAD / 0.67448975` 围绕基线计算，下界不低于零，MAD 为零时范围等于基线。厂商证据通过[厂商事件关联目录](../event-association/overview.md)补充事件代码、关联类型、中文含义和实例严重级别；只有启用且已审核定义提供正式语义，目录缺失、停用或待审核时均明确显示“未分类厂商事件”。`source_ref` 和故障指纹都是内部追溯标识，仅保留在可展开的“技术关联信息”中，不作为用户可见结论；该区域只说明证据标识、标识作用和回查方式，不重复上方的关联对象、范围或类型。监控质量引用 `quality:<cluster>:<stream>:<timestamp>:<reason>` 在服务端转为中文采集链路及“覆盖不足”或“采集过期”等结论，前端不解析内部格式。时间线返回可读的动作、说明和操作人；新写入的“关联新证据”会记录对应的简短说明，历史记录无法重建细节时使用中性说明。

维护窗口和事件静默只抑制派生 Incident 的创建/重开或通知：采集、原始事实和分析快照仍保留。维护窗口按项目、可选集群/资产和 UTC 起止时间匹配；`silenced_until` 到达后自动不再抑制通知。

确定性 RCA 至多给出 `capacity_pressure`、`device_fault`、`performance_contention`、`telemetry_blindspot` 三项候选；其中内部 `device_fault` 的用户可见名称是“设备健康风险”。各候选使用固定权重、同类最高证据、冲突扣 0.20、独立类型数/最新时间/固定优先级排序。仅当部署配置 `incident_analytics.replay_gate_verified=true` 且候选分数至少 0.8、含至少两类独立证据时才标记“高”置信度；当前该开关默认关闭。

Incident 可选附加 AI 处置研判，但不会覆盖确定性 `severity`、原始事实或人工操作。AI 仅生成受 schema 约束的分类、独立紧急度、研判依据、排查建议、解决建议与至多一个相邻状态建议；`normal_fluctuation` 必须明确低绝对负载、短时波动或证据不足的依据，`actionable` 必须包含排查与解决建议。成功研判以 `ai_analysis` 时间线评论保存，自动状态变化以 `ai_status_changed` 保存，固定显示操作人为“AI 处置 Agent”。模型只能建议保持当前状态或推进一个相邻状态；服务端在写入前重新比较状态与最后证据快照，因此过期快照、无效输出、模型失败或关闭配置均不会写评论或改状态。正常波动也只能在后续 30 分钟复评中逐步自动推进至已解决。完整约束见[事件 AI 处置 Agent](../../ai/incident-agent/overview.md)。

## API、权限与审计

接口使用完整路径：

- `GET /storage-pulse/api/v1/forecasts`、`GET /storage-pulse/api/v1/anomalies`、`GET /storage-pulse/api/v1/incidents`
- `GET /storage-pulse/api/v1/incidents/{id}`、`PATCH /storage-pulse/api/v1/incidents/{id}`、`GET /storage-pulse/api/v1/incidents/{id}/diagnosis`
- `POST /storage-pulse/api/v1/incidents/{id}/comments`、`POST /storage-pulse/api/v1/maintenance-windows`
- `GET /storage-pulse/api/v1/admin/incident-ai-settings`、`PATCH /storage-pulse/api/v1/admin/incident-ai-settings`

列表先进行项目作用域过滤再数据库分页，`size <= 100`。`reader` 只读本项目事件、诊断和证据摘要；`editor` 可认领、相邻迁移、静默和评论；`project_admin` 可创建本项目维护窗口；无作用域事件只允许 `super_admin` 读取或操作。所有写操作均从 Incident 或维护窗口反查项目并写入统一 `AuditEvent`。

AI 处置设置和候选模型绑定仅 `super_admin` 可读写。启用时至少选择一个全局已启用模型；候选顺序是回退顺序，已被当前设置引用的模型不能删除。设置关闭或候选移除后不再发起新的运行。API 输出中的 `ai_assessment` 只包含模型名称、生成时间和受限建议；不返回原始 prompt、凭据、完整厂商日志、路径或人工评论。

诊断工具只暴露安全摘要：候选、固定分数/置信度、证据 ID、中文数据缺口详情，以及厂商事件的事件代码、实例严重级别和安全关联语义。关联语义只来自启用且已审核目录；其他情况只返回 `unknown` 和“未分类厂商事件”。聊天服务把模型输出限制为这些确定性字段的精确 JSON 回显，并始终由服务端重新渲染；未知证据、候选、分数、置信度或数据缺口会回退到确定性模板。原始路径、作业环境、完整日志、设备凭据、故障指纹和厂商载荷不会进入该工具。

## 任务、通知与作业关联

- 容量预测每日运行；质量快照在容量、厂商事件和性能原始写入成功后异步排队；性能异常在性能采集成功后异步排队。三者都使用 Redis 单例锁，异常不会回滚原始采集。QuestDB 查询的时间窗口下限统一绑定为 UTC RFC 3339 `Z` 字符串，避免 PGWire 将带时区时间适配为不兼容的 `timestamptz`。
- 新建、系统重开或新增关联证据的 Incident 在事务提交后异步排入 AI 研判；未解决 Incident 还会按 30 分钟周期复评。任务和运行记录分别以 Redis 锁、事件快照/时间桶幂等键防止并发和重复调用。运行记录只保存触发来源、尝试顺序、脱敏输入快照、实际模型快照、受限结构化结果、状态和脱敏错误码。
- `incident_notifications.enabled` 是 Incident 通知总开关；启用时默认受众是 `super_admin_usernames`。项目负责人、项目成员、额外用户名、邮件和飞书均需分别显式开启，邮件和飞书可独立投递。仅新建、系统重开和严重度升级尝试发送；维护窗口与静默不影响原始告警或厂商事件通知。
- `WorkloadStorageAdapter` 是默认不连接客户系统的只读契约。Slurm/LSF/EDA 夹具只输出按实际执行窗口、项目、主机、已解析 `AssetRef` 与 5 分钟窗汇总的 `active_job_count`。作业 ID、原始路径、环境和日志仅可在内存映射中使用，绝不持久化或发送给模型。

## 前端入口与验证范围

“事件中心”位于“系统管理”的“事件与审计”分区，路径为 `/admin/incidents`，仅超级管理员可见，支持服务端分页和详情中的认领、状态推进、静默、评论与维护窗口。存储集群详情的“关联事件”页签懒加载，显示该集群关联事件、预测数和异常数；它不改变既有告警或系统事件页签。

容量预测不作为事件中心或一级导航栏目展示。四个维度均在对应资源详情的“耗尽风险”页签发布轻量结论；入口、展示和兼容重定向见[容量耗尽风险前端说明](../../ai/capacity-prediction/frontend.md)。资源详情的关联事件仍只校验当前资源的项目 `reader` 权限，不受预测发布开关影响；关闭风险展示不会隐藏用户原本有权读取的事件。

## 容量风险与 AI 治理关系

容量预测的四维范围、基线算法、风险阈值、AI 输出校验、候选启用门槛和发布开关统一由[四维容量耗尽风险](../../ai/capacity-prediction/overview.md)定义。事件中心只消费预测事实：P90 在未来 7 日内耗尽时可形成容量压力证据；它不负责向用户展示模型治理、完整曲线或容量计划。

固定线性增长历史夹具已验证 30 天预测 MAPE 不高于 15%，固定 RCA 夹具已验证 Top-3 命中率不低于 80%；它们只证明算法回归。真实 NetApp/PowerScale 只读回放、真实 QuestDB/Redis/Celery 任务和生产通知通道仍待隔离环境验收；在此之前界面不会通过默认配置显示高置信度。
