# 代码审查问题修复记录 - 2026-07-18

## 主题

针对本次 RBAC、统一审计、遥测可观测性等大规模变更的代码审查，核实并修复了若干安全与正确性缺陷。本记录按严重程度记录已确认的问题、修复方式，以及经复核后排除的误报。

## 已修复问题

### 1. 告警投递并发竞态（高危）

**文件**：`backend/celery_tasks/tasks/storage_alerts.py`

**问题**：`_prepare_delivery_attempt` 写入了 `next_attempt_at` 租约字段，但自身从不校验租约。`deliver_storage_alert_task` 既由周期调度触发，也由 `quotaService` 直接 `.delay()` 触发。若同一告警事件在租约窗口内被二次派发，会重复自增 `delivery_attempts` 并重复调用飞书发送；随后先完成的 `_record_delivery_result` 因 `delivery_attempts != attempt` 而静默跳过结果记录，事件可能永久停留在 `retrying` 状态。

**修复**：在 `_prepare_delivery_attempt` 领取投递任务前增加租约校验——当 `next_attempt_at > now` 时直接返回，拒绝在退避/租约窗口内重复投递。此行为与生产环境调度器（`storage_alerts_schedule_task` 以 `next_attempt_at <= now` 过滤后再派发）保持一致。

**测试**：更新 `test_delivery_marks_failed_after_initial_attempt_and_three_retries`，在每次重试前模拟调度器行为（将 `next_attempt_at` 重置为过去时间），以匹配真实的退避重试流程。

### 2. 项目存在性枚举（中危）

**文件**：`backend/services/project_access_service.py`、`backend/routers/projects.py`

**问题**：`require_project_permission` 先做 `db.get(Project)` 存在性判断返回 404，再判成员权限返回 403。任一已认证用户据此可枚举系统中哪些 `project_id` 真实存在（不存在→404，存在但无权→403），构成信息泄露。此外，部分只读路由在调用授权前自行做了前置 404 检查，绕过了服务层防护。

**修复**：
- 服务层 `require_project_permission` 调整判断顺序：超管先确认授权再校验存在性（仍返回准确 404）；非超管对"不存在或无权"一律返回 403。
- `projects.py` 中面向普通用户的只读端点（`read_project_by_id`、`read_project_storage_usage_by_id`）将授权前移到存在性检查之前，使所有项目作用域端点行为统一。
- 受超管保护的写端点（如 `update_project_by_id`）保持 404 行为不变。

**测试**：更新 `test_router_error_paths.py`，新增 `assert_forbidden` 辅助函数，将 reader 用户访问项目作用域端点的断言从 404 改为统一的 403。

### 3. Correlation 中间件双响应尝试（低危）

**文件**：`backend/middleware/correlation.py`

**问题**：异常处理中先发送 `PlainTextResponse(500)` 再 `raise`，重新抛出后外层异常处理器可能尝试再次发送响应。

**修复**：发送兜底 500 响应后直接 `return`，仅在响应已开始时才重新抛出（以便服务器记录错误）。

### 4. `_as_project_id` 类型处理说明（低危 / 代码质量）

**文件**：`backend/services/ai_chat_service.py`

**问题**：`0` 与 `false` 的处理路径不同但最终结果一致，属防御性设计，实际影响很小。

**修复**：补充 docstring 说明布尔值优先拒绝、零与负数视为无效项目 ID 的设计意图，无行为变更。

## 经复核排除的误报

初评的部分结论经核实为误报，未做改动：

- **quotaService 超管返回 `None`**：两处调用方（`group.py`、`storage_usage.py`）均未使用返回值，无崩溃风险。
- **operation_audit "commit 不生效"**：`SessionLocal()` 的 `commit()` 正常持久化，无需显式事务块。
- **storagePulseMonitor "孤儿成员记录"**：成员授权与外层同一 session 同一事务，一起提交/回滚。
- **quota "device 前提交 attempt"**：代码注释明确刻意保留 pre-device 记录，且各 except 分支均写入 result 事件。
- **AI 历史可见性排除当前轮次**：`turn_visibility` 在轮次结束时通过实时 `tool_trace` 与当前轮次可见性合并（`_combine_visibility`），逻辑正确。
- **audit Windows 路径启发式红action边界**：属有意的启发式行为。

## 验证

- 完整后端测试套件通过：`526 passed`。
- 相关专项套件全部通过：告警投递、RBAC 授权、correlation、AI 历史安全、统一审计、路由错误路径。
