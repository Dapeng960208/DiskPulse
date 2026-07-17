# 项目级 RBAC 与统一审计后端

## 当前已实现

- `project_memberships` 保存项目成员及 `reader`、`editor`、`project_admin` 角色；`Project.in_charge_user_id` 会补齐为 `project_admin`，已移除 `pt_user`。
- AI 会话保持创建者隔离且不保存项目归属。AI 工具以当前用户身份签发内部 Bearer token 调用受项目过滤的原 HTTP 路由；历史工具轨迹会按当前成员权限重新检查，范围失效或旧范围不可证明时隐藏助手内容和工具结果。
- `audit_events` 追加式模型、查询 CRUD、`GET /storage-pulse/api/v1/audit-events`、`GET /storage-pulse/api/v1/audit-events/{event_id}`、`X-Request-ID`/`X-Trace-ID` 关联中间件和合并后的 `000000000008_project_rbac_unified_audit.py` 已存在。
- 审计写入通过 `append_audit_event()` 只执行 `add`/`flush`，不替业务事务提交；摘要和 AI 专项审计详情会递归移除凭据、Token、原始 prompt/response 内容及完整路径。迁移为 SQLite、PostgreSQL、MySQL 生成拒绝 `UPDATE`/`DELETE` 的触发器。

## 当前接口与权限

- 统一审计查询支持项目、主体、动作、结果、时间和分页过滤。超级管理员可查询全局；非超级管理员必须指定项目并通过该项目 `project_admin` 校验。
- 项目成员 Router 已注册为 `/storage-pulse/api/projects/{project_id}/members` 的 CRUD 端点，且限制项目管理员只管理 `reader`/`editor`。路由合同已验证 `GET/POST` 成员集合与 `PATCH/DELETE` 单个成员端点由主应用公开。
- `Group`、`StorageUsage`、`LargeFiles` 和可反查的 `StorageAlerts` 均在数据库分页/导出前按项目过滤；无作用域的存储集群、容量池、存储空间和 Qtree（NetApp）只允许超级管理员读取。项目、项目组和用户目录响应返回最小 `capabilities`，仅用作前端展示，后端继续强制授权。
- 项目组负责人可调整其负责项目组及其用户目录的配额；普通 `editor` 不可调整，服务层也拒绝缺失认证主体的直接调用。
- 关联中间件在正常和异常 HTTP 响应均回写 `X-Request-ID`、`X-Trace-ID`。AI 模型创建、更新、删除和连接测试也写入统一审计，并继承请求关联 ID。

## 未完成边界

- `AIAuditLog` 保持既有 AI 专项记录；统一审计不要求 AI 会话绑定 `project_id`。AI 数据隔离同时依赖工具路由的当前用户权限检查和历史读取时的范围再授权。
- PostgreSQL 生产 `stamp`、备份恢复演练、应用账号 `INSERT/SELECT` 与审计只读账号的实际 `GRANT` 尚未执行。`create_all()` 仅能覆盖开发/测试模型，不会安装审计触发器。
