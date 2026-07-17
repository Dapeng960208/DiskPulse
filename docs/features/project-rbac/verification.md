# 项目级 RBAC 与统一审计验证

## 已完成的本地验证

- 统一审计、配额和 AI 平台聚焦验证：

  ```powershell
  Set-Location backend
  uv run pytest test/test_quota_adjustment.py test/test_project_scope_red.py test/test_unified_audit.py test/test_ai_platform.py -q
  ```

  已通过 `54` 项，覆盖关联 ID 保留/替换、凭据/路径/prompt 脱敏、追加写入不提交事务、SQLite 不可更新/删除触发器、SQLite/PostgreSQL/MySQL 离线 DDL 编译、AI 会话/消息生命周期，以及两类配额调整的同操作 ID attempt/result。

- 认证审计聚焦验证：

  ```powershell
  Set-Location backend
  uv run pytest test/test_auth_api.py -q
  ```

  已通过 `11` 项，覆盖登录成功、无效凭据拒绝、登出撤销和三类认证结果审计；审计摘要不保存口令或 JWT。

- 受影响后端文件已执行 `py_compile`，并已执行 `git diff --check`。

- 主应用成员路由合同：

  ```powershell
  .\.venv\Scripts\python.exe -m pytest backend\test\test_project_memberships_routing.py backend\test\test_project_rbac_memberships.py -q
  ```

  已通过 `7` 项，确认主应用公开项目成员集合的 `GET/POST` 和单成员的 `PATCH/DELETE` 端点。

## 待验证

- 验证未登录、跨项目、角色变更即时生效、项目管理员不得授予 `project_admin`、普通 `editor` 不得调整配额及项目组负责人例外。
- 存储设备采集、Celery 任务和通知链路尚未接入统一审计；仍需覆盖其成功、拒绝、校验失败和设备失败的关联记录。
- 运行项目成员和前端审计页面的聚焦测试；本次文档交付未重新执行浏览器或前端全量测试。
- 在真实 PostgreSQL 变更窗口完成备份恢复、`alembic upgrade`/downgrade、触发器和应用/只读数据库角色权限验证。
- 在当前已接入的认证、成员、AI 和配额范围内补齐失败路径覆盖；最终确认所有记录可按 `request_id`、`trace_id`、`operation_id` 关联。
