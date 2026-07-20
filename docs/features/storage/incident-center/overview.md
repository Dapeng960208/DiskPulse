# 预测、RCA 与事件中心

## 目标与边界

本专题实现 `Forecast → Anomaly → Evidence → Incident → Diagnosis` 的派生分析闭环。QuestDB 容量/性能样本、`StorageAlerts` 和厂商系统事件仍是原始事实源；PostgreSQL 新表只保存分析版本、事件状态、时间线和不可变事实引用。

既有“告警”页继续只展示 `StorageAlerts.source="diskpulse"`；NetApp/PowerScale 厂商事件继续留在存储集群健康分析的“系统事件”页签。Incident 不删除、混排、替代或复制这些原始记录。

本专题不训练基础模型、不建设 RAG/向量库或通用 CMDB、不调用存储设备写 API，也不控制 Slurm、LSF 或 EDA 调度器。

## 数据与算法

- `telemetry_quality_snapshots` 从 `telemetry_collection_runs` 和 QuestDB 覆盖率派生，不会写回或替代账本中的最后成功时间。
- `capacity_forecasts` 使用有硬限额的存储集群、卷、Qtree、项目组和用户目录的 45 个 UTC 日窗口。每天保留最大已用值；有效日少于 30 或覆盖率小于 80% 时只保存 `capacity_history_insufficient` 数据缺口。满足条件后以 Theil-Sen 中位斜率和残差 P10/P50/P90 生成未来 30 天曲线及三条耗尽日期。
- `anomaly_observations` 对 QuestDB 性能样本按 5 分钟桶计算 P95 延迟、IOPS、吞吐量；以过去 28 天同星期/小时中位数与 MAD 建模，绝对鲁棒 Z 分数至少 3.5 且连续三个相邻 5 分钟点才写入。零 MAD 只在数值不同于基线时使用有界高分，孤立尖峰或存在采样空档的三点均不写入。
- `incident_evidence` 的唯一键是 `(source, source_ref)`，只保存引用、类型、时间、缺口和哈希。回放或重算不覆盖原始事实；同算法版本的分析结果以各自唯一键幂等。
- 无法把厂商事件或性能对象映射到卷/Qtree/项目时，使用集群级 `AssetRef` 并记录 `asset_mapping_missing`。

## 事件与诊断

事件按 `storage_cluster + AssetRef + category + 30 分钟 UTC 桶` 归并；同键已解决事件在 24 小时内有新证据时由系统重开。人工状态只允许 `open → acknowledged → investigating → mitigated → resolved` 的相邻迁移。

维护窗口和事件静默只抑制派生 Incident 的创建/重开或通知：采集、原始事实和分析快照仍保留。维护窗口按项目、可选集群/资产和 UTC 起止时间匹配；`silenced_until` 到达后自动不再抑制通知。

确定性 RCA 至多给出 `capacity_pressure`、`device_fault`、`performance_contention`、`telemetry_blindspot` 三项候选。各候选使用固定权重、同类最高证据、冲突扣 0.20、独立类型数/最新时间/固定优先级排序。仅当部署配置 `incident_analytics.replay_gate_verified=true` 且候选分数至少 0.8、含至少两类独立证据时才标记“高”置信度；当前该开关默认关闭。

## API、权限与审计

接口均位于 `/storage-pulse/api/v1`：

- `GET /forecasts`、`GET /anomalies`、`GET /incidents`
- `GET/PATCH /incidents/{id}`、`GET /incidents/{id}/diagnosis`
- `POST /incidents/{id}/comments`、`POST /maintenance-windows`

列表先进行项目作用域过滤再数据库分页，`size <= 100`。`reader` 只读本项目事件、诊断和证据摘要；`editor` 可认领、相邻迁移、静默和评论；`project_admin` 可创建本项目维护窗口；无作用域事件只允许 `super_admin` 读取或操作。所有写操作均从 Incident 或维护窗口反查项目并写入统一 `AuditEvent`。

