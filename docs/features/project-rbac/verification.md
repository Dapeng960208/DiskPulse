# 项目级 RBAC 与统一审计验证

## 已完成的本地验证

- 统一审计聚焦验证：

  ```powershell
  .\.venv\Scripts\python.exe -m pytest backend\test\test_unified_audit.py backend\test\test_group_tag_contract.py -q
  ```

  已通过 `16` 项，覆盖关联 ID 保留/替换、凭据/路径/prompt 脱敏、追加写入不提交事务、SQLite 不可更新/删除触发器，以及 SQLite/PostgreSQL/MySQL 离线 DDL 编译。

- 受影响后端文件已执行 `py_compile`，并已执行 `git diff --check`。

- 主应用成员路由合同：

  ```powershell
  .\.venv\Scripts\python.exe -m pytest backend\test\test_project_memberships_routing.py backend\test\test_project_rbac_memberships.py -q
  ```

  已通过 `7` 项，确认主应用公开项目成员集合的 `GET/POST` 和单成员的 `PATCH/DELETE` 端点。

## 待验证

- 验证未登录、跨项目、角色变更即时生效、项目管理员不得授予 `project_admin`、普通 `editor` 不得调整配额及项目组负责人例外。
- 运行项目成员、AI 项目绑定和前端审计页面的聚焦测试；本次文档交付未重新执行浏览器或前端全量测试。
- 在真实 PostgreSQL 变更窗口完成备份恢复、`alembic upgrade`/downgrade、触发器和应用/只读数据库角色权限验证。
- 为登录/登出、项目和成员管理、配额/设备、AI、Celery 接入统一审计后，验证成功、拒绝、校验失败和设备失败均可按 `request_id`、`trace_id`、`operation_id` 关联。
