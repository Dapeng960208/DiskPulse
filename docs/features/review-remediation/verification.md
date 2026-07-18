# 代码审查问题修复复盘

## 目标与范围

本复盘记录 `main` 相对 `origin/main` 的前端、后端、数据库读写与 Celery 任务审查结论，以及在隔离工作树 `codex/review-fixes` 上的修复和验证。问题按原始严重程度从高到低排列；每个生产修复均在对应代码附近以 `Review fix:` 注释标识，并保留独立 RED/GREEN 提交。

## 审查问题与处置

| 严重程度 | 问题 | 影响范围 | 问题位置 | 修复与提交证据 | 验证状态 | 残余风险 |
| --- | --- | --- | --- | --- | --- | --- |
| 高 | MySQL 升级删除 `projects.pt_user_id` 时未先删除外键，`000000000009` 会中断升级。 | 已在 r8 或更早版本运行 MySQL 的部署；项目级 RBAC 与审计迁移无法继续。 | `backend/migrate/versions/000000000009_project_rbac_unified_audit.py` | RED `ffa5aa6`；GREEN `31cb1e0`。迁移先反射并删除仅引用 `pt_user_id` 的外键，再删除列。 | 迁移组合测试 `10 passed`；SQLite/PostgreSQL/MySQL 离线 DDL 编译、Alembic 链验证通过。 | 未连接真实 MySQL 执行在线 DDL；变更窗口前仍应在目标版本的备份副本执行 upgrade。 |
| 高 | 非超级管理员访问 Dashboard 时会请求无 `project_id` 的全局接口并收到 403，首页不可用。 | 所有尚未选择项目的项目成员。 | `frontend/src/pages/dashboard/DashboardPage.vue` | RED `1fdbdfa`；GREEN `1b1eb15`。非超级管理员未选择项目时不发请求并展示选择提示。 | Dashboard 聚焦 `5 passed`；前端覆盖率全量 `67 files / 412 passed`。 | 未执行已登录浏览器 E2E；项目选择器实际接口由现有 API 集成环境验证。 |
| 高 | 存储告警投递未原子领取任务，可并发重复发送且重试次数失真。 | Celery 重复投递、积压或多 worker 并行消费时的飞书存储告警。 | `backend/celery_tasks/tasks/storage_alerts.py` | RED `599c5ac`；GREEN `a4c935e`。引入 `delivering` 状态和 60 秒租约，仅领取到期记录；过期租约可恢复。 | 存储告警聚焦 `32 passed`；后端全量 `530 passed`。 | 未连接真实 Redis、Celery worker 和飞书服务进行并发/超时演练。 |
| 中 | 采集失败虽然已分类错误码，但运行账本和接口永远写入空 `error_code`；已部署 r8/r9 账本也需要更新终态约束。 | 容量、厂商事件、性能采集的失败诊断、`/telemetry-runs` 与升级到该版本的既有遥测账本。 | `backend/services/telemetryObservabilityService.py`；`backend/models.py`；`backend/migrate/versions/000000000008_telemetry_collection_runs.py`；`backend/migrate/versions/000000000010_telemetry_failed_error_code.py` | RED `0ac1df4` / GREEN `f318160`；r10 RED `95be2ec` / GREEN `c284630`；补强 SQLite 在线升级测试 `4738a04`。失败终态必须保存白名单错误码，r10 替换存量账本约束。 | 遥测聚焦 `36 passed`；SQLite 从 r8 升级到 r10 后写入 `failed/vendor_timeout` 通过；三方言离线 DDL 编译和后端全量 `530 passed`。 | 未连接真实 PostgreSQL/MySQL、QuestDB 或设备 API 验证在线升级与错误分类来源。 |
| 中 | Provider 返回未知工具名时，调用端索引注册表会抛出 `KeyError`，导致 SSE 流异常中断。 | AI 对话中模型产生过期、错误或未注册工具名的请求。 | `backend/services/ai_chat_service.py` | RED `3e4c063`；GREEN `92ded68`。未知工具继续返回安全失败，并完成 SSE 终态与审计可见性。 | AI 服务聚焦 `19 passed`；后端全量 `530 passed`。 | 未使用真实 Provider 发送未知工具名；生产侧仍应观察流终态指标。 |
| 中 | ECharts 懒加载返回后可能对已卸载 DOM 初始化，或让过期渲染覆盖新渲染。 | 所有复用 `use-echarts-chart` 且在 chunk 加载时路由切换/重绘的图表。 | `frontend/src/composables/use-echarts-chart.js` | RED `cd58146`；GREEN `afe0d97`。使用 active 状态和 render generation 使过期异步结果无副作用。 | 图表组合测试 `7 passed`；前端覆盖率全量 `67 files / 412 passed`。 | 未执行浏览器中弱网加载与快速导航压力测试。 |
| 低 | 项目成员新增、编辑、删除的 API 失败被吞掉或变成未处理 rejection。 | 项目管理员进行成员授权变更时的失败反馈与列表一致性。 | `frontend/src/pages/project/components/ProjectMembersTab.vue` | RED `a1a6ec4`；GREEN `9be4fae`。区分用户取消和 API 失败，失败时提示并保留可恢复状态。 | 成员管理聚焦 `2 passed`；前端覆盖率全量 `67 files / 412 passed`。 | 未进行真实项目成员权限 API 的浏览器联调。 |

## 验证汇总

- 后端：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test -q`，`530 passed`。
- 前端覆盖率：`npx vitest run --coverage --reporter=dot`，`67 files / 412 passed`；Statements/Lines `97.90%`、Branches `87.24%`、Functions `82.51%`，高于 `80%` 门槛。
- 前端静态与构建：`npm run lint`、`npm run build:prod` 通过。构建保留既有 `%VITE_APP_TITLE%` 未定义与大 chunk 警告。
- 迁移与语法：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m compileall -q backend`、`D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini heads`、`D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini history` 和 `git diff --check main..HEAD` 通过；Alembic 唯一 head 为 `000000000010`。

## 环境与交付边界

- 新 worktree 不包含根目录 `.venv`，后端测试显式复用 `D:\dev\DiskPulse\.venv\Scripts\python.exe`；不修改依赖声明。
- 新 worktree 初始没有 `frontend/node_modules`，执行 `npm ci` 后前端测试可运行；该环境恢复过程已登记到错误记录。
- 没有真实 PostgreSQL/MySQL、Redis、Celery、飞书、设备 API 或已登录浏览器环境，因此在线迁移、并发投递和端到端交互仍需在部署或集成环境验收。
