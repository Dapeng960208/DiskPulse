# 项目级 RBAC 与统一操作审计实施计划

- 依据：[实施计划索引](./2026-07-17-220000-enterprise-ai-storage-implementation-index.md)
- 状态：本地实施与自动化验收完成；生产数据库与外部设备待验证。
- 前置条件：生产 PostgreSQL 已完成可恢复备份，并已确定数据库变更窗口。

## 目标与边界

- 保留现有 LDAP → JWT → Redis 会话认证和 `super_admin_usernames` 全局管理员语义。
- 增加项目作用域角色 `reader`、`editor`、`project_admin`，使项目资源和成员管理受项目边界保护；AI 会话保持创建者隔离，AI 工具/返回数据按当前用户项目权限过滤；事件确认/认领留给第 05 工作包的 `Incident` 模型。
- 新增追加式统一 `audit_events`，覆盖 HTTP、AI、设备操作与关键管理变更；保留 `ai_audit_logs` 作为既有 AI 专项追踪记录，本工作包不删除它；其最小化和保留策略由第 02 工作包收敛。
- 本工作包不引入 OIDC/SSO、服务账号、双人审批、自治策略、SIEM 转发或设备写权限下放。

## 数据、权限与 API 契约

- 先建立 PostgreSQL Alembic：新增配置与依赖，从现网 schema 创建不可重放的 baseline，生产库在备份/变更窗口内 `stamp`，后续功能只使用显式前向 revision；`create_all()` 只保留给隔离开发/测试，不能作为生产升级机制。对新 revision 同时验证 PostgreSQL upgrade/downgrade 与 SQLite/MySQL DDL 编译兼容性。
- Alembic 新增 `project_memberships`：`id`、`project_id`、`user_id`、`role`、`created_by`、`updated_by`、`created_at`、`updated_at`；唯一约束 `(project_id,user_id)`，索引 `(user_id,project_id)`、`(project_id,role)`。
- `AIConversation` 不绑定 `project_id`。新建和历史会话均仅创建者可见；AI 工具必须以当前用户身份调用受项目过滤的后端接口，绝不返回用户无权访问的项目数据。
- 角色矩阵固定为：
  - `reader`：只读所属项目的容量、性能、告警、项目组、用户目录与受项目过滤的 AI 结果。
  - `editor`：在 `reader` 基础上可更新无设备副作用的项目元数据；不可调整配额、成员、集群、模型、全局规则，亦不可确认或认领尚未实现的 `Incident`。
  - `project_admin`：可管理本项目 `reader`/`editor` 成员和项目级告警规则；不可授予或撤销 `project_admin`，不可跨项目或执行设备写操作。
  - 项目组 `in_charge_user`：仅可调整其负责项目组及其用户目录的配额；该例外不赋予成员管理或全局权限。
  - `super_admin`：保留当前全局访问、配置、集群凭据、模型治理、审计及 `project_admin` 成员管理权限。
- Alembic 新增追加式 `audit_events`：`id(UUID)`、`operation_id(UUID)`、`phase(attempt|result)`、`occurred_at`、`actor_type`、`actor_user_id`、`action`、`resource_type`、`resource_id`、`project_id`、`outcome(success|denied|failure)`、`reason_code`、`before_summary`、`after_summary`、`metadata`、`request_id`、`trace_id`。索引为 `(project_id,occurred_at,id)`、`(actor_user_id,occurred_at,id)`、`(operation_id,occurred_at)`；应用运行账号仅有 `INSERT/SELECT`，无 `UPDATE/DELETE`，并以数据库拒绝更新/删除触发器防止未来代码绕过追加式约束；审计查询使用独立只读角色。
- 所有设备外部调用以同一 `operation_id` 写入 `attempt` 和 `result` 两条审计事件；成功 result 与本地业务写同事务，失败 result 使用独立事务保留，设备调用的双事件不能被吞掉。
- 授权服务提供 `require_project_permission(project_id, minimum_role)` 和由资源反查项目的版本；Router 声明依赖，Service 在写入前再次校验。固定映射为 `Group.project_id` 直连，`StorageUsage.group_id -> Group.project_id`，`LargeFiles.group_id -> Group.project_id`，`StorageAlerts` 仅在 `related_type/related_id` 可反查至 `Group` 或其 `StorageUsage` 时继承该项目。Cluster/Aggregate/Volume/Qtree 以及无法反查的 `StorageUsage`、`LargeFiles`、`StorageAlerts` 都是无作用域资源，仅 `super_admin` 可见/操作；不得回退为所有项目角色可见。
- 请求中间件在每个 HTTP 请求创建或接收受校验的 `request_id`/`trace_id`，并向 AI、Celery 和设备调用传播；所有统一审计记录必须带该关联值。
- 新接口：
  - `GET/POST /storage-pulse/api/projects/{project_id}/members`
  - `PATCH/DELETE /storage-pulse/api/projects/{project_id}/members/{user_id}`
  - `GET /storage-pulse/api/v1/audit-events`
