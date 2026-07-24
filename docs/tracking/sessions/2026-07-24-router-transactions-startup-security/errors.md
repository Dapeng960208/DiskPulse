# 本会话错误记录

- [FastAPI 同步 yield 依赖跨线程重置 ContextVar 失败](../../errors/backend/fastapi-yield-dependency-contextvar-cross-thread-reset.md)：已改为无状态 Router 事务检查点适配器。
- [Router 通用写事务提前结束 SSE 会话](../../errors/backend/router-sse-write-transaction-detached-session.md)：流式路由改为显式排除通用事务并使用短检查点。
- [Celery Redis 锁在任务注册期形成循环导入](../../errors/backend/celery-redis-lock-import-cycle.md)：锁客户端改为调用时导入。
- [PostgreSQL 历史数据修复在 SQLite 结构验证中执行](../../errors/backend/postgresql-data-repair-runs-in-sqlite-structure-test.md)：历史数据修复迁移仅在 PostgreSQL 执行。
- [横切 API 与迁移契约变化后测试预期未同步](../../errors/backend/cross-cutting-contract-test-drift.md)：迁移契约改为验证单一 head 与历史修订可达性。
- [已审核厂商事件测试夹具缺少必填处置方案](../../errors/backend/reviewed-vendor-event-fixture-missing-solution.md)：为两个已审核夹具补充处置方案。
- [Vue 模板属性未按仓库 ESLint 换行规则书写](../../errors/frontend/vue-attribute-line-lint.md)：修复全量 lint 发现的既有模板格式问题。
- [前端全量与覆盖率曾保留既有失败](../../errors/frontend/baseline-test-debt.md)：同步当前路由、列表菜单、AI 表单和系统事件窄屏契约；显式 stub inactive lazy tab，避免卸载后的异步 API 导入。
