# 项目级 RBAC 与统一审计后端

## 当前已实现

- `project_memberships` 保存项目成员及 `reader`、`editor`、`project_admin` 角色；`Project.in_charge_user_id` 会补齐为 `project_admin`，已移除 `pt_user`。
- `AIConversation.project_id` 为可选字段。创建会话时可携带项目 ID，已提供项目 ID 时按项目权限校验；未绑定项目的历史会话仍可保留。
- `audit_events` 追加式模型、查询 CRUD、`GET /storage-pulse/api/v1/audit-events`、`X-Request-ID`/`X-Trace-ID` 关联中间件和 `000000000009_unified_audit.py` 已存在。
- 审计写入通过 `append_audit_event()` 只执行 `add`/`flush`，不替业务事务提交；摘要会递归移除凭据、Token、原始 prompt/response 内容及完整路径。迁移为 SQLite、PostgreSQL、MySQL 生成拒绝 `UPDATE`/`DELETE` 的触发器。

## 当前接口与权限

- 统一审计查询支持项目、主体、动作、结果、时间和分页过滤。超级管理员可查询全局；非超级管理员必须指定项目并通过该项目 `project_admin` 校验。
- 项目成员 Router 已注册为 `/storage-pulse/api/projects/{project_id}/members` 的 CRUD 端点，且限制项目管理员只管理 `reader`/`editor`。路由合同已验证 `GET/POST` 成员集合与 `PATCH/DELETE` 单个成员端点由主应用公开。

## 未完成边界

- 登录/登出、项目/用户/模型管理、AI、配额、设备调用、Celery 任务尚未逐项调用 `append_audit_event()`；现阶段为关联、脱敏、不可变存储和查询基础，不代表写操作审计覆盖已完成。
- `AIAuditLog` 尚未通过当前请求的 `trace_id` 与统一事件完整关联；AI 历史无归属会话的 90 天归档/清理和 `project_id` 非空收敛也尚未完成。
- PostgreSQL 生产 `stamp`、备份恢复演练、应用账号 `INSERT/SELECT` 与审计只读账号的实际 `GRANT` 尚未执行。`create_all()` 仅能覆盖开发/测试模型，不会安装审计触发器。