- 成员 API 只接收本地已存在 `users.id`，不得触发 LDAP 账号创建；项目管理员只可管理 `reader`、`editor`。审计查询只对超级管理员和项目管理员开放，响应只含脱敏摘要。

## 实施步骤

## 实施状态（2026-07-18）

- 已完成：`project_memberships`、`pt_user` 删除、项目负责人角色补齐、成员 Router 注册、资源反查过滤、独立 AI 会话、当前权限下的 AI 历史再授权、项目成员/项目审计前端页签、统一审计模型/合并迁移/关联 ID/脱敏/查询基础和统一审计前端页面。
- 已完成：认证、成员、配额、AI 生命周期、AI 模型治理、采集、通知和管理写入的统一审计；`audit_events` SQLite 运行时不可变触发器验证、SQLite/PostgreSQL/MySQL 离线 DDL 编译及遥测 r8 → RBAC/审计 r9 的 SQLite 实际 `r7 → r9 → r7` 迁移验证。
- 已完成：本地后端全量、迁移、配额、AI、前端聚焦和构建验收。生产数据库角色授权、备份恢复、真实 PostgreSQL 变更窗口、设备与通知联调仍待上线前验证。

1. 在 `backend/test/` 先补角色矩阵、跨项目读取/写入、成员管理和审计序列化的 RED 测试；复用现有 JWT/SQLite fixture，不修改生产逻辑。
2. 建立 Alembic baseline 并在生产变更窗口完成 `stamp` 演练后，创建前向 revision、ORM 模型、Pydantic schema、CRUD 与授权/审计 service；迁移仅以 `Project.in_charge_user_id` 初始化 `project_admin`，删除 `pt_user_id`，空项目由超级管理员补齐。
3. 保持 AI 会话创建者隔离；将项目、项目组、用户目录、项目关联告警、大文件、Dashboard 和 AI 工具读取收敛到项目过滤。为每类资源建立可测试的 `project_id` 反查规则；列表查询必须先按作用域过滤再分页或统计。
4. 接入 `editor`/`project_admin` 可写范围；普通 `editor` 不可调整配额，项目组负责人仅可调整其负责项目组及其用户目录；存储集群、用户、模型和全局配置继续保持 `super_admin` 限制。
5. 为项目、配额、集群、用户、模型、AI 工具调用和登录/登出接入统一审计；由中间件传播的 `trace_id` 关联 `AIAuditLog`、HTTP、Celery 和设备操作；以数据库权限/触发器验证审计不可修改或删除。
6. 新增成员与审计前端页面/API client/路由守卫，后端鉴权仍是唯一安全边界。
7. 同步认证、AI、项目与审计文档，更新 `docs/overview/latest-features.md`、`docs/tracking/current-release.md`；可复现的权限或迁移问题写入 `docs/tracking/error-log.md`。

## 验证与验收

- RED/GREEN：未登录 `401`、跨项目 `403/404`、角色矩阵、成员唯一性、权限即时失效、项目管理员不可授予 `project_admin`、无作用域资源拒绝项目角色、AI 会话创建者隔离、AI 工具项目过滤、先过滤后分页均需有聚焦测试。
- 审计测试覆盖成功、拒绝、输入校验失败和设备失败；断言凭据、Token、完整敏感路径、原始模型提示词和设备响应都不进入数据库摘要或 API，并验证应用角色/触发器拒绝审计更新和删除。
- 运行聚焦后端和前端测试、Alembic upgrade/DDL 验证、`git diff --check`；真实 PostgreSQL 在变更窗口完成 backup/restore 前置验证。
- 验收：跨项目越权为零；纳入范围写操作审计覆盖率 `100%`；既有超级管理员 API 无行为回归；AI、HTTP、设备操作可由 `trace_id`/`operation_id` 关联。
