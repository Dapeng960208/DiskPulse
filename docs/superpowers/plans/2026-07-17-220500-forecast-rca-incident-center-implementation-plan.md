# 容量预测、异常/RCA 与事件中心实施计划

- 依据：[实施计划索引](./2026-07-17-220000-enterprise-ai-storage-implementation-index.md)
- 状态：待实施；第一版只读，不触发设备写操作。
- 前置条件：项目级 RBAC、统一审计、模型网关/私有模型路由、遥测新鲜度已上线，且 QuestDB 具备至少 45 天合格历史数据和可重复故障标注夹具。

## 目标与边界

- 将现有容量、性能、厂商事件转为 `Forecast → Anomaly → Evidence → Incident → Diagnosis` 的可解释闭环。
- 保留 `StorageAlerts` 的现有语义：告警页只显示 DiskPulse 告警，厂商系统事件保留在存储健康；新的 `Incident` 只引用原始证据，不能替代或复制原始告警。
- LLM 只能把确定性 `Diagnosis` 转成说明，不能添加证据、制造事实或提高置信度。
- 本工作包不训练基础模型、不建设 RAG/向量库/通用 CMDB，也不执行设备写操作。

## 数据、算法与接口契约

- PostgreSQL 新增：
  - `telemetry_quality_snapshots`：资产、周期、最新点、覆盖率、缺口、质量状态；它只从第 03 工作包的 `telemetry_collection_runs` 和 QuestDB 覆盖率派生，是分析快照，不能成为第二套最后成功时间权威来源。
  - `capacity_forecasts`：资产、训练窗口、`p10/p50/p90` 30 天曲线、耗尽日期、算法版本、输入质量、回放误差。
  - `anomaly_observations`：资产、指标、观测值、季节性基线、MAD 分数、严重度、证据窗口。
  - `incidents`、`incident_evidence`、`incident_timeline`、`maintenance_windows`、`diagnoses`：分别记录事件状态、不可变证据引用、操作时间线、抑制规则和版本化 Top-N 诊断。
- 稳定对象：
  - `AssetRef = {asset_type,asset_id,storage_cluster_id,project_id?,vendor,display_name}`
  - `TelemetryEnvelope = {asset_ref,source,observed_at,collected_at,metric_or_event,value,quality,source_ref}`
  - `Diagnosis = {incident_id,algorithm_version,candidates[],confidence,evidence_ids[],data_gaps[]}`
- 证据生产与幂等：容量、性能、NetApp/PowerScale 厂商事件采集在写入各自原始存储后生成 `TelemetryEnvelope`；以 `(source,source_ref)` 作为不可变证据去重键，回放/重算只能新增带算法版本的分析结果，不能重复或覆盖原始证据。厂商事件无法映射到卷、Qtree 或项目时，退回集群级 `AssetRef` 并标注 `data_gap=asset_mapping_missing`。
- 容量预测规则：对有硬限额的集群、卷、Qtree、项目组、用户目录按每日最大已用容量训练；45 天至少 30 个有效日点且覆盖率至少 80%；用 Theil-Sen 趋势与残差分位数生成 `p10/p50/p90`；条件不足时只返回“证据不足”。
- 性能异常规则：对 P95 延迟、IOPS、吞吐量按同一小时/星期计算 28 天中位数 + MAD；鲁棒 Z 分数绝对值 `>=3.5` 且连续 3 点才形成异常。
- 事件归并：按 `storage_cluster + AssetRef + category + 30 分钟窗口` 创建或追加；已解决事件 24 小时内同键证据重开。状态固定：`open → acknowledged → investigating → mitigated → resolved`；静默和维护窗口只抑制，不删除证据。
- RCA 只输出 `capacity_pressure`、`device_fault`、`performance_contention`、`telemetry_blindspot` 四类候选，最多三项。候选评分固定为不同证据类型的权重之和、上限 `1.0`：容量压力使用耗尽预测 `0.45`、硬/软限额告警 `0.35`、高使用率 `0.20`；设备故障使用严重厂商事件 `0.50`、重复指纹 `0.25`、同时段采集错误 `0.15`；性能争用使用连续性能异常 `0.45`、同时段吞吐/IOPS 偏离 `0.30`、关联作业/邻居证据 `0.25`；遥测盲区使用新鲜度过期 `0.60`、采集失败 `0.25`、覆盖率不足 `0.15`。同类证据只取最高一条，冲突证据扣除 `0.20` 且强制标注数据缺口；并列时依次按独立证据类型数、最新证据时间、固定候选优先级排序。高置信度仍要求至少两类独立证据且评分 `>=0.8`。
- 新接口：`GET /storage-pulse/api/v1/forecasts`、`GET /storage-pulse/api/v1/anomalies`、`GET /storage-pulse/api/v1/incidents`、`GET/PATCH /storage-pulse/api/v1/incidents/{id}`、`POST /storage-pulse/api/v1/incidents/{id}/comments`、`POST /storage-pulse/api/v1/maintenance-windows`。列表统一先作用域过滤、再数据库分页，`size<=100`，新时间字段为 UTC ISO-8601。
- 事件权限固定为：`reader` 可读本项目事件和证据摘要；`editor` 可在本项目确认、认领、变更允许状态和评论；`project_admin` 额外可建立本项目维护窗口；`super_admin` 可处理无作用域/全局事件。所有写操作由服务端从 `Incident` 反查项目并写统一审计。

## 实施步骤

1. 先为质量、预测、异常、事件状态机和跨项目读取写 RED 测试，增加 Alembic、ORM、Pydantic、CRUD、授权依赖和只读 API；不创建事件。
2. 增加质量、容量预测、性能异常 Celery 任务：质量随采集完成运行，性能异常按性能周期运行，容量预测每日运行。
3. 增加证据关联、事件生命周期、确定性 RCA；只在私有模型/模型网关强制 `restricted` 路由后，将 AI 助手只读接入诊断 GET 工具。
4. 新增经客户授权的 EDA/LSF/Slurm 作业到存储路径只读关联 adapter：只保存作业系统、项目、时间窗口、主机和已解析 `AssetRef`，不将原始作业环境、路径或日志发送给模型；关联结果仅作为性能争用/影响分析证据，不控制调度器。
5. 新增“事件中心”根路由及集群详情“关联事件”页签，保留既有告警页和系统事件页语义。
6. 用历史回放达到门槛后才显示“高置信度”；未达到时只显示证据和数据缺口。同步更新 `docs/features/` 的健康分析/AI 专题、`docs/overview/latest-features.md` 与 `docs/tracking/current-release.md`。

## 验证与验收

- RED/GREEN：数据不足、遥测过期、孤立尖峰、跨项目读取、无效状态迁移、重复/重开事件均有覆盖。
- 固定历史夹具：稳定增长对象 30 天预测 MAPE `<=15%`；标注故障的 RCA Top-3 命中率 `>=80%`。
- 集成：厂商事件风暴与性能异常只生成一个关联事件；维护窗口只抑制新事件/通知；原始告警和系统事件不被删除或混排。
- E2E：不同项目用户只看本项目事件；事件认领、状态变更、评论和维护窗口均记录统一审计。
- 计划验证命令（相应测试文件完成后）：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_storage_health_analytics.py backend/test/test_forecast_incident_center.py -q`、`D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head`、`cd frontend; npm exec vitest run test/unit/IncidentCenterPage.test.js test/unit/StorageClusterDetailPage.test.js --coverage.enabled=false`，以及 NetApp/PowerScale 隔离环境的只读回放验收。