诊断工具只暴露安全摘要：候选、固定分数/置信度、证据 ID 与数据缺口。聊天服务把模型输出限制为这些字段的精确 JSON 回显，并始终由服务端重新渲染；未知证据、候选、分数、置信度或数据缺口会回退到确定性模板。原始路径、作业环境、日志、设备凭据和厂商载荷不会进入该工具。

## 任务、通知与作业关联

- 容量预测每日运行；质量快照在容量、厂商事件和性能原始写入成功后异步排队；性能异常在性能采集成功后异步排队。三者都使用 Redis 单例锁，异常不会回滚原始采集。
- `incident_notifications.enabled` 是 Incident 通知总开关；启用时默认受众是 `super_admin_usernames`。项目负责人、项目成员、额外用户名、邮件和飞书均需分别显式开启，邮件和飞书可独立投递。仅新建、系统重开和严重度升级尝试发送；维护窗口与静默不影响原始告警或厂商事件通知。
- `WorkloadStorageAdapter` 是默认不连接客户系统的只读契约。Slurm/LSF/EDA 夹具只输出按实际执行窗口、项目、主机、已解析 `AssetRef` 与 5 分钟窗汇总的 `active_job_count`。作业 ID、原始路径、环境和日志仅可在内存映射中使用，绝不持久化或发送给模型。

## 前端入口与验证范围

“事件中心”位于根路由 `/incidents`，支持服务端分页和详情中的认领、状态推进、静默、评论与维护窗口。存储集群详情的“关联事件”页签懒加载，显示该集群关联事件、预测数和异常数；它不改变既有告警或系统事件页签。

## 资源详情预测与 AI 治理

- 项目组详情 `/group/:id` 与用户目录详情 `/usage/:id` 分别提供独立的“容量预测”页签。两类资产分别取数和展示，不能将用户目录预测汇总回项目组。
- `capacity_prediction_settings.user_visible` 默认关闭。关闭时，后台基线预测、候选评估、异常、RCA 和新鲜度任务继续运行；非超级管理员无法读取资源预测接口或看到页签。超级管理员打开全局可见性后，`reader` 才能读取自己项目范围内的预测，`project_admin` 才能新增该资产的结构化容量计划；容量变化必须是有限非零值，批准说明去除首尾空白后不能为空。
- 预测页展示容量趋势、P10/P50/P90 区间、耗尽日期、回测 MAPE、日样本量、覆盖率、最新遥测、预测新鲜度、模型版本、来源、容量计划摘要及事件/RCA 边界。无有效数据、遥测过期或 AI 输出失败时必须显示数据质量/回退状态，不得把缺失数据表示为准确率。
- AI 候选仅允许已启用的私有 Ollama 模型。每次调用只发送当前资源的日级聚合容量、限额、白名单质量摘要和已批准计划，不发送路径、用户标识、密钥、端点配置或跨项目明细。P10/P50/P90 必须是连续 30 个 UTC 日、非负、有限且顺序有效；超时和其他无效输出分别记录原因并回退 Theil-Sen 基线。
- 后台对候选执行三个互不重复的滚动 30 天留出窗口，只持久化跨资源聚合后的 MAPE 与耗尽风险覆盖结果；数据库按候选和窗口强制唯一。候选平均 MAPE 较基线降低至少 10%，且耗尽风险覆盖不变差，超级管理员才可启用；启用时会再次确认关联私有模型仍处于启用状态。资源读取只使用与当前基线 `training_end` 完全一致的候选曲线，旧候选结果不会覆盖当天基线。治理页只展示模型 ID、聚合评估和 AI 回退计数，不显示资源标识或端点细节；预测生成、回退、候选启用、全局可见性和容量计划变更均写入统一操作审计，通用 HTTP 审计不再为这些写操作追加重复事件。

固定线性增长历史夹具已验证 30 天预测 MAPE 不高于 15%，固定 RCA 夹具已验证 Top-3 命中率不低于 80%；它们只证明算法回归。真实 NetApp/PowerScale 只读回放、真实 QuestDB/Redis/Celery 任务和生产通知通道仍待隔离环境验收；在此之前界面不会通过默认配置显示高置信度。
