# Router 事务与启动安全校验交付记录

## 范围

- 将 HTTP 写操作的事务边界统一到 Router。
- 将 JWT 密钥最小长度提升至 32，并在应用构造时校验。
- 拒绝 credentials 与 CORS 通配来源的危险组合。
- 修复本次全量验证暴露的后端、前端基线债务，并记录根因和处理方式。

## 已完成

- `TransactionalAPIRouter` 为写路由注入函数级事务依赖；成功提交一次，异常回滚并保留 HTTP 错误。
- AI SSE 路由通过 `@skip_write_transaction` 管理首事件、完成、取消和异常的短事务检查点，不在模型调用期间持有数据库事务。
- `create_app()` 在路由注册和可选迁移前完成 JWT 与 CORS fail-fast 校验，`app = create_app()` 保持既有入口。
- 常规 HTTP Service 写路径改为 `flush`；LDAP 同步任务在 Worker 边界显式提交或回滚，Redis 锁改为调用时导入以断开注册期循环依赖。
- PostgreSQL 专用历史数据修复迁移在 SQLite 结构测试中跳过；迁移契约测试改为验证单一 head 与历史修订可达性。
- 修复前端当前实现与旧测试契约的差异：容量预测入口、AI 模型选择、页面路由矩阵、系统事件窄屏列及 lazy tab 测试隔离。
- 更新后端分层规范、数据库迁移规范、后端架构、认证和用户同步事实文档，以及存储健康窄屏行为说明。

## 验证

- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest -q`（同步主线 `49ed973` 后，`backend/`）：974 passed。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test/test_questdb_time_contract_guard.py test/test_datetime_utils.py -q`（`backend/`）：18 passed。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m compileall -q .`（`backend/`）：通过。
- 合并主线 `efd8504` 的冲突后，`test/test_dashboard_overview.py`：9 passed。
- `pnpm lint`（同步主线 `625a57b` 后，`frontend/`）：通过。
- `pnpm test -- test/unit/storage-cluster-resource-tab-scroll.test.js test/unit/pages/storage-cluster-health-analytics.test.js`：4 passed、15 failed；失败项为组件化后未同步的旧父页面测试。
- 初始功能分支的 `pnpm test`（107 个测试文件、737 项测试）、`pnpm test:coverage` 与 `pnpm build:prod`：均通过。
- `git diff --check`：通过。

## 未验证范围与风险

- 未执行真实 LDAP、Redis、存储设备和 AI Provider 的外部集成调用；现有测试以模拟替身覆盖调用边界。
- 未跟踪的本地 `backend/config.yml` 不随提交修改；部署前必须由配置所有者替换为至少 32 个字符的非占位 JWT 密钥。
- 最终同步 UTC 时间主线后，前端全量 `pnpm test` 仍有 1 个失败（登录 API mock 未实现 `updateCurrentProfile`）和 1 个未处理 rejection（实时页夹具时间格式过时）；用户已明确要求本任务不继续处理，覆盖率与生产构建未在该最终合并状态重跑。
- 同一主线同步新增的 `test/test_utc_time_contract.py` 还暴露 2 个 PostgreSQL 迁移安全契约失败（DDL 前数据检查与锁超时）；用户已明确要求本任务不继续处理。
- 同步 `625a57b` 后，存储集群详情页已将健康分析迁移到子组件，而旧父页面测试仍断言内联实现，聚焦运行产生 15 项失败；用户已明确要求本任务不继续处理。
