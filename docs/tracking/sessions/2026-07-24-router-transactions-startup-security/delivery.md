# Router 事务与启动安全校验交付记录

## 范围

- 将 HTTP 写操作的事务边界统一到 Router。
- 将 JWT 密钥最小长度提升至 32，并在应用构造时校验。
- 拒绝 credentials 与 CORS 通配来源的危险组合。

## 已完成

- `TransactionalAPIRouter` 为写路由注入函数级事务依赖；成功提交一次，异常回滚并保留 HTTP 错误。
- `create_app()` 在路由注册和可选迁移前完成 JWT 与 CORS fail-fast 校验，`app = create_app()` 保持既有入口。
- 更新 HTTP Service 的常规写路径为 `flush`，并将 LDAP 同步的 Celery 提交/回滚保留在任务入口。
- 更新测试配置、后端分层规范、后端架构及认证/用户同步事实文档。

## 验证

- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test/test_router_transaction_and_startup_security.py test/test_app_config.py test/test_auth_api.py test/test_security_regressions.py test/test_core_api.py test/test_group_tag_contract.py test/test_project_memberships_routing.py test/test_user_management_ldap_sync.py test/test_quota_adjustment.py test/test_vendor_event_definition_admin_api.py test/test_incident_ai_agent.py test/test_telemetry_observability.py -q`
- 结果：211 passed。

## 未验证范围与风险

- 未运行全量后端测试或真实 LDAP、Redis、存储设备和 AI Provider 集成检查。
- 未跟踪的本地 `backend/config.yml` 不随提交修改；部署前必须由配置所有者替换为至少 32 个字符的非占位 JWT 密钥。
