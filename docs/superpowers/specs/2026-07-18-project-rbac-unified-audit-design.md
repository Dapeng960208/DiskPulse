# 项目级 RBAC 与统一操作审计设计

- 关联实施计划：[项目级 RBAC 与统一操作审计实施计划](../plans/2026-07-17-220100-project-rbac-unified-audit-implementation-plan.md)
- 状态：已确认，待实施。

## 目标与边界

在保持 LDAP、JWT、Redis 会话和全局 `super_admin_usernames` 语义不变的前提下，为项目数据增加 `reader`、`editor`、`project_admin` 三个项目作用域角色，并为关键业务操作写入追加式统一审计事件。

本轮不实现 OIDC/SSO、服务账号、双人审批、SIEM 转发、设备写权限下放或尚未存在的 Incident 确认/认领能力。

## 数据与授权设计

新增 `project_memberships`，以 `(project_id, user_id)` 唯一约束保存角色、创建者、更新者及时间。`project_admin` 只能管理本项目的 `reader` 与 `editor`；只有 `super_admin` 可以授予或撤销 `project_admin`。既有项目负责人和 PT 负责人会在迁移中去重初始化为 `project_admin`。

授权服务提供项目 ID 及资源反查两种校验入口。`Group` 直接归属项目；`StorageUsage` 与 `LargeFiles` 经所属项目组归属项目；仅能可靠反查至项目组或用户目录的 `StorageAlerts` 继承其项目。无作用域资源继续只允许 `super_admin` 读取或操作。列表和统计必须先按作用域过滤，再分页。

采集规则：当采集写入或更新一个可经 `StorageUsage -> Group -> Project` 确认的用户目录时，确保目录所属用户拥有该项目的 `reader` 成员关系。此操作幂等：已有 `reader` 不重复创建，已有 `editor`、`project_admin` 或全局超级管理员不降级；无法反查项目的目录不触发授权。

## 审计与关联设计

新增只追加 `audit_events`，包含操作、阶段、主体、资源、项目、结果、脱敏前后摘要和 `request_id`/`trace_id`。HTTP 中间件生成或校验关联 ID，并传播给 AI、Celery 和设备调用。设备外部调用按一个 `operation_id` 写 `attempt` 与 `result` 两条记录；事务内业务写和审计写同成同败。数据库触发器拒绝更新和删除，应用账户只拥有读取与写入权限。

审计响应只返回脱敏摘要；不得持久化凭据、令牌、完整敏感路径、原始模型提示词或原始设备响应。

## 接口与前端设计

成员管理使用项目嵌套资源：`GET/POST /projects/{project_id}/members` 与 `PATCH/DELETE /projects/{project_id}/members/{user_id}`。审计查询使用 `GET /audit-events`，只允许超级管理员和具有相关项目审计范围的项目管理员访问。Pydantic schema 负责输入校验，路由声明鉴权依赖，service 在每次写入前复核授权。

前端按现有 API 模块、路由和菜单模式增加项目成员与审计浏览入口。路由守卫只改善体验；后端授权仍是唯一安全边界。

## 迁移、测试与运维边界

先建立 PostgreSQL baseline/stamp 演练，再提交显式前向 Alembic revision。迁移、模型索引和 SQLite/PostgreSQL/MySQL DDL 兼容性必须同步验证。生产库备份、恢复演练、变更窗口、`stamp` 及审计数据库角色/权限配置需由具备生产授权的运维人员执行。

测试先覆盖未登录、跨项目拒绝、角色矩阵、成员唯一性和授权即时失效、自动 `reader` 补齐及不降级、无作用域资源拒绝、先过滤后分页、AI 会话归属和审计脱敏/追加性。每个 RED/GREEN 阶段运行对应聚焦测试；完成后运行迁移、前端和安全复核。
