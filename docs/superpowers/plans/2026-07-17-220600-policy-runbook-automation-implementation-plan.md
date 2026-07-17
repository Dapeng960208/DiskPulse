# 策略、Runbook、审批与受控自治实施计划

- 依据：[实施计划索引](./2026-07-17-220000-enterprise-ai-storage-implementation-index.md)
- 状态：待实施。
- 前置条件：01-05 已完成，Vault/KMS 已提供短生命周期的应用访问令牌/租约与可轮换、最小权限的设备凭据，且有 NetApp/PowerScale 隔离测试对象。

## 目标与安全边界

- 建立确定性执行控制面，将建议与执行分离：模型只生成 `ActionPlanDraft`，设备调用只由后台 Runbook 执行器进行。
- 任何改变设备状态的路由不再通过 `ai_exposed`/`ai_system_management` 被 AI 直接调用；AI 只能创建计划草案，不能调用现有配额写服务。
- R0 只读诊断和 R1 重新采集/重新计算可按策略执行；R2 仅支持配额增加并要求不同用户审批；R3 永不自动执行。
- 本工作包不做通用工作流引擎、不开放任意设备 API、不自动执行 R2/R3、也不将 AI 聊天审计当作变更审计。

## 风险分级、状态机与数据契约

- R0：查询健康、生成诊断包、查询保护/配额状态，可自动执行并审计。
- R1：重新采集指定集群、重新计算预测/诊断，可经策略预批准执行，必须幂等和验证。
- R2：仅增加用户目录或项目组配额，前提为独占目标、增量不超过当前限额 20% 且不超过 1 TiB；需不同于申请人的 `project_admin` 或 `super_admin` 审批。
- R3：删除、降低保护、权限变更、升级、跨站切换、配额缩减不进入第一版。
- 新增 PostgreSQL 表：`policy_versions`、`change_windows`、`action_plans`、`action_plan_steps`、`approval_decisions`、`runbook_executions`、`runbook_step_executions`、`automation_circuit_breakers`；复用 `audit_events`。
- 状态固定：`draft → policy_evaluated → pending_approval → approved → scheduled → running → verifying → succeeded|failed|needs_manual_intervention`；`pending_approval → rejected|expired|cancelled`，且尚未运行的 `draft`、`policy_evaluated`、`approved`、`scheduled` 可转 `cancelled`。`rejected`、`expired`、`cancelled` 为不可执行终态。原计划仅在关联且重新审批的补偿计划 `succeeded` 后才可标记 `rolled_back`；补偿失败保留原计划的 `failed` 或 `needs_manual_intervention`，不得伪报回滚成功。
- 核心对象：
  - `ActionPlan = {id,incident_id?,action_type,target:AssetRef,parameters,expected_before,risk,policy_version,idempotency_key,request_hash}`
  - `PolicyDecision = {allow,reason_codes,approval_count,window_id?,limits,policy_version}`
  - `RunbookExecution = {plan_id,state,worker_lease,provider_operation_ref?,precheck,verification,rollback_plan_id?,trace_id}`
- 客户端必须提交 `Idempotency-Key`；同一动作、目标、键和请求哈希返回原计划，不同请求体返回 `409`。执行器按目标持有数据库租约。

## 执行规则与 API

- 创建计划后服务端重新读取作用域、当前限额、设备能力、遥测新鲜度和变更窗口，冻结 `PolicyDecision`。
- R2 审批 30 分钟失效，申请人不能审批自己；第 06 工作包新增 `approve_r2` 权限：`project_admin` 只可审批本项目、`super_admin` 可审批全局，但两者都必须不同于申请人且不获得设备执行权限。服务端从目标反查项目并在写入审批前再次校验；执行始终由受控 Runbook Worker 完成。执行前再次检查 `expected_before`，不匹配即 `needs_manual_intervention`。
- 设备写入后必须读回验证。网络超时后禁止盲重试写请求，转入 `verifying` 读取真实设备状态。
- 每个 `vendor + cluster + action_type` 在 10 分钟内连续 3 次失败后熔断 30 分钟；只有超级管理员可在审计下解除。
- 配额回滚是单独的 R2 补偿计划，只有实际用量低于原限额、预检通过且重新审批后才可执行；不自动缩减配额。
- NetApp 与 PowerScale 写操作必须封装在 `RunbookActionAdapter`，调用方只传领域动作而不能传 URL、HTTP method、设备命令或凭据。
- 新接口：
  - `POST/GET /storage-pulse/api/v1/automations/action-plans`
  - `GET /storage-pulse/api/v1/automations/action-plans/{id}`
  - `POST /storage-pulse/api/v1/automations/action-plans/{id}/approval-decisions`
  - `POST /storage-pulse/api/v1/automations/action-plans/{id}/execution-requests`
  - `GET /storage-pulse/api/v1/automations/runbook-executions`
  - `GET/POST/PATCH /storage-pulse/api/v1/policies`
  - `GET/POST/PATCH /storage-pulse/api/v1/change-windows`
- 新增“自动化中心”：操作计划、待审批、执行记录、策略/变更窗口四个页签。事件详情只可创建计划或查看执行，不提供绕过审批的执行按钮。

## 实施步骤

1. 先写策略、审批、幂等、状态机和 dry-run RED 测试，移除 AI 对设备写路由的暴露。
2. 实现 `ActionPlan`、策略决策、审计、权限、数据库租约与只读 dry-run；新增自动化中心。
3. 实现 R0/R1 Runbook、执行状态机、熔断、验证记录和任务租约。
4. 将“配额增加”适配为 R2 审批流，接入 NetApp 与 PowerScale；按顺序移除 AI 暴露、将前端迁移到 `ActionPlan`、以 feature flag 禁止遗留同步直写、对遗留接口返回弃用响应/公告，最终删除该直写路径或改造成“创建计划并返回 `202`”。在退出条件满足前，不得声明审批链不可绕过。
5. 在隔离设备完成故障注入、回读验证和补偿演练后才启用 R1 策略自治；R2 始终人工审批。同步更新 `docs/features/` 的 AI、配额和健康分析专题、`docs/overview/latest-features.md`、部署/变更 Runbook 与 `docs/tracking/current-release.md`。

## 验证与验收

- RED/GREEN：重复幂等键、请求冲突、自我审批、审批过期、越权、窗口外执行、陈旧遥测、前值变化、熔断、未知写结果。
- 同键重放不重复写设备；不同键并发只有一个执行器获得租约；超时写调用只读回验证，读回一致才成功。
- AI 无法提交任意设备 URL/命令；凭据、Token、敏感路径不进入审计、异常或模型上下文；R2 无审批一律不执行。
- 在 NetApp 和 PowerScale 测试对象分别完成配额增加、读回校验、失败熔断和人工补偿计划；不得用生产设备作为首轮测试环境。
- 验收：低风险动作成功率目标 `>=99%`，越权执行和敏感数据违规出网均为零。
- 计划验证命令（相应测试文件完成后）：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_quota_adjustment.py backend/test/test_ai_platform.py backend/test/test_runbook_automation.py -q`、`D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head`、`cd frontend; npm exec vitest run test/unit/AutomationCenterPage.test.js test/unit/IncidentDetailPage.test.js --coverage.enabled=false`，再在 NetApp/PowerScale 隔离对象完成写入、回读、熔断和补偿演练。
