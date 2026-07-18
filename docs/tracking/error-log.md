# 错误记录

### 2026-07-18：前端 Mock 缺少一条命令可用的启动入口

- 触发：在 `frontend/` 尝试直接通过包管理器启动 Mock 网页，并运行新增的启动契约测试。
- 现象：只能手工设置 `VITE_USE_MOCKS=true`；RED 测试读取 `.env.mock` 时返回 `ENOENT`。
- 根因：`package.json` 没有 Mock 专用脚本，仓库也没有为 Vite `mock` 模式提交环境文件。
- 修复：新增 `pnpm mock` 对应的 `vite --host --mode mock` 脚本，并显式提交仅包含 `VITE_USE_MOCKS=true` 的 `.env.mock`。
- 验证：Mock 运行时 `6 passed`；严格执行 `pnpm mock` 后自动端口返回 HTTP 200 且页面包含 Vue 应用根节点。
- 风险：启动输出保留既有 `%VITE_APP_TITLE%` 未定义警告；Mock 仅用于本地演示，不连接真实后端。

### 2026-07-18：Mock 启动探针把端口参数放在 Vite 分隔符之后

- 触发：使用 `pnpm mock -- --host 127.0.0.1 --port 5192` 为自动探针指定端口。
- 现象：Vite 输出中参数位于字面量 `--` 之后，忽略指定端口并按 5173 起自动选择可用端口。
- 根因：`pnpm` 已把脚本后的参数传给 Vite，额外的 `--` 成为 Vite 参数分隔符，其后的 host/port 不再作为 CLI 选项解析。
- 修复：验收严格执行原始 `pnpm mock`，从 Vite 启动输出提取实际自动端口后发起 HTTP 探针，并按精确进程树回收测试服务。
- 验证：自动识别端口 5176，HTTP 状态为 200，页面含 `<div id="app"></div>`。
- 风险：5173 至 5175 已被其他本地服务占用；本次未停止或修改这些既有进程。

### 2026-07-18：分支全量 ESLint 被既有登录页模板格式阻塞

- 触发：对 `codex/review-remediation-20260718` 执行前端全量 ESLint。
- 现象：`LoginPage.vue` 第 119、121 行报告 5 个 `vue/max-attributes-per-line` 错误。
- 根因：既有 Mock 快捷登录按钮把多个属性写在同一行，不符合当前 Vue ESLint 规则；本次 `pnpm mock` 入口没有修改该文件。
- 修复：在独立低优先级提交中把 Mock 账户容器和按钮的属性逐行排列，不改变登录行为或样式。
- 验证：同一全量 ESLint 命令通过且无错误；此前前端全量单测为 `72 files / 426 tests passed`，生产构建通过。
- 风险：仅做模板格式整理，未新增浏览器交互验证；既有 Mock 登录单测继续覆盖账户填充行为。

### 2026-07-18：关联 ID 中间件 fallback 500 缺少服务端异常日志

- 触发：下游在响应开始前抛出未处理异常，由 `CorrelationIdMiddleware` 发送 fallback 500。
- 现象：客户端安全收到 500 和关联 ID，但服务端没有对应 ERROR/堆栈记录。
- 根因：中间件捕获异常后直接返回，只有响应已开始的异常才重新抛给服务器记录。
- 修复：发送 fallback 500 前使用模块 logger 记录异常上下文和已校验的 request/trace ID；响应不包含异常消息或堆栈。
- 验证：关联 ID 与 AI 管理审计测试文件 `2 passed`，断言日志含关联 ID 和 `exc_info`，客户端不含 `boom`。
- 风险：日志后端的保留期、采集和告警规则未在本地验证；本次不记录请求体、认证头或其他潜在敏感数据。

### 2026-07-18：乱序证据回拨 Incident 最近证据时间

- 触发：先关联 08:10 的证据，再接收同一事件桶内迟到的 08:05 唯一证据。
- 现象：`last_evidence_at` 从 08:10 回拨为 08:05。
- 根因：既有 Incident 分支无条件用当前输入的 `observed_at` 覆盖汇总时间。
- 修复：统一使用 `max(current, observed)` 更新汇总时间；证据行继续保存自身原始 `observed_at`。
- 验证：乱序证据与同桶/跨桶重开回归合计 `3 passed`。
- 风险：本地未模拟多个 Celery worker 对同一 Incident 的数据库级并发更新；部署环境仍需观察锁与事务隔离行为。

### 2026-07-18：Mock 通用表映射暴露系统资源给项目角色

- 触发：使用 `demo-project-admin` 读取 `/storage-clusters` 等系统资源。
- 现象：请求返回 `200` 和系统清单，项目管理员还可进入通用写入分支。
- 根因：Mock 只限制 `/admin` 前缀，系统资源 API 使用独立资源前缀并被通用 `tableMap` 直接处理。
- 修复：集中声明系统资源前缀，在列表、详情和写入分发前统一要求 `superadmin`；个人资料和登出路径显式排除。
- 验证：Mock 运行时系统/项目资源回归 `5 passed`。
- 风险：Mock 仍是本地内存实现，不替代真实后端权限验收；新增系统 API 时需同步该集中边界。

### 2026-07-18：AI 页面聚焦测试从仓库根目录启动导致别名解析失败

- 触发：在仓库根目录调用主工作区 Vitest 二进制运行 `frontend/test/unit/ai-pages.test.js`。
- 现象：Vite 报 `Failed to load url @/pages/ai/AiChatPage.vue`，测试文件显示 `0 test`。
- 根因：前端 Vite 配置和 `@/` 别名以 `frontend/` 为项目根；从仓库根启动使配置根目录错误。
- 修复：将工作目录切换到目标 worktree 的 `frontend/` 后运行相同相对测试路径。
- 验证：`ai-pages.test.js` 通过 `16 tests`。
- 风险：独立 worktree 仍复用主工作区 `node_modules`；命令必须保持目标 `frontend/` 为当前目录。

### 2026-07-18：AI 配额确认卡片无法从会话历史恢复

- 触发：生成 AI 配额确认后刷新页面或重新打开所属会话。
- 现象：实时 SSE 曾显示确认卡片，但历史助手消息不包含 `quota_confirmation`。
- 根因：会话序列化只恢复工具轨迹和状态，没有从持久化审计提取待确认元数据；原返回值也缺少绝对过期时间。
- 修复：审计持久化绝对 `expires_at` 和安全预览；历史只对会话所有者序列化未过期确认，并对白名单预览字段过滤，不读取 Redis 工具参数。
- 验证：后端 AI/配额聚焦 `48 passed`，前端 AI 页面 `16 passed`。
- 风险：未连接真实 Redis 或 Provider 验证刷新后点击确认；Redis 一次性消费和确认时超级管理员复验逻辑未改变。

### 2026-07-18：r10 降级无法接纳已分类的失败遥测行

- 触发：r8 账本升级 r10、写入带 `vendor_timeout` 的失败行后执行 r10 downgrade。
- 现象：SQLite 表重建复制数据时报 `CHECK constraint failed: ck_telemetry_run_terminal_fields`。
- 根因：旧终态约束要求失败行 `error_code IS NULL`，但降级直接恢复旧约束，没有先转换 r10 新增的数据状态。
- 修复：先移除 r10 终态约束，清空失败行分类错误码，再恢复旧约束；SQLite 通过无终态约束的中间表完成两阶段重建。
- 验证：SQLite 实际升降级和 SQLite/PostgreSQL/MySQL 离线迁移合计 `4 passed`。
- 风险：降级会有意丢弃旧 schema 无法表达的失败分类码；真实 PostgreSQL/MySQL 在线降级仍须在备份与维护窗口验收。

### 2026-07-18：性能资产厂商标识与整数 Volume 主键比较

- 触发：使用 UUID 形式的性能 `object_id` 解析 Volume 资产，并检查生成的 SQL。
- 现象：查询条件同时生成 `volumes.id = <UUID>`；PostgreSQL 会拒绝整数列与文本 UUID 的比较。
- 根因：资产映射无条件把厂商 `object_id` 同时用于名称列和整数 `Volume.id`。
- 修复：UUID/名称只匹配 `Volume.name`；仅 ASCII 纯数字 `object_id` 转为整数后参与主键匹配。
- 验证：新增 SQL 契约与连续性能异常回归合计 `3 passed`。
- 风险：未连接真实 PostgreSQL 与厂商性能接口回放；数值型主键路径保持既有行为但仍需部署环境数据验收。

### 2026-07-18：同一关联桶内已解决事件未被新证据重开

- 触发：先在 30 分钟关联桶内创建并解决 Incident，再在同一桶写入新的唯一证据。
- 现象：关联结果返回 `reopened=False`，Incident 保持 `resolved`。
- 根因：服务先按关联桶命中 Incident，只有未命中时才查询 24 小时内已解决事件并执行重开。
- 修复：把已解决状态判断提升为统一重开分支，同桶命中和跨桶回查共用同一状态迁移与时间线逻辑。
- 验证：新增同桶回归与既有跨桶 24 小时重开用例合计 `2 passed`。
- 风险：真实并发采集与数据库锁竞争未在本地复验；乱序证据的时间单调性由后续独立问题处理。

### 2026-07-18：事件中心新增后路由测试契约未同步

- 触发：运行 `content-spacing-contract.test.js` 与 `routes-dynamic-import.test.js` 聚焦测试。
- 现象：在用页面矩阵期望 24、实际 25；懒加载组件期望 28、实际 29。
- 根因：事件中心已经注册为新的懒加载页面，但两个穷举式路由测试仍保留新增前的固定集合和数量。
- 修复：页面矩阵显式加入 `IncidentCenterPage`，懒加载测试增加对应模块 Mock，并同步两个精确数量断言。
- 验证：同一聚焦命令通过 `2 files / 12 tests`。
- 风险：固定数量契约仍要求以后新增或移除路由时显式更新测试，这是有意保留的审查门禁。

### 2026-07-18：已移除的功能 worktree 被 CodeGraph 与 Vite 进程占用

- 触发：完成 `main` 本地合并后删除 `codex/project-rbac-unified-audit` worktree。
- 现象：Git 删除返回 `Invalid argument`；PowerShell 随后报告 `.codegraph/codegraph.db` 和 `frontend` 目录正被其他进程使用。
- 根因：该 worktree 的 CodeGraph 索引 daemon 和 Vite 预览进程仍在运行，分别持有索引数据库和前端目录句柄。
- 修复：按 daemon PID 和命令行仅结束指向该 worktree 的 CodeGraph/Vite 进程，再删除孤立目录并执行 `git worktree prune`。
- 验证：`git worktree list` 仅保留 `D:/dev/DiskPulse [main]`；`codex/project-rbac-unified-audit` 分支已删除，主工作区干净。
- 风险：后续启动临时 worktree 服务时，清理前仍须先停止该 worktree 下的索引与前端进程。

### 2026-07-18：并行分支复用了 Alembic revision `000000000008`

- 触发：将遥测可观测与项目 RBAC/统一审计分支合并，并执行迁移唯一 head 与 SQLite 升降级回归。
- 现象：Alembic 报告 revision `000000000008` 重复；RBAC 测试虽然指定 r8，但实际只执行遥测表，`pt_user_id` 未删除。
- 根因：两个独立工作包都以 r7 为上游并分配了 r8，不能在已存在 r8 的主线中继续复用 revision ID。
- 修复：保留 `000000000008_telemetry_collection_runs.py` 不变，RBAC/审计迁移改为显式前向 `000000000009_project_rbac_unified_audit.py`，并更新所有迁移契约。
- 验证：新唯一 head 预期 RED；修复后 `alembic heads` 为 `000000000009 (head)`，遥测/RBAC 迁移回归 `38 passed`，完整后端回归 `526 passed`。
- 风险：生产仍需在备份和变更窗口内验证 r8 已执行环境到 r9 的真实 upgrade；r9 的 `pt_user_id` 数据恢复限制不变。

### 2026-07-18：metrics 抓取复用了应用数据库连接池

- 触发：对 `/storage-pulse/api/v1/metrics` 进行 CodeGraph 实现复查，并新增路由和专用连接生命周期回归测试。
- 现象：Router 将全局 `SessionLocal` 作为参数传入 `render_metrics`；指标读取可能占用正常 API 的 PostgreSQL 连接池，偏离探针专用 `pool_size=1` 连接契约。
- 根因：指标服务支持 session factory 注入以便测试，但生产 Router 直接复用了业务 factory，未在服务层为默认抓取创建专用 engine。
- 修复：Router 不再导入或传入 `SessionLocal`；服务在默认路径使用 `_probe_engine(..., pool_size=1)` 和专用 `sessionmaker`，并在单次抓取结束时 `dispose()`；测试注入能力保留。
- 验证：RED 分别得到路由实参不符和缺少 `sessionmaker` 的预期失败；GREEN 后遥测聚焦 `32 passed`、后端全量 `442 passed`。
- 风险：真实数据库连接超时、并发抓取和 P95 仍需部署环境验证。

### 2026-07-18：独立 worktree 缺少运行时配置，无法执行真实 PostgreSQL Alembic 升降级

- 触发：在 `D:\dev\DiskPulse\.worktrees\telemetry-observability\backend` 执行 `D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head`。
- 现象：Alembic 在加载 `appConfig.py` 时提示 `Configuration file not found: ...\backend\config.yml`，未建立数据库连接或执行迁移。
- 根因：`backend/config.yml` 是未跟踪的部署运行时配置，独立 Git worktree 只复制受版本控制文件，不应复制真实数据库凭据。
- 修复：未创建或复制真实配置；本次改用 SQLite 实际 upgrade/downgrade 与 SQLite/PostgreSQL/MySQL 离线 DDL 编译测试验证 `000000000008`。
- 验证：新增迁移测试通过，`alembic heads` 显示唯一 `000000000008`。
- 风险：真实 PostgreSQL 的升级、回退、外键 `ON DELETE SET NULL` 和连接超时行为仍需由部署环境使用受控运行时配置验收。

### 2026-07-18：AI 会话续聊可重新暴露已撤销项目权限的数据

- 触发：对“不绑定项目 ID 的 AI 会话”执行合并前权限复查；先创建含项目工具结果的回合，再撤销成员资格并继续对话或读取历史。
- 现象：服务端把原助手正文直接交给模型续聊；后续没有工具调用的总结回合也没有继承先前的项目可见范围，可能在新 SSE 或历史 API 中泄露失权数据。
- 根因：历史读取只用单回合审计 trace 判定可见性；无工具或 legacy 回合被默认视为全局可见，模型输入路径没有按当前权限过滤。
- 修复：无权助手正文在模型输入和历史响应中替换为受限占位；新回合合并会话历史范围和当前工具范围；缺少 audit/visibility 的旧助手消息 fail-closed。
- 验证：RED 提交 `187aa4c` 覆盖撤权续聊、跨回合范围继承与 legacy 场景；GREEN 提交 `eaecab7` 后 AI 历史/服务/平台及关联审计组合 `81 passed`。
- 风险：真实 Provider 对受限占位的回答质量需在不含生产数据的测试会话中抽检。

### 2026-07-18：统一审计未覆盖原始响应字段别名

- 触发：对审计脱敏名单进行合并前安全复查，输入 `response`、`raw_response`、`device_response` 和 `body` 字段。
- 现象：原实现只识别部分 `response_payload` 命名，别名字段可能以截断文本写入审计摘要。
- 根因：通用敏感字段匹配未包含 `response` 与 `body` 词根。
- 修复：将两者加入统一脱敏名单，覆盖上述响应别名的递归脱敏。
- 验证：RED 提交 `6da29b5` 预期失败；GREEN 提交 `7be0180` 后统一审计文件 `13 passed`。
- 风险：后续新增外部 Provider 字段仍须随接入添加脱敏回归。

### 2026-07-18：Alembic 执行后 pytest 无法捕获采集调度日志

- 触发：执行 `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test -q`。
- 现象：`test_storage_collection_trigger.py` 两条断言在单文件通过、全量运行失败，`caplog.text` 为空。
- 根因：Alembic `env.py` 的 `fileConfig()` 替换了 root handlers，移除了 pytest 的捕获 handler。
- 修复：仅在 root 尚无 handler 时加载 Alembic INI 日志配置；CLI 仍获得默认日志配置，宿主应用和测试保留自身 handler。
- 验证：新增 RED/GREEN 后，迁移日志回归与采集调度组合 `12 passed`，后端全量 `490 passed`。
- 风险：生产 CLI 日志行为未在真实 PostgreSQL 变更窗口验证。

### 2026-07-18：合并 RBAC 审计迁移会丢失项目告警规则

- 触发：在 SQLite 执行 `000000000007 → 000000000008 → 000000000007`。
- 现象：batch `copy_from` 未包含 `projects.storage_alert_rule`，升级或降级后列/JSON 值可能丢失。
- 根因：合并后的 SQLite 迁移只复制了部分旧项目列。
- 修复：在迁移的 SQLite 批处理结构中保留 `storage_alert_rule`，并补唯一 head、三方言 DDL 与实际升级/降级测试。
- 验证：迁移专题测试 `6 passed`；SQLite、PostgreSQL、MySQL 离线 DDL 均编译通过。
- 风险：删除的 `pt_user_id` 历史值仍不可由 downgrade 恢复，升级前必须备份。

### 2026-07-18：配额测试意外连接真实 Kombu broker

- 触发：执行 `backend/test/test_quota_adjustment.py -q`。
- 现象：前三项后阻塞在 Kombu broker 投递；中断后显示 `3 passed in 85.59s`，栈落在 `kombu.utils.functional.py:332`。
- 根因：配额成功路径默认向 Celery 投递通知，测试没有隔离异步 enqueue。
- 修复：测试文件默认将 enqueue 替换为 no-op；需要断言入队的用例显式 monkeypatch，生产投递逻辑未改。
- 验证：配额聚焦测试 `19 passed in 1.74s`；服务层无认证主体调用另有 RED/GREEN，现返回 `401`。
- 风险：真实 broker、设备与通知投递仍需部署环境联调。

### 2026-07-18：AI 历史和审计详情可能暴露过期或敏感工具数据

- 触发：撤销项目成员关系后读取同一创建者的 AI 历史，或读取包含旧 prompt/path/response 的 AI 审计详情。
- 现象：历史助手消息和工具结果仍可返回；AI 审计详情可返回完整路径、prompt、token 或原始 response。
- 根因：会话只检查创建者，历史轨迹没有范围再授权；AI 专项审计读取没有二次脱敏。
- 修复：每个工具轨迹保存脱敏可见范围，读取时按当前成员权限重新判定；范围失效/不可证明时隐藏整轮内容；AI 专项审计读取再次脱敏并继承请求 trace。
- 验证：AI 权限、脱敏与既有 AI 平台/服务回归 `48 passed`，后端全量 `490 passed`。
- 风险：生产环境需按真实权限撤销和 Provider 响应进行脱敏抽检。

### 2026-07-18：前端全量 coverage 被过期测试隔离契约阻断

- 触发：执行 `npm run test:coverage`。
- 现象：布局、应用壳、告警路由和组件烟测共 5 条失败；其中出现 CRLF 下样式选择器失效、未激活 Pinia、路由元数据顺序假设和深层 API 基类为 `undefined`。
- 根因：测试依赖了平台行尾、实现字段相邻顺序，或在 smoke 场景加载了不属于当前包装页边界的 store/API/异步子树。
- 修复：使用跨行尾选择器并放宽非语义元数据顺序；为 AppLayout 补齐 breadcrumbs/router Pinia 隔离，为详情烟测 mock 深层依赖和 Element Plus 子组件。未修改生产页面、路由或样式。
- 验证：四个目标文件共 `28 passed`；全量 coverage 无失败，Lines/Statements `97.67%`、Functions `82.26%`、Branches `87.40%`；`npm run build:prod` 通过。
- 风险：构建仍保留 `%VITE_APP_TITLE%` 未定义和大 chunk 警告；两者不影响本轮功能正确性。

### 2026-07-17：AI 工具轮次和参数格式错误被泛化为服务不可用

- 触发：AI 对话连续调用只读工具达到 `ai.max_tool_iterations`，或 Provider 输出非 JSON/非对象的工具参数。
- 现象：已完成的工具调用仍显示成功，但助手消息被统一替换为“AI 服务暂时不可用”，用户无法基于已有信息继续，也没有机会授权新的查询回合。
- 根因：工具轮次上限和客户端参数解码异常直接抛出 `AIClientError`，进入通用 `error` SSE 分支；前端只检查 HTTP/读取异常，未验证 SSE 是否收到确认和终态事件。
- 修复：为非法参数保留安全上下文并最多两次反馈模型修复；上限或修复耗尽时改为无工具总结与本地降级回退，持久化 `degraded`/`recovery`；前端校验 SSE 终态并显示继续或重新查询操作。
- 验证：后端 AI 聚焦测试 `32 passed`，前端 AI 聚焦测试 `24 passed`，目标 ESLint、Python 编译和生产构建通过；登录态页面加载、历史会话切换通过。
- 风险：真实 Provider 的工具调用格式和无工具总结需在部署环境以脱敏测试会话继续联调；原始非法参数始终不得进入 SSE、审计或用户文案。

### 2026-07-17：AI 工具调用在刷新会话后消失

- 触发：在“AI 助手”发起会调用工具的提问，观察回复过程中的工具状态后刷新页面或重新打开同一会话。
- 现象：流式期间可看到工具调用，但历史消息只保留助手文本；刷新后工具名称、状态和返回信息全部消失，且无法判断它们属于哪一条助手回复。
- 根因：前端把工具状态保存在会话级临时 `toolStatus`，打开会话时直接清空；服务端只在完成后创建助手消息，SSE 工具事件没有稳定 `turn_id`/`call_id`，审计工具摘要也没有与助手消息建立可供会话历史恢复的关联。
- 修复：开始 SSE 前预创建助手消息和运行中审计；所有事件以 `turn_id` 关联，工具以 `call_id` 原位更新；工具轨迹在开始/结束时持久化，并由会话详情合并到所属助手消息。
- 验证：后端 AI 聚焦测试 `27 passed`，前端聊天、SSE 和 API 聚焦测试及目标 ESLint 通过，覆盖实时文本、同名多次工具调用、成功/失败/取消、`32 KiB` 截断、会话隔离与刷新恢复。
- 风险：工具结果可能包含业务数据，持久化展示必须继续受会话所有者和原业务接口权限约束，管理员审计不得因此暴露未脱敏参数或完整结果。

### 2026-07-17：项目组和用户目录详情动态模块加载失败

- 触发：在项目组或用户目录列表点击“详情”，或在全新浏览器会话直接打开 `/group/1`、`/usage/1`。
- 现象：Row/Col 的 Element Plus 样式优化依赖返回 `504 Outdated Optimize Dep`，Vue Router 随后报 `Failed to fetch dynamically imported module`，详情页无法进入。
- 根因：`GroupDetailPage.vue`、`UsageDetailPage.vue` 和共享 `RealTimePage.vue` 都保留了模板未使用的 `ElRow`、`ElCol` 导入；Element Plus 插件为它们生成样式请求，而浏览器持有的 Vite optimize-deps 版本已经失效。
- 修复：删除三处无用 Row/Col 导入；未通过路由重试或异常吞并掩盖问题，也未修改页面字段和接口。
- 验证：静态契约先得到 `2 failed`，补充共享页后再次得到 `1 failed, 2 passed`；修复后为 `3 passed`。详情路由组合测试共 `14 passed`，目标 ESLint、生产构建通过；全新浏览器访问两个详情路由均无 `504` 和动态导入错误。
- 风险：浏览器复验未携带登录令牌，真实业务 API 返回 `401`，因此只验证了路由模块加载；用户现有标签页需要刷新一次。

### 2026-07-17：趋势图视觉验收发现分段色被固定线色覆盖

- 触发：使用 Mock API 在 `1440×900` 浏览器中验收 Dashboard 容量趋势，并执行后端全量 `uv run pytest -q`。
- 现象：阈值线和标签颜色正确，但单对象曲线仍整体显示为蓝色；后端全量另有 1 条存储集群容量变化旧断言失败，结果为 `391 passed, 1 failed`，因为响应新增了 `trend_meta`。
- 根因：单对象 series 同时设置了固定 `lineStyle.color` 和 `visualMap`，固定线色覆盖了分段视觉映射；存储健康旧测试仍要求响应完全等于新增字段前的 payload。
- 修复：单对象不再设置固定线色，让四段 `visualMap` 生效，多对象仍显式保留身份色；新增回归断言锁定该配置，并让容量变化旧测试显式校验和移除 `trend_meta` 后再比较原 payload。
- 验证：新断言先复现为 `1 failed, 3 passed`，修复后为 `4 passed`；浏览器实图确认蓝、金黄、橙、红在阈值处换色，Tooltip 与三级线正常。后端全量 `392 passed`，前端全量 `351 passed`。
- 风险：浏览器使用 Mock API，未核对真实 QuestDB 历史；`390×844` 下趋势图自身没有越界，但既有顶部用户操作区仍使应用壳产生约 `39px` 横向溢出，不属于本次图表实现。

### 2026-07-17：原 90% 前端 coverage gate 阻塞全量 CI

- 触发：执行前后端全量覆盖率门禁。
- 现象：后端 coverage 已达到 `91%`；前端 `294` 个测试全部通过，但 Branches `89.84%`、Functions `83.95%` 未达到原四项 `90%` 门禁。
- 根因：当前前端真实业务分支和函数仍有未覆盖路径，测试本身没有失败。
- 修复：按当前交付要求将后端门禁调整为 `85%`、前端四项门禁调整为 `80%`，未扩大 coverage 排除范围。
- 验证：前端在新门禁下通过；后端全量测试及 coverage 通过。远端 GitHub Actions 尚未执行。
- 风险：后续若恢复更高门禁，仍需继续补充前端分支和函数测试。
### 2026-07-16：前端全量回归仍断言已移除的 LDAP 与目录移动入口

- 触发：执行 `npm test` 和 `npm run test:coverage`。
- 现象：`user-management-ldap-sync.test.js` 两项找不到“新增用户”和“同步 LDAP 用户”，`write-form-experience.test.js` 一项找不到“移动用户目录 / 移动目录”；结果均为 `272 passed, 3 failed`。
- 根因：页面已在此前系统设置废弃配置清理中移除 IAM/LDAP 集成和用户目录移动入口，但三条旧测试契约仍保留。
- 修复：本轮不恢复已废弃功能，也不把无关测试清理并入使用率改动；在主工作区同一基线上复跑相同两份测试，确认同样为 `15 passed, 3 failed`。
- 验证：排除两份已失效契约后覆盖率回归 `44 files / 257 passed`，Statements/Lines `92.69%`、Branches `83.26%`、Functions `68.19%`。
- 风险：前端全量与默认覆盖率命令保持非零退出；后续应单独删除或改写这三条废弃功能断言。

### 2026-07-16：Vitest exclude 参数重复传值被 CLI 拒绝

- 触发：为确认其余前端覆盖率，连续传入两个 `--exclude` 参数。
- 现象：Vitest 报 `Expected a single value for option "--exclude <glob>"`，未开始测试。
- 根因：当前 Vitest CLI 的 `--exclude` 只接受一个 glob 值。
- 修复：改用单个 brace glob：`--exclude "test/unit/{user-management-ldap-sync,write-form-experience}.test.js"`。
- 验证：修正后 `44 files / 257 passed` 并生成覆盖率摘要。
- 风险：仅影响验证命令形状，不影响生产代码。

### 2026-07-16：列表页挂载测试加载了被整体 mock 的 API 基类

- 触发：为共享 `Progress` 增加 Pinia 阈值缓存后，运行存储空间、容量池和 Qtree 列表的既有挂载测试。
- 现象：三个用例均报 `Class extends value undefined is not a constructor or null`，堆栈落在 `UsersApi extends CrudApi`。
- 根因：测试只在挂载配置中 stub `Progress`，模块加载阶段仍执行真实组件依赖；该测试环境又整体替换了 API 基类，间接加载用户 API 时基类为 `undefined`。
- 修复：在列表页测试的模块边界直接 mock `Progress.vue`，使筛选契约测试不加载与目标无关的阈值和用户 API。
- 验证：相同前端聚焦测试复验为 `7 files / 51 passed`。
- 风险：仅调整测试隔离边界，生产组件、阈值请求和页面行为未改变。

### 2026-07-16：NetApp/Isilon 设备错误响应在不同调用阶段被改写或吞掉

- 触发：设备登录、探测、读取、配额写入或读回返回 4xx/5xx；尤其是 Isilon Session 登录/探测和 NetApp 非 JSON 错误。
- 现象：部分路径只返回 `False`，配额接口会重新序列化 JSON，纯文本设备错误被包装成 DiskPulse 消息；状态码和厂商原始消息不完整，问题定位困难。
- 根因：两个厂商客户端分别调用 `raise_for_status()`，缺少统一错误边界；Isilon `_login/_probe` 还捕获所有异常并返回 `False`，配额 service 只透传 JSON。
- 修复：新增共享设备 HTTP 边界，所有 NetApp/Isilon 正式调用在 4xx/5xx 时记录原始状态和消息并保留 `HTTPError.response`；Isilon 登录/探测不再吞错；同步配额接口原样返回设备状态码、响应字节和 `Content-Type`。只有设备未返回 HTTP 响应时才使用 `502`，注销错误记录后不覆盖主业务结果。
- 验证：TDD RED 复现 JSON 字节被改变、纯文本 `409` 被包装及 Isilon Session 错误被吞；GREEN 聚焦用例确认 NetApp `403`、Isilon 登录/探测/缓存 Session 验证错误和配额 JSON/纯文本响应均保持原生响应。相关测试共 `159 passed`，目标模块 `compileall` 通过。
- 风险：后台 Celery 没有浏览器 HTTP 响应可透传，只能在 worker 日志保留厂商状态与消息；部署后需重启 API 和 Celery worker 才会加载统一约束。

### 2026-07-16：Isilon 原生 403 被改写为 502 且控制台重复 TLS warning

- 触发：调整 Isilon 项目组已有的 Directory quota。
- 现象：OneFS 返回 `403 AEC_FORBIDDEN`，接口却统一响应 `502 Storage quota adjustment failed`；集群显式关闭 TLS 校验时，每个请求还会重复输出 `InsecureRequestWarning`。
- 根因：DiskPulse 配置的 Isilon 服务账号缺少写权限 `ISI_PRIV_QUOTA_QUOTAMANAGEMENT`。同时发现原更新请求包含仅创建时需要的 `type/path`，不符合 OneFS 22 quota item PUT schema，但不是本次 403 的原因。
- 修复：外部需为服务账号所属角色的 Quota 父权限和 Quota Management 子权限授予写权限；代码侧让已有 quota 的 PUT 仅发送 `thresholds`，并让配额接口保留设备 JSON HTTP 状态码和响应体。集群明确配置 `tls_verify=false` 时关闭对应 urllib3 warning。
- 验证：使用当前值执行等值 PUT 复现设备原生 `403`；服务和路由测试确认响应保持 `403` 与原始 `errors` 数组，后端聚焦测试 `12 passed`，`compileall` 通过。
- 风险：权限调整前所有 Isilon quota 写入都会继续失败；授权后仍需重试原操作完成设备写入和读回验证。

### 2026-07-16：配额弹窗未复用全局表单样式且软限额单位形似禁用

- 触发：打开项目组或用户目录的配额调整弹窗。
- 现象：弹窗仍使用左侧标签和私有间距；软限额单位显示为灰色文本，视觉上像禁用控件。
- 根因：配额弹窗未挂载全局 `write-form` 类，软限额复用了请求的公共单位值但只渲染为静态文字。
- 修复：复用全局紧凑写入表单结构，硬、软限额均提供联动单位下拉；切换单位时同步换算两个数值。
- 验证：配额与权限聚焦测试 `8 passed`，目标 ESLint、测试构建通过。
- 风险：硬、软限额仍按后端契约共用同一单位，因此任一下拉切换都会同步更新另一个下拉及两个数值。

### 2026-07-16：存储告警已触发但飞书通知全部超时

- 触发：启用 `feishu_notification` 后检查告警列表和最新投递事件。
- 现象：告警事件正常生成，但发送状态均为“发送失败”；最新事件已尝试 4 次，内部错误摘要为 `timed out`，用户未收到飞书提醒。列表内容仍显示 `storage_usage storage trigger/repeat` 和英文告警级别。
- 根因：配置域名解析到 `10.0.42.47`，但当前主机到 TCP `32013` 不可达，调用 `/auth/token` 在约 5 秒后 `ConnectTimeout`；这不是告警规则或 Celery 评估未触发。内容问题来自事件描述和页面级别直接展示内部英文枚举。
- 修复：飞书正文、事件描述、限额口径和告警级别改为中文；用户目录上下文补充项目，告警列表从结构化字段生成中文摘要并兼容历史记录。网络侧仍需恢复 `10.0.42.47:32013` 的服务监听、路由或防火墙放行。
- 验证：后端存储告警聚焦测试 `29 passed`，前端规则与列表契约测试 `8 passed`；DNS、TCP 和认证接口检查均未输出密钥。
- 风险：连接恢复前新通知仍会失败；已进入 `failed` 的历史事件不会自动重放，恢复网络后必须经人工确认再重发，避免重复通知。

### 2026-07-16：超级管理员看不到配额调整入口

- 触发：使用配置中的超级管理员账号打开项目组或用户目录列表。
- 现象：后端允许该账号调用配额接口，但前端未显示“调整配额”按钮。
- 根因：后端 profile 返回角色码 `superadmin`，前端 `hasRole()` 仅识别目标角色和历史全局角色 `*:root`。
- 修复：共享 `hasRole()` 将 `superadmin` 识别为全局角色，两个页面无需分别增加判断。
- 验证：权限与配额弹窗聚焦测试 `7 passed`，目标 ESLint 通过。
- 风险：`superadmin` 将获得前端所有基于 `hasRole()` 的管理入口，与后端超级管理员语义一致；实际写操作仍由后端权限依赖校验。

### 2026-07-16：前端测试误在仓库根目录执行

- 触发：组合复验时在 `D:\dev\DiskPulse` 执行 `npm test -- test/unit/quota-adjustment.test.js`。
- 现象：npm 报 `ENOENT`，找不到仓库根目录下的 `package.json`。
- 根因：本项目的前端 `package.json` 位于 `frontend`，命令未切换工作目录。
- 修复：在 `D:\dev\DiskPulse\frontend` 执行相同测试命令。
- 验证：修正工作目录后配额弹窗测试 `3 passed`。
- 风险：仅影响本地验证命令，不影响实现。

### 2026-07-16：配额弹窗选项属性未通过 Vue 模板格式检查

- 触发：对配额调整相关前端文件执行定向 ESLint。
- 现象：`QuotaAdjustmentDialog.vue` 的 5 个 `ElOption` 报 `vue/max-attributes-per-line`。
- 根因：`label` 与 `value` 写在同一行，不符合仓库多属性组件的换行规则。
- 修复：将 5 个选项的 `label`、`value` 分行排列，不改变字段值或交互。
- 验证：重新执行相同定向 ESLint，结果为 `0 errors`。
- 风险：仅为模板格式问题，不影响 API 和配额行为。

### 2026-07-16：Vitest 聚焦测试路径相对工作目录错误

- 触发：在 `frontend` 工作目录执行 `npm test -- --run frontend/test/unit/quota-adjustment.test.js frontend/test/unit/api/modules.test.js`。
- 现象：Vitest 提示 `No test files found`，两个测试文件均未执行。
- 根因：测试路径仍带仓库根目录的 `frontend/` 前缀，并额外传入了不需要的 `--run` 参数。
- 修复：改用 `npm test -- test/unit/quota-adjustment.test.js test/unit/api/modules.test.js`。
- 验证：修正命令后配额弹窗与 API 聚焦测试 `4 passed`。
- 风险：仅影响本地验证命令，不影响生产代码。

### 2026-07-16：独立告警任务测试数据违反项目组存储目标约束

- 触发：为 `storage_alerts_schedule_task` 增加最新采集批次选择测试。
- 现象：SQLite 报 `CHECK constraint failed: ck_group_monitored_has_storage_target`，测试未执行到缺失实现。
- 根因：测试创建启用监控的项目组时未设置 `volume_id` 或 `qtree_id`。
- 修复：测试项目组补充占位 `volume_id`，再次执行后 RED 仅来自独立 Beat 和样本选择实现缺失。
- 验证：实现后 `backend/test/test_storage_alert_rules.py` 共 `29 passed`。
- 风险：仅影响测试夹具，不涉及生产数据或迁移。

### 2026-07-16：性能多指标图表未通过模板缩进检查

- 触发：执行存储集群详情页和页面测试的定向 ESLint。
- 现象：`StorageClusterDetailPage.vue` 的多指标 `BarStackChart` 区块出现 11 个 `vue/html-indent` error；生产构建仍可完成。
- 根因：在 `performance-charts` 容器内新增循环图表时，子组件缩进层级少了两个空格。
- 修复：按现有 Vue 模板规则对齐整个循环图表区块，不改页面行为。
- 验证：重新执行定向 ESLint，要求生产页面 `0 errors`；测试文件只保留既有 `vue/one-component-per-file` warning。
- 风险：仅为模板格式问题，不影响性能指标查询与图表数据。

### 2026-07-16：存储告警 Alembic 检查使用了错误配置路径

- 触发：在 `backend` 执行 `python -m alembic -c migrate\alembic.ini heads` 或 `history`。
- 现象：Alembic 报 `No 'script_location' key found in configuration`，未读取项目实际配置。
- 根因：仓库的 Alembic 配置入口由 `backend` 当前目录和项目默认配置解析，不应把版本目录中的路径当成 ini 文件传给 `-c`。
- 修复：在 `backend` 目录执行 `D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic heads` 和 `... -m alembic history`。
- 验证：命令返回唯一 head `000000000006`，history 从 `000000000001` 至 `000000000006` 连续。
- 风险：从错误目录或继续传入 `migrate\alembic.ini` 会复现；部署脚本应固定工作目录。

### 2026-07-16：Worktree 缺少忽略配置导致 Celery 静态导入失败

- 触发：在独立 Worktree 的 `backend` 直接导入 `celery_worker` 检查任务注册和 Beat 配置。
- 现象：首次报 `FileNotFoundError: Configuration file not found: ...\backend\config.yml`；把 `base_config.path` 直接赋为字符串后又报 `AttributeError: 'str' object has no attribute 'read_text'`。
- 根因：包含环境配置的 `backend/config.yml` 被 Git 忽略，Worktree 不会自动带入；`base_config.path` 的类型是 `pathlib.Path`。
- 修复：不复制或提交配置，验证命令在导入前只读注入 `Path(r'D:\dev\DiskPulse\backend\config.yml')`，复用主工作区现有本地配置。
- 验证：静态导入确认 `evaluate_storage_alerts_task=True`、`deliver_storage_alert_task=True`，且 Beat 中 `retry_storage_alerts_task=True`。
- 风险：该检查只证明任务注册和调度表加载，不代表真实 Redis broker、worker 或 Beat 能消费任务；配置输出还会显示现有数据库连接摘要，交付日志不得包含密钥。

### 2026-07-16：存储告警迁移离线 SQL 的规则 JSON 被误解析为绑定参数

- 触发：为 `000000000006_storage_alert_rules` 生成 PostgreSQL/MySQL/SQLite 离线 SQL，并检查默认规则 JSON。
- 现象：JSON 中冒号后的内容被 SQLAlchemy `text()` 识别为绑定参数，离线 SQL 出现缺失或损坏的阈值/频次值。
- 根因：Alembic 离线模式仍会解析文本 SQL 的冒号，直接内联 JSON 未转义。
- 修复：离线 JSON 中的冒号按 Alembic 文本绑定规则转义；SQLite 离线模式使用显式方言分支生成可执行的 upgrade/downgrade DDL。
- 验证：自动化测试逐项检查默认值 `80/24/90/6/95/1`；SQLite 离线 SQL 已实际执行升降级，PostgreSQL/MySQL 离线 SQL 生成通过。
- 风险：PostgreSQL/MySQL 本轮只生成离线 SQL，未连接真实数据库执行在线迁移。

### 2026-07-16：最终全局覆盖率未达到存储告警计划的 90% 目标

- 触发：执行后端 `coverage run -m pytest backend\test`/`coverage report` 和前端 `npm run test:coverage`。
- 现象：后端全局为 `84%`；前端 Statements/Lines 为 `92.62%`，Branches 为 `81.96%`，Functions 为 `70.29%`，未满足计划中的四项 90%。
- 根因：仓库现有门禁为后端 80%，前端 Vitest 也未对四项统一执行 90% 门禁；大量既有分支和函数不在本功能测试范围，后端标准配置还排除了 Celery 任务和迁移。
- 处理：不为抬高数字扩展到无关模块；补充存储规则、状态机、飞书、outbox、迁移与前端入口的聚焦测试。后端规则 schema/规则服务/飞书服务选择性统计为 `92%`。
- 验证：后端 `312 passed` 并通过仓库 80% 门禁；前端 40 个测试文件、`205 passed`，现有 coverage 命令成功退出。
- 风险：用户计划中的全局 90% 验收条件仍未满足；Celery 评估/outbox 的标准 coverage 未计入，需后续专项治理而非把当前结果描述为达标。

### 2026-07-16：存储告警实施基线存在三个既有回归失败

- 触发：在独立 Worktree 开始功能实施前执行 `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend\test -q` 和 `npm test`。
- 现象：后端为 `283 passed, 1 failed`，`test_storage_health_migration_backfills_attributable_alerts_on_sqlite` 实际得到 `(None, "diskpulse", "info")`；前端为 `194 passed, 2 failed`，`storage-resource-terminology.test.js` 找不到 `label="存储目标"` 和 `label="访问协议"`。
- 根因：后端测试按迁移文件名取最后一个迁移，新增 `000000000005` 后不再执行待测的 `000000000004` 回填；前端两个术语断言已与当前页面删除的列和详情摘要不一致。三项均可在功能代码改动前稳定复现。
- 处理：按存储告警实施计划的基线门禁暂停；用户确认继续后，后端测试改为按明确 revision 定位待测迁移，前端术语测试同步当前页面契约，修复提交为 `d16e8f1`。
- 验证：修复后后端全量 `284 passed`；前端全量 39 个测试文件、`196 passed`。`npm ci` 成功，Alembic `heads/history` 成功且唯一 head 为 `000000000005`，CodeGraph 索引为最新。
- 风险：本条只确认既有基线恢复；存储告警功能后续 RED/GREEN 与最终验证结果见 `docs/features/storage-alerts/design.md` 和 `docs/tracking/current-release.md`。

### 2026-07-16：Worktree 前置检查对空 Git 输出调用 Trim 失败

- 触发：首次检查主仓库路径时，对 `git rev-parse --show-superproject-working-tree` 的空输出直接调用 `.Trim()`。
- 现象：PowerShell 报空值不能调用方法，Worktree 创建命令尚未执行。
- 根因：普通非子模块仓库会返回空输出，检查脚本未先把输出规整为字符串。
- 修复：改用 `@(git rev-parse --show-superproject-working-tree) -join ''` 后再判断，随后成功创建 Worktree；未产生半成品分支或目录。
- 风险：仅影响一次性初始化检查，不影响仓库和功能代码。

### 2026-07-16：Isilon 性能错误读取节点磁盘延迟，无法按 Directory Quota 展示

- 触发：性能分析只显示对象 `1`、类型 `node` 和 `0ms`，需求是按 Isilon 每个逻辑存储空间查看延迟；采集账号已经增加 `ISI_PRIV_PERFORMANCE`。
- 根因：客户端从 `statistics/keys` 选择第一个 node latency 键，没有读取 OneFS Partitioned Performance 的 dataset/workload。真机实际存在 ID `3` 的 `path` dataset，`cluster.performance.dataset.3` 返回 workload 延迟，但响应使用内部 workload ID，必须再用 performance workloads 接口映射到路径。
- 修复：改为读取 `path` dataset、已固定 workload 和 dataset statkey；按 `latency_read/write/other` 的 `sum/count` 计算平均微秒并转为毫秒，保存对象类型为 `volume`、对象名称为 Directory Quota 完整路径；前端性能查询固定过滤 `volume`，不再混入历史 node 指标。
- 验证：RED 为 `3 failed`；GREEN 存储健康后端 `93 passed, 1 deselected`。通过现有 Session 客户端连接 OneFS 9.11.0.5，解析到 8 个已固定 workload；其中 7 个匹配 PostgreSQL 的 67 个 Directory Quota，正式采集写入并回读 7 个路径，额外父路径被过滤。其余 60 个路径需要 root 在 OneFS 补充 workload，权限本身不会自动产生逐路径数据。
- 数据清理边界：首次验证曾写入一条 `/ifs/data/ICO` 父路径样本；当前 QuestDB 对该表执行行级 `DELETE` 返回 `unexpected token [FROM]`，因此没有强行重建分区。查询服务现按 PostgreSQL Volume 路径二次校验，该历史样本不会显示，并按表的 180 天 TTL 自然过期。

### 2026-07-16：后端环境未安装 pytest-cov 插件

- 触发：尝试用 `pytest --cov` 统计系统事件改动模块覆盖率。
- 现象：pytest 返回 `unrecognized arguments: --cov ... --cov-report=term`。
- 根因：当前虚拟环境安装了 `coverage.py`，但没有注册 `pytest-cov` 插件。
- 修复：不新增依赖，改用 `coverage run -m pytest` 和 `coverage report` 执行同一聚焦测试。
- 验证：替代命令成功执行 `90 passed, 1 deselected` 并生成模块覆盖率报告。
- 风险：后续继续直接使用 `pytest --cov` 仍会失败，应沿用项目现有 coverage 入口或安装插件后再使用。

### 2026-07-16：系统事件日志等级选项未通过模板属性换行规则

- 触发：执行存储集群详情页和聚焦测试的定向 ESLint。
- 现象：四个 `ElOption` 报 `vue/max-attributes-per-line`，测试辅助组件另有既有 `vue/one-component-per-file` warning。
- 根因：新增日志等级选项把 `label` 和 `value` 写在同一行，不符合当前 Vue 模板格式规则。
- 修复：将四个选项的属性拆行；测试文件的既有多组件 warning 不影响退出码，本轮不拆分测试桩。
- 验证：重新执行定向 ESLint，要求 `0 errors`。
- 风险：仅为模板格式问题，不影响接口、筛选或分页行为。

### 2026-07-16：存储健康迁移回填测试错误选择最后一个迁移

- 触发：执行 `uv run pytest test/test_storage_health_analytics.py -q`。
- 现象：`test_storage_health_migration_backfills_attributable_alerts_on_sqlite` 期望 `(1, "diskpulse", "critical")`，实际得到 `(None, "diskpulse", "info")`；其余本轮 RED 失败均为新功能预期失败。
- 根因：测试按文件名加载全部迁移后使用 `migrations[-1]` 执行待测回填；新增 `000000000005_storage_cluster_session_cache.py` 后，最后一个迁移不再是包含回填逻辑的 `000000000004_storage_health.py`。
- 修复：本轮不修改与系统事件搜索无关的迁移测试；功能验证改为精确执行系统事件 CRUD/API 用例，并保留该问题等待单独修复测试定位方式。
- 验证：系统事件后端聚焦用例 `4 passed`，前端页面聚焦用例 `10 passed`。
- 风险：全量存储健康测试仍会保持一个非功能断言失败；真实迁移链本轮未改动，不能由该失败推断生产迁移本身异常。

### 2026-07-16：Isilon 性能和系统事件接口有数据但解析后全部丢失

- 触发：本地服务账号权限恢复后，存储集群详情的性能分析和故障分析仍为空；使用现有 `StoragePulseMonitor` 会话流程读取真实 OneFS 响应并对比解析结果。
- 现象：statistics 返回 `node.disk.access.latency.0`，单位为 `seconds`、值为 `0.0`，解析结果为 `0` 条；event group/list 分别返回 `2888`/`218` 条，标准化结果同样为 `0` 条。
- 根因：延迟解析器只接受微秒和毫秒，未接受 OneFS 实际返回的秒；性能采集未读取 `time`。事件解析器未识别 event group 的 `last_event`、`time_noticed`、`causes`，也未展开 event list 外层记录中的 `events[]`；整数 Unix 时间戳还会被错误替换为采集当前时间。
- 修复：秒统一乘 `1000` 转为毫秒并保留合法零值；统一支持整数 Unix 时间戳和 statistics `time`；展开 OneFS 嵌套事件，使用事件组最近时间、原因代码/消息及设备编号生成标准事件记录。
- 验证：RED 为 `4 failed, 9 passed`；GREEN 相关解析测试 `24 passed`，目标任务模块分支覆盖率 `83%`。真实 OneFS 无写入复验得到性能 `1/1` 条可解析、事件 `3888` 条可解析，其中最近 8 小时 `94` 条、最近 24 小时 `331` 条。正式采集写入 QuestDB 性能 `1` 条、PostgreSQL 事件 `331` 条；重启 worker/Beat 后再次异步投递性能任务，QuestDB 记录增至 `2` 条，最新时间为 `2026-07-16 10:39:54`。
- 风险：Windows `solo` worker 执行 OneFS 长分页请求时不会及时响应 Celery inspect 控制命令，不能单凭 inspect 超时判断 worker 离线；应同时检查进程、任务结果或目标库最新时间戳。

### 2026-07-15：覆盖率插桩触发三个前端测试超时

- 触发：执行 `npm run test:coverage` 验证全站筛选栏改造。
- 现象：普通全量测试仅保留两条已记录的术语断言失败；开启覆盖率后另有三个既有重型组件用例超过 `15s`。
- 根因：Vue SFC 覆盖率插桩增加编译和挂载开销，现有全局 `15s` 超时不足，并非用例断言或业务行为新增失败。
- 修复：将 Vitest `testTimeout` 调整为 `30s`，不修改覆盖率阈值和测试断言。
- 验证：默认覆盖率命令恢复为仅两条已记录失败；排除该已知失败文件后 `188 passed`，总体覆盖率为 Statements `92.58%`、Branches `81.80%`、Functions `72.04%`、Lines `92.58%`。
- 风险：仅放宽单用例执行时限；覆盖率门禁仍由现有配置控制。

### 2026-07-15：登录页模板缩进未通过 ESLint
- 触发：执行 `.\node_modules\.bin\eslint.cmd src/pages/auth/LoginPage.vue` 验证登录页改版。
- 现象：ESLint 报告 `62` 条 `vue/html-indent`，均为新增表单层级少缩进两个空格。
- 根因：登录表单移入右侧面板内容容器后，内部 `ElForm` 及其子节点仍保留原有缩进。
- 修复：对 `LoginPage.vue` 执行项目 ESLint 单文件自动修复，仅调整模板缩进。
- 验证：同一目标 ESLint 重跑无错误；聚焦测试 `2 passed`，生产构建通过。
- 风险：仅为模板格式问题；构建仍保留与本轮无关的既有大 chunk warning。

### 2026-07-15：窄屏应用壳固定侧栏产生横向溢出
- 触发：在浏览器中将存储集群详情页依次调整到 `320px`、`375px`、`414px`、`768px` 和 `1280px` 宽度。
- 现象：日期范围和导出动作在各宽度均未重叠；`320/375px` 下页面整体仍出现横向溢出，`414px` 及以上无该问题。
- 根因：既有应用壳保留固定宽度侧栏和对应的主内容偏移，窄于两者最小总宽度时超出视口；不是本轮查询栏动作插槽造成。
- 修复：本轮保持任务最小边界，未修改全局导航；详情页查询栏允许动作换行并限制日期控件宽度。
- 验证：`1280×720` 下日期控件右边界为 `562px`、导出按钮左边界为 `979px`；`414×896` 下无横向溢出。
- 风险：如产品需要支持手机宽度，应单独将全局侧栏改为抽屉或折叠菜单，并对所有管理页执行响应式回归。

### 2026-07-15：存储健康性能与 Isilon 系统事件始终未落库
- 触发：查询 PostgreSQL/QuestDB 最新记录，并分别直连 NetApp 和 Isilon 执行只读性能、事件接口探测。
- 现象：两套集群的 `storage_performance_metrics` 均为 `0`；Isilon 厂商事件总数为 `0`。NetApp Volume 请求返回 `400/262197`；Isilon `platform` 登录返回 `403`，事件和 statistics 接口返回 `401`；`celery inspect registered` 当前没有节点响应。
- 根因：NetApp 客户端错误请求不存在的复数 `metrics` 并按同名字段解析，真机只支持单数 `metric`。Isilon 当前账号没有成功取得 OneFS `platform` 服务会话，因此事件和性能接口均未授权；worker 控制面当前不可达，部署进程状态仍需检查。
- 修复：NetApp 请求和采集解析统一改为 `metric`；Isilon 不在代码中伪造回退，需在 OneFS 恢复账号的 Platform API 登录及 event/statistics 只读权限，并重启 Celery worker。
- 验证：真机对比请求确认 `metrics` 返回 `400`、`metric` 返回 `200` 且包含延迟结构；聚焦后端测试 `82 passed`。为避免改写生产数据，本轮未手工调用落库函数。
- 风险：Isilon 权限和 worker 状态属于外部阻塞；在权限恢复、worker 重启并观察到最新事件/性能时间戳前，页面空态不能解释为设备正常。

### 2026-07-15：QueryForm 新动作插槽烟测被浅挂载桩吞掉
- 触发：为查询栏新增 `actions` 插槽后运行三个前端聚焦测试文件。
- 现象：页面和路由测试通过，组件烟测仍报 `expected 'Filters' to contain 'Actions'`。
- 根因：`shallowMount` 自动替换的 `GridContainer` 桩只保留默认槽，没有透传生产组件使用的 `tail` 作用域，导致测试观察不到已渲染的动作槽。
- 修复：在该烟测中使用只透传默认槽和 `tail` 槽的最小 `GridContainer` 桩。
- 验证：同一前端聚焦命令重跑为 `11 passed`。
- 风险：仅影响测试装配，不影响生产页面。

### 2026-07-15：前端仍显示用户但业务接口持续返回 401
- 触发：页面保留已加载的用户信息时继续访问存储集群、项目、项目组等业务接口。
- 现象：请求已到达后端，但全部返回 `401 Unauthorized`；这表示后端在线并拒绝当前 token，不是后端进程掉线。
- 根因：现有 JWT 配置只有 60 分钟有效期，前端用户显示与 token 有效性不同步；撤销状态还仅保存在后端进程内存。未取得截图中的原始 token，无法进一步区分它是已过期还是签名不匹配。
- 修复：登录后将 token 摘要写入 Redis 会话白名单，JWT 和 Redis TTL 默认统一为 7 天；鉴权校验白名单，登出删除对应 key，Redis 故障时返回 `503`。
- 验证：Redis DB 7 `PING=True`；契约测试从 `4 failed, 6 passed` 转为 `10 passed`。
- 风险：部署后旧 token 没有 Redis 记录，用户必须重新登录一次；本轮未修改前端收到 `401` 后自动清理用户显示的行为。

### 2026-07-15：认证覆盖率命令误用未安装的 pytest-cov
- 触发：执行 `pytest ... --cov=utils.security --cov-fail-under=80` 验证认证安全覆盖率。
- 现象：pytest 报 `unrecognized arguments: --cov`，目标测试未执行；改用全局 coverage 报告时又被仓库整体 `66%` 覆盖率门槛拒绝。
- 根因：当前虚拟环境安装了 `coverage.py`，但没有安装提供 `--cov` 参数的 `pytest-cov`；全局报告还包含大量与本次认证无关的模块。
- 修复：不新增依赖，改用 `python -m coverage run` 执行目标测试，再仅对 `backend/utils/security.py` 生成报告。
- 验证：认证/安全/核心接口组合测试 `53 passed`，目标模块分支覆盖率 `84%`，后端全量 `262 passed`。
- 风险：本轮只验证目标认证模块达到覆盖率要求，仓库整体 coverage 仍为现有 `66%`，未把它描述为全局门禁通过。

### 2026-07-15：项目组详情只读字段导致监控配置保存失败
- 触发：在“修改项目组监控配置”弹窗提交由详情接口加载的项目组。
- 现象：页面先提示“网络错误”，随后提示“保存项目组失败，请稍后重试”；PUT 请求实际返回 `422`。
- 根因：编辑表单把详情响应中的只读 `qtree`、`in_charge_user` 原样放入 payload，后端 `GroupBindingUpdate` 配置 `extra="forbid"` 后拒绝额外字段。
- 修复：提交前剔除 `qtree`、`in_charge_user`，保留现有可写字段和存储目标切换逻辑。
- 验证：新增回归用例先稳定复现只读字段泄漏，再以同一聚焦测试验证 `12 passed`。
- 风险：尚未连接运行中的前后端执行浏览器保存冒烟；公共请求层对其他未专门处理的 HTTP 状态仍可能显示通用提示。

### 2026-07-15：Claude 流式工具参数拼接出无效 JSON
- 触发：模拟 Claude `content_block_start` 返回空 `input={}`，随后通过 `input_json_delta` 流式返回工具参数。
- 现象：客户端把起始空对象序列化为 `"{}"`，再拼接参数增量后得到 `"{}{\"id\":3}"`，最终报“AI 工具参数不是有效 JSON”。
- 根因：流式解析误把起始块中的空输入当成完整参数，而 Claude 后续仍会发送参数 JSON 增量。
- 修复：起始输入为空时将参数缓冲区初始化为空字符串；只有起始块包含非空输入时才序列化。
- 验证：OpenAI/Claude 流式协议聚焦测试通过，并确认 Claude 工具参数解析为 `{\"id\": 3}`。
- 风险：当前为协议级模拟验证，尚未使用真实 Claude API Key 执行工具调用冒烟。

### 2026-07-14：登录认证慢且 profile 和当前用户被重复查询
- 触发：使用真实 LDAP 配置登录后，观察 `/users/login`、重复的 `/users/current/profile` 及后续业务接口响应。
- 现象：LDAP 精确用户查询三次为 `1738.9/1548.0/1601.1 ms`，均为 `matches=1`；独立进程数据库查询 cold 为 `777.4 ms`、warm 为 `41.9–46.1 ms`。登录跳转还会请求两次 profile，同一后端请求内重复读取当前用户。
- 根因：前端登录页取得 profile 后，路由守卫没有复用 store；后端认证依赖与 `CurrentUserDep` 没有共享当前请求的用户；ldap3 `Server` 使用 `get_info=ALL`，精确用户查询前额外读取无关目录 schema/info。
- 修复：路由守卫复用登录页已写入的 profile；后端通过当前 `Request` 复用已验证用户，但每个新请求仍独立校验 JWT；LDAP `Server` 改用 `get_info=NONE`，保留 STARTTLS、CA 和 timeout。
- 验证：后端 RED `2 failed, 14 passed`、GREEN `43 passed`；前端 RED `1` 个预期失败且刷新用例通过、GREEN `4 passed`。优化后 LDAP 精确用户查询为 `651.4/353.6/366.4 ms`，均为 `matches=1`。
- 风险：尚未使用真实密码测量包含用户 bind 的完整登录耗时，浏览器真实登录冒烟待最终验证；数据库 cold 连接耗时仍存在。

### 2026-07-14：Isilon PAPI 登录间歇性拒绝且客户端未释放会话
- 触发：使用应用已配置的 Isilon 账号执行 OneFS 9.11 只读验收。
- 现象：初次检查时应用配置入口的 `POST /session/1/session` 间歇性拒绝 `platform` 服务；节点管理入口曾成功登录，后续新会话也出现拒绝。
- 根因：账号已启用、未锁定、密码未过期，且角色包含 Platform API、Cluster、SmartPools 和 Quota 权限，原“账号缺少 PAPI 权限”和“配置入口不支持 PAPI”判断均被后续真机结果排除。代码审查确认客户端只关闭本地连接、未删除服务端会话，会增加并发会话耗尽风险；未检查设备审计日志，因此早期 `403` 的精确触发条件仍未完全确认。
- 修复：未缓存会话关闭时调用 `DELETE /session/1/session`；注销请求失败只记录异常类型，并保证本地 HTTP session 关闭。
- 验证：使用部署数据库中的原 Isilon 配置成功登录 OneFS `9.11.0.5`，读取 `2264` 条 Quota：`40` 条 default-user、`64` 条 directory、`2160` 条 user。会话关闭聚焦测试 `3 passed`，资源映射测试文件 `19 passed`。
- 风险：真机 Storage Pool 条目未返回可选的 `usage` 对象，当前容量池采集仍会因缺少总容量和已用容量而回滚；容量字段来源和单位确认前不得认定真机采集完成，也不得猜测性填充容量。

### 2026-07-14：存储一览加载态引用了不存在的变量
- 触发：为“存储一览”新增集群切换页面测试并挂载 `DashboardPage.vue`。
- 现象：Vue 提示 `Property "querying" was accessed during render but is not defined on instance`，页面请求期间不会进入加载态。
- 根因：`useQuery` 将状态解构为 `storageSummaryQuerying`，模板仍引用旧变量名 `querying`。
- 修复：模板统一改用 `storageSummaryQuerying`。
- 验证：页面聚焦 Vitest 通过，`1 passed`；`npm run build:prod` 通过。
- 风险：仅修正存储一览加载态变量引用，未修改其他图表行为。

### 2026-07-14：设置页旧测试仍操作已隐藏的备份控件
- 触发：执行离职备份前端隐藏的五文件聚焦回归测试。
- 现象：`settings-config.test.js` 仍读取两个 `ElInputNumber` 和一个 `ElSwitch`，隐藏备份页签后数组为空并触发 `Cannot read properties of undefined (reading 'vm')`。
- 根因：旧用例把离职备份控件视为系统设置页的固定可见输入，没有覆盖“隐藏展示但保留配置值”的新契约。
- 修复：移除对隐藏控件的交互，继续断言保存其他可见设置时完整配置对象提交，已有备份字段和值保持不变。
- 验证：同一聚焦命令通过，`5` 个文件、`19` 个测试；`npm run lint` 和 `npm run build:prod` 通过。
- 风险：仅调整前端测试假设；未改变后端配置或备份执行逻辑。

### 2026-07-14：Volume 页面测试桩未隔离作用域插槽和 Select 依赖
- 触发：执行 `.\node_modules\.bin\vitest.cmd run test/unit/pages/volume-list-page.test.js --coverage.enabled=false`。
- 现象：首次挂载因 `ElTableColumn` 测试桩未提供 `row` 报错；页面引入 `StorageClusterSelect` 后又在加载真实依赖链时触发 `Class extends value undefined`。
- 根因：页面级测试错误地渲染了表格列作用域插槽，且只在挂载配置中 stub 组件，没有在模块加载阶段 mock 新增的 Select import。
- 修复：表格列桩不再渲染作用域插槽，并在导入页面前 mock `StorageClusterSelect.vue`，使测试只覆盖 Volume 页面的筛选接线。
- 验证：同一聚焦测试命令通过，`1 passed`；`npm run build:prod` 通过。
- 风险：仅影响新增测试装配，不影响生产页面；真实浏览器交互尚未执行。

### 2026-07-14：QuestDB migration 聚焦覆盖率被全局排除规则过滤
- 触发：使用仓库默认 `.coveragerc` 对 `backend/questdb/migrate.py` 运行聚焦覆盖率。
- 现象：测试通过，但 coverage 输出 `No data to report`，并提示命令行 `--include` 因配置中的 `source` 被忽略。
- 根因：核心后端覆盖率门禁历史上整体排除了 `backend/questdb/*`，聚焦命令仍继承该配置，无法单独计量新迁移执行器。
- 修复：使用 `.tmp` 下任务专用 coverage 配置运行聚焦计量，验证后删除临时文件；不改变既有核心后端门禁范围。
- 验证：QuestDB migration 测试 `12 passed`，`backend/questdb/migrate.py` statements/branches 综合覆盖率 `98%`。
- 风险：全局核心后端覆盖率报告仍不包含 QuestDB；后续若将整个 QuestDB 目录纳入全局门禁，应单独评估既有数据库连接与设备集成代码的测试范围。

### 2026-07-14：Alembic 默认版本表无法用于 QuestDB
- 触发：使用 `questdb-connect` 1.1.0 方言离线编译 Alembic 默认 `alembic_version` 表。
- 现象：`VARCHAR(32) PRIMARY KEY` 版本列触发 `sqlalchemy.exc.ArgumentError: Column type is not a valid QuestDB type`。
- 根因：QuestDB 方言只接受自身类型；QuestDB 也不支持 PostgreSQL 式 `PRIMARY KEY/NOT NULL` 约束，PGWire 不支持 Alembic 降级到 base 所需的 `DELETE`。
- 修复：复用现有 SQLAlchemy 连接，新增前向 QuestDB migration 执行器、静态 SQL revision 和 `diskpulse_schema_migrations` 账本；启动时不再调用无版本记录的 `QuestDBBase.metadata.create_all()`。
- 验证：QuestDB migration 聚焦测试 `12 passed`、迁移执行器覆盖率 `98%`；当前配置指向的 QuestDB 为 revision `000000000001`，包含 `7` 张趋势表和版本账本，重复升级返回 `up to date`。
- 风险：QuestDB DDL 不具备 PostgreSQL 式事务回滚；revision 必须保持前向、幂等和不可修改，破坏性回退需备份后使用修复 revision 或重建实例。

### 2026-07-14：MySQL 全 metadata 编译因无长度 String/VARCHAR 失败
- 触发：迁移独立审计对 `Base.metadata` 的全部 `14` 张表执行 MySQL `CreateTable` 编译。
- 现象：`14` 张表中 `13` 张触发 SQLAlchemy `CompileError`，错误均指向 MySQL `VARCHAR` 必须声明长度；只有不包含相关无长度字符串列的表可编译。
- 根因：现有 ORM 广泛使用未指定长度的 `String`，SQLite 和 PostgreSQL 接受该定义，MySQL 方言不接受无长度 `VARCHAR`。
- 处理：本次项目存储环境 baseline 明确只支持 SQLite/PostgreSQL；MySQL 明确不支持并列为待专项整改，不为未纳入部署范围的 MySQL 批量修改既有 ORM。文档不得把三方言编译门禁描述为通过。
- 验证：SQLite 空库 upgrade/downgrade 与 metadata 对比通过，PostgreSQL offline upgrade/downgrade DDL 通过；MySQL 全 metadata 编译可稳定复现上述 `13/14` 失败。
- 风险：当前实现未满足 `backend-development-standard.md` 的默认 SQLite/PostgreSQL/MySQL 三方言编译门禁；若将 MySQL 纳入部署范围，必须先为相关 `String/VARCHAR` 补齐长度并重新验证完整 baseline。

### 2026-07-14：项目存储环境文档仍描述已删除的兼容迁移
- 触发：完成严格 Group 模型和单一 Alembic baseline 后，审查 `docs/features/project-storage-environment/design.md` 与交付记录。
- 现象：文档仍把回填脚本、兼容双写、M3 收紧和旧 revision 链描述为当前方案，与初始开发阶段的实际代码不一致。
- 根因：需求从增量迁移调整为绿地空库 baseline 后，先前设计和历史交付陈述未同步收敛。
- 修复：统一改为 root/head `000000000001`、空库重建、无回填和无兼容窗口；明确 QuestDB 不属于 Alembic。
- 验证：全 `docs/` 搜索旧 revision、回填脚本和 M3 当前态陈述，并执行 `git diff --check`。
- 风险：已使用删除前 revision 的开发数据库不能原地升级，必须确认数据可丢弃后重建空库。

### 2026-07-13：跨方言删除列测试导入错误
- 触发：执行 `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_backend_schema_contract.py -q`。
- 现象：测试收集时报错 `ImportError: cannot import name 'DropColumn' from 'sqlalchemy.schema'`。
- 根因：SQLAlchemy 2.0.48 不公开 `sqlalchemy.schema.DropColumn`；删除列 DDL 元素由 Alembic 提供。
- 修复：改从 `alembic.ddl.base` 导入 `DropColumn`，并按其表名和列参数签名构造 DDL。
- 验证：重跑同一聚焦测试命令通过，`6` 个测试。
- 风险：该错误仅影响新增迁移测试收集，不影响生产迁移实现。

### 2026-07-13：group_alarm_daily 重要告警计数器未初始化
- 触发：执行 `backend/test/test_project_environment_usage_alert_backup.py` 中真实 Group 告警邮件与持久化回归。
- 现象：`group_alarm_daily()` 在重要级别分支使用未定义的 `important_in_this_email`，触发 `NameError`；收件人循环的宽泛异常处理只记录 `Error in send mail:name 'important_in_this_email' is not defined`，导致该封邮件错误被吞并跳过后续结果收集。
- 根因：重构每封邮件的紧急、警告和重要计数时，只初始化了前两个计数器。
- 修复：在每个收件人处理开始时把 `important_in_this_email` 初始化为 `0`，与另外两个邮件级计数器保持同一作用域。
- 验证：`& 'D:\dev\DiskPulse\.venv\Scripts\python.exe' -m pytest backend\test\test_project_environment_usage_alert_backup.py -q` 通过，`32` 个测试。
- 风险：未连接真实 SMTP 执行邮件发送；当前仅验证模板数据、发送调用和告警持久化路径。

### 2026-07-13：Pydantic 2 StorageUsage 调用不存在的 default_dict
- 触发：修复邮件计数器后，继续执行真实 `storageUsageSchema.StorageUsage` 的 Group TOP20 邮件序列化回归。
- 现象：Pydantic 2 模型不存在 `default_dict()`，调用时触发 `AttributeError`，Group 告警邮件无法完成组装。
- 根因：旧代码把 Pydantic 序列化方法误写为不存在的 `default_dict()`，Mock 没有暴露真实模型契约。
- 修复：对 `StorageUsage.model_validate(...)` 的结果调用 Pydantic 2 `model_dump()`。
- 验证：`& 'D:\dev\DiskPulse\.venv\Scripts\python.exe' -m pytest backend\test\test_project_environment_usage_alert_backup.py -q` 通过，`32` 个测试。
- 风险：未连接真实 SMTP 或生产 PostgreSQL；当前验证使用真实 Pydantic 2 schema 和测试数据库 ORM 对象。

### 2026-07-13：LDAP 登录成功后 profile 请求返回 401
- 触发：LDAP 登录接口返回 `200` 后，前端立即请求 `/storage-pulse/api/users/current/profile`。
- 现象：登录成功，但 profile 请求返回 `401 Unauthorized`。
- 根因：前端请求拦截器把 JWT 直接写入 `Authorization`，后端只接受 `Bearer <token>`。
- 修复：有 token 时统一添加 `Bearer` scheme。
- 验证：`npx vitest run test/unit/api/support.test.js test/unit/auth-login.test.js` 通过，3 个测试。
- 风险：未执行真实浏览器自动化；开发环境需刷新页面后重新登录。

### 2026-07-13：LDAP 用户 bind 失败无服务端原因日志
- 触发：使用可被域控查询到的用户调用 `POST /storage-pulse/api/users/login`。
- 现象：接口返回 `401 Unauthorized`，控制台仅显示访问日志，无法区分 STARTTLS、凭据拒绝或运行时异常；首次补充的 `app:auth` warning 在 Uvicorn 控制台仍不可见。
- 根因：`_bind_ldap_user()` 对 bind 失败直接返回 `False` 并吞掉异常，且首次补充日志使用了未接入 Uvicorn handler 的 logger。
- 修复：在共享用户 bind 函数记录安全的失败阶段、LDAP result code/description 或异常类型，目录查询无匹配时记录独立 warning，并统一通过 `uvicorn.error` 输出；不记录用户名、DN 和密码。
- 验证：真实服务账号查询得到一个用户结果；`..\.venv\Scripts\python.exe -m pytest test\test_auth_ldap.py -q` 通过，7 个测试。
- 风险：未获取用户密码，无法替用户执行真实用户 bind；下一次登录日志可进一步确认是否为 `invalidCredentials`。

### 2026-07-13：YAML 配置测试漏建配置实例
- 触发：执行 `.\.venv\Scripts\python.exe -m pytest backend\test\test_app_config.py -q`。
- 现象：`test_resolves_secret_file_relative_to_yaml` 报错 `NameError: name 'config' is not defined`。
- 根因：新增相对路径测试创建了配置文件，但漏写 `Config(config_path)` 实例化步骤。
- 修复：在断言前显式创建 `Config` 实例。
- 验证：同一命令重跑通过，7 个测试全部成功。
- 风险：无生产代码影响；该失败只存在于新增测试装配。

### 2026-06-30：后端安全审查发现敏感信息和命令拼接风险
- 触发：审查当前后端代码并新增 `backend/test/test_security_regressions.py`。
- 现象：`/config/storage` 和存储集群响应包含密码字段；通用异常响应回显内部异常文本；JWT 解码不校验 header 算法；NetApp/Isilon 默认关闭 TLS 校验；远程文件管理直接拼接 `sudo mkdir/chmod/chown/mv/rsync/rm -rf` 命令参数。
- 根因：内部 schema 与 public API schema 混用，异常处理把调试信息返回给客户端，外部客户端和远程任务沿用开发便利默认值，动态参数缺少统一白名单和 shell 参数引用。
- 修复：新增 public response schema，收敛异常响应，校验 JWT header，开启 TLS 默认校验，远程命令参数使用 `shlex.quote`，动态排序/指标/树图字段使用白名单，后台任务内创建独立 DB session。
- 验证：`.\.venv\Scripts\python.exe -m unittest backend.test.test_security_regressions`、`.\.venv\Scripts\python.exe -m unittest discover -s backend\test -p "test_*.py"`、`.\.venv\Scripts\python.exe -m compileall -q backend` 均通过。
- 风险：真实外部设备和 LDAP 环境未端到端验证；自签名证书环境需要配置 CA 或显式受控降级。

### 2026-06-30：覆盖率门禁缺少本地工具
- 触发：执行 `.\.venv\Scripts\python.exe -m coverage --version` 和后续覆盖率门禁。
- 现象：本地虚拟环境提示 `No module named coverage`。
- 根因：后端依赖文件未声明 `coverage`，本地 `.venv` 也未安装该包。
- 修复：在 `backend/requirements.txt` 补充 `coverage==7.13.0`，并执行 `.\.venv\Scripts\python.exe -m pip install coverage==7.13.0`。
- 验证：`.\.venv\Scripts\python.exe -m coverage run -m unittest discover -s backend\test -p "test_*.py"; .\.venv\Scripts\python.exe -m coverage report` 通过，核心后端覆盖率 `73%`。
- 风险：新环境需要重新安装依赖后才能执行覆盖率门禁。

### 2026-06-30：导出接口响应类型与文件类型不一致
- 触发：新增核心 API 测试覆盖 `storage-usages/export/` 和 `large-files/export/`。
- 现象：存储使用 PDF 导出返回 Excel MIME，Excel 导出返回 `application/pdf`；大文件 `.xlsx` 导出也返回 `application/pdf`。
- 根因：路由中 `media_type` 常量写反或沿用了错误值。
- 修复：修正 `backend/routers/storage_usage.py` 和 `backend/routers/large_files.py` 的导出 `media_type`。
- 验证：`.\.venv\Scripts\python.exe -m unittest backend.test.test_core_api` 通过。
- 风险：只验证了响应头和路由契约，未打开真实导出文件做人工内容验收。

### 2026-06-30：手动存储设备测试脚本包含真实连接信息
- 触发：审查后端测试和手动集成脚本。
- 现象：`backend/test/test_netapp.py`、`backend/test/test_isilon.py` 中存在真实设备地址、用户名和密码。
- 根因：手动验证脚本与自动测试目录混放，连接配置直接写在源码中。
- 修复：改为读取 `NETAPP_*`、`ISILON_*` 环境变量；NetApp 手动函数去掉 `test_` 前缀，避免自动测试误识别。
- 验证：`.\.venv\Scripts\python.exe -m unittest discover -s backend\test -p "test_*.py"` 通过，未触发真实外部连接。
- 风险：真实设备连通性未验证，需由具备环境变量的人工环境单独执行脚本。

### 2026-06-30：规范引用文件与当前仓库结构不一致
- 触发：按 `AGENTS.md` 和项目标准读取必读文档、前端样式入口。
- 现象：`docs/standards/domain-terminology.md` 不存在；`frontend/src/style.css` 不存在。
- 根因：规范引用仍指向旧文件，当前仓库实际样式入口为 `frontend/src/styles/style.scss`。
- 修复：新增 `docs/standards/domain-terminology.md`，并将前端标准中的全局样式入口改为 `frontend/src/styles/style.scss`。
- 验证：`docs/standards/domain-terminology.md` 已存在；前端实际入口由 `frontend/src/main.js` 引入 `frontend/src/styles/style.scss`。
- 风险：历史交付记录中如引用旧路径，需要以后续当前标准为准。

### 2026-07-14：通过 npm test 传递 Vitest 超时参数未生效

- 触发：执行 `npm test -- --testTimeout=15000` 全量验证前端。
- 现象：耗时约 `7.5` 秒的既有设置页测试仍按默认 `5000ms` 超时失败，npm 同时提示该参数被识别为未知 CLI 配置。
- 根因：当前 npm/脚本参数转发方式没有把 `--testTimeout` 传给 Vitest。
- 修复：直接执行 `.\\node_modules\\.bin\\vitest.cmd run --testTimeout=15000`。
- 验证：`25` 个测试文件、`126` 个测试全部通过。
- 风险：继续通过 `npm test -- ...` 追加 Vitest 参数可能重复触发默认超时，应直接调用仓库内 Vitest 命令。

### 2026-07-14：PowerShell 直接解析 ESLint brace glob 失败

- 触发：执行 `.\\node_modules\\.bin\\eslint.cmd src/**/*.{js,jsx,vue,ts,tsx} --fix`。
- 现象：PowerShell 在 `{js,jsx,...}` 处报 `Missing argument in parameter list`，ESLint 未启动。
- 根因：未引用的 brace glob 被 PowerShell 自身解析。
- 修复：使用调用运算符并把 glob 作为单个字符串传入：`& '.\\node_modules\\.bin\\eslint.cmd' 'src/**/*.{js,jsx,vue,ts,tsx}' --fix`。
- 验证：自动修复完成，随后 `npm run lint` 通过。
- 风险：PowerShell 下直接复制类 Unix brace glob 命令会再次失败，需要引用 glob 或通过 npm script 执行。

### 2026-07-14：聚焦测试导入 Celery 任务时缺少 Redis 包

- 触发：为集群保存后定向采集编写 RED 测试并直接导入 `celery_tasks.tasks.storages`。
- 现象：pytest 收集阶段报 `ModuleNotFoundError: No module named 'redis'`，目标断言未执行。
- 根因：`celery_worker.py` 直接导入 `redis`，但依赖文件只声明基础 `celery`，干净环境不会安装 Redis transport。
- 修复：将依赖声明改为 `celery[redis]`，安装 transport 后恢复定向快照测试。
- 验证：定向快照和 API 调度测试已进入目标断言；最终聚焦测试 `13 passed`，`pip check` 通过。
- 风险：本轮不会启动真实 Celery/Redis，后台任务消费仍需部署环境验证。

### 2026-07-14：存储集群表单缺少启用开关且调度无开发日志

- 触发：在管理后台编辑存储集群，并使用 `uvicorn main:app --reload` 观察保存后的采集调度。
- 现象：表单没有“是否启用”选项；开发控制台只有 HTTP access log，没有集群采集任务投递日志。
- 根因：`StorageClusterFormDialog` 的初始模型和模板遗漏 `is_active`；调度服务只记录异常，且普通应用 logger 的 INFO 不在 Uvicorn 默认输出中显示。
- 修复：表单新增默认启用的 `ElSwitch` 并提交 `is_active`；调度改用 `uvicorn.error` logger 记录开始、成功和失败，Celery 任务补充开始日志。
- 验证：同一组 RED 用例转为 GREEN；前端 `7 passed` 且生产构建通过，后端相关用例 `10 passed`、目标模块合计覆盖率 `93%`。
- 风险：真实 Redis、Celery worker 和存储设备日志仍需部署环境验证。

### 2026-07-14：自签名存储证书导致采集返回空数据

- 触发：Celery worker 通过 HTTPS 连接使用自签名证书的 NetApp。
- 现象：请求报 `CERTIFICATE_VERIFY_FAILED`，随后采集日志显示 `Fetched 0 volumes` 和 `Fetched 0 user quotas`。
- 根因：NetApp/Isilon 客户端支持 `tls_verify`，但采集入口未从存储配置传入；客户端又将连接异常吞成空结果。
- 修复（当时）：新增全局 `storage.tls_verify` 布尔配置并默认关闭，统一传入 NetApp/Isilon；API 连接和 HTTP 失败改为向上抛出，由集群事务回滚。该全局配置现已由逐 `StorageCluster` 的 `protocol`、`tls_verify` 字段取代并从 YAML 删除。
- 验证：配置默认值、类型校验、两个客户端参数贯通和连接失败传播共 `7 passed`。
- 风险：已有集群迁移为 `https/false` 以保持连接行为；关闭证书校验会降低中间人攻击防护，受信任证书环境应逐集群设为 `true`。HTTP 下设备凭据会以明文传输。

### 2026-07-14：QuestDB 缺少软限额列且 Aggregate 误写软限额字段

- 触发：NetApp 采集完成后，Celery worker 向 QuestDB 写入卷和聚合容量指标。
- 现象：`volume_storage_usages` 和 `aggregate_storage_usages` 均报 `Invalid column: soft_limit`；集群总容量指标仍可写入。
- 根因：软限额写入逻辑已启用，但 QuestDB 初始表没有对应列；通用写入分支还给不属于配额层的 Aggregate 强行加入了值为 `None` 的软限额字段。
- 修复：新增 QuestDB 前向迁移 `000000000002_add_soft_quota_metrics`，为五张配额历史表补充 `soft_limit`、`soft_use_ratio`；写入器仅在实体实际具备软限额属性时携带字段，Aggregate 保持物理容量口径。
- 验证：`cd backend && ..\.venv\Scripts\python.exe -m pytest test\test_questdb_migrations.py test\test_storage_soft_quota.py -q` 通过，`17 passed`。
- 风险：当前开发实例已升级并验证实际列；其他环境仍需先执行 `python -m questdb.migrate upgrade`，真实 NetApp 采集尚未重新触发。

### 2026-07-14：SQLAlchemy Inspector 无法读取 QuestDB 列元数据

- 触发：使用 `inspect(questdb_engine).get_columns(table)` 验证迁移后的实际列。
- 现象：`questdb-connect` inspector 调用 SQLAlchemy 2 已移除的 `Engine.execute()`，报 `AttributeError`；直接查询时未引用 `column` 又被 QuestDB 判定为保留字。
- 根因：当前 `questdb-connect` inspector 仍使用旧 SQLAlchemy API，同时 QuestDB 的 `table_columns()` 结果字段 `column` 需要双引号引用。
- 修复：验证命令改为通过显式 Connection 执行 `SELECT "column" FROM table_columns(:tn)`。
- 验证：五张配额历史表均返回 `soft_limit`、`soft_use_ratio`，`aggregate_storage_usages` 返回空列表。
- 风险：仅影响诊断命令，不影响业务写入；本轮不升级依赖，后续使用 Inspector 仍会复现。

### 2026-07-14：NetApp Qtree 请求包含不支持的 oplocks 字段

- 触发：Celery worker 调用 `GET /api/storage/qtrees` 同步 Qtree。
- 现象：ONTAP 返回 `400 Bad Request`，错误码 `262197`，提示 `oplocks` 对 `fields` 无效。
- 根因：客户端固定请求 `oplocks`，但当前 ONTAP 的 Qtree REST 资源不支持该字段。
- 修复：从 Qtree 请求字段中移除 `oplocks`；下游继续使用既有缺省值 `False`。
- 验证：逐字段只读探测确认只有 `oplocks` 返回 400；聚焦测试 `13 passed`；修改后的客户端从真实设备成功返回 `82` 条 Qtree。
- 风险：Celery worker 需要重启后才会加载新代码；`tls_verify=false` 的 HTTPS 集群仍会保留 `InsecureRequestWarning`。

### 2026-07-14：前端覆盖率全量测试超过默认 5 秒超时

- 触发：在 `frontend` 目录执行 `npm run test:coverage`。
- 现象：`147/150` 个用例通过，`3` 个较慢用例因超过默认 `5000ms` 超时失败，命令返回非零。
- 根因：全量 coverage 插桩增加执行耗时，三个用例超过 Vitest 默认 `5s` 限制，并非功能断言失败。
- 修复：在 `frontend/vitest.config.js` 统一将 `testTimeout` 调整为 `15000ms`，覆盖普通测试和 coverage，不再依赖额外命令参数。
- 验证：默认 `npm test` 和 `npm run test:coverage` 均为 `150/150` 通过；Statements/Lines `91.88%`、Branches `82.10%`、Functions `69.75%`。
- 风险：慢用例当前最长约 `13.8s`；若继续增长接近 `15s`，应优化模块加载和挂载开销，而不是继续放宽超时。

### 2026-07-14：多 LDAP 搜索范围导致登录误报快照不完整

- 触发：用户登录时按用户名依次查询多个 `ldap.user_bases`，首个范围没有该用户。
- 现象：登录接口返回 `500`，服务端抛出 `RuntimeError: incomplete LDAP directory snapshot`。
- 根因：完整 LDAP 同步新增的范围完整性检查被复用于单用户登录查询，把“该范围无匹配”错误视为同步快照不完整。
- 修复：单用户查询遇到无匹配范围时继续搜索；无用户名的完整快照查询仍在任一范围失败时中止。
- 验证：`backend/test/test_auth_ldap.py` 新增多范围登录回归；认证、用户管理与同步聚焦测试 `41 passed`，`compileall` 通过。
- 风险：未连接真实 LDAP 复验；需重启后端进程加载修复。

### 2026-07-14：项目组标签新增按钮造成列表额外留白

- 触发：打开“项目组标签”列表并与“存储集群”列表布局对比。
- 现象：“新增标签”单独占用筛选栏与表格之间的一行，表格整体下移，与同类列表不一致。
- 根因：标签页把新增按钮放在 `DataTable` 外部的独立右对齐容器中，没有复用操作列表头插槽。
- 修复：将“新增标签”移入最右侧 `ElTableColumn` 的 `#header` 插槽，删除独立按钮行。
- 验证：聚焦回归测试 `4 passed`，页面和测试文件 ESLint 通过。
- 风险：未连接运行中的前后端做浏览器截图复验。

### 2026-07-15：PostgreSQL AI 表预建导致 Alembic DuplicateTable

- 触发：数据库 revision 为 `000000000002` 时执行 `alembic upgrade head`。
- 现象：`000000000003` 创建 `ai_configs` 时报 `psycopg2.errors.DuplicateTable`。
- 根因：应用启动时的 `Base.metadata.create_all()` 已创建 AI 四表，但不会推进 Alembic 版本账本。
- 修复：移除 PostgreSQL 启动期 `create_all()`；`000000000003` 仅在四表及字段完整匹配时接管既有结构，部分或不匹配结构明确拒绝升级。
- 验证：复现测试先为 `3 failed`、修复后 `4 passed`；真实 PostgreSQL 已从 `000000000002` 升至唯一 head `000000000004`。
- 风险：其他环境若存在手工创建的半套 AI 表，需先核对并修复结构，不能直接 stamp revision。

### 2026-07-15：项目详情标签属性未换行导致 ESLint 失败

- 触发：对存储标签统一样式涉及的前端文件执行定向 ESLint。
- 现象：`ProjectDetailPage.vue:42` 报 `vue/max-attributes-per-line`。
- 根因：为内联 `ElTag` 增加共享样式类时，`type` 与 `class` 保留在同一行。
- 修复：将存储集群列及标签属性拆成多行，保持现有 Vue 模板格式。
- 验证：重新执行定向 ESLint、聚焦测试和生产构建。
- 风险：仅为模板格式问题，不影响后端接口或数据。

### 2026-07-15：存储术语组合测试存在两个既有契约失败

- 触发：统一存储标签样式后运行 `storage-resource-terminology.test.js` 组合测试。
- 现象：`11` 个组合用例中 `9 passed, 2 failed`；分别缺少用户目录“存储目标”列，以及存储集群详情“访问协议”/“TLS 证书校验”摘要。
- 根因：当前工作区中的 `UsageListPage.vue` 已有改动删除“存储目标”列；存储集群详情此前已收敛配置摘要，但旧术语测试仍保留历史断言。
- 修复：本轮不回退既有页面变更，仅将标签样式测试独立锁定为 6 个文件、12 个落点。
- 验证：标签聚焦测试、定向 ESLint、生产构建和后端软限额契约测试均通过。
- 风险：`storage-resource-terminology.test.js` 仍需在对应页面需求确认后单独更新或恢复实现。
### 2026-07-15：存储集群分析页加载态和筛选布局不一致

- 触发：打开存储集群详情并在“容量趋势”和“存储分布”之间切换。
- 现象：存储分布的自绘柱状加载动画位置异常；容量趋势筛选栏与页签内容分离，时间范围显示不全，两张主图高度不足。
- 根因：筛选栏位于页签卡片外；分布加载态使用独立 ECharts 图形并在页签切换期间初始化；主图高度分别硬编码为 `360px` 和 `420px`。
- 修复：筛选栏移入需要时间范围的页签内容区并扩宽日期时间字段，存储分布保持无时间筛选；分布改用 Element Plus 标准加载遮罩，两张主图统一为 `520px`。
- 验证：页面聚焦回归测试通过，`9 passed`；生产构建通过；Playwright 确认筛选栏位于页签内容区，加载遮罩完整覆盖 `1097.6×520px` 绘图区并保持居中。
- 风险：本地浏览器未登录，尚未使用真实后端数据复验图表内容和导出下载。

### 2026-07-15：Vite 端口参数被误解析为主机名

- 触发：执行 `npm run dev -- --port 5173` 启动本地视觉验证服务。
- 现象：实际命令变为 `vite --host 5173`，报 `getaddrinfo ENOTFOUND 5173`。
- 根因：项目 `dev` 脚本已以无值的 `--host` 结尾，追加的第一个参数被 Vite 当作 `--host` 的值。
- 修复：视觉验证改用 `npx vite --host 127.0.0.1 --port 5173`，显式提供主机和端口。
- 验证：本地页面返回 `200`，Playwright 成功打开存储集群详情并完成截图和尺寸检查。
- 风险：不影响生产构建；后续如继续通过 `npm run dev` 传参，应同时显式传入 `--host` 值。

### 2026-07-15：NIS Isilon 账号的 PAPI 登录权限再次返回 403

- 触发：使用两个独立 `StoragePulseMonitor` 对 Redis Session 缓存做真实 OneFS 复用验证。
- 现象：Redis `PING/set/get/delete` 正常，但 OneFS `/session/1/session` 返回 `403`，提示账号没有请求服务的登录权限；因此没有生成可复用的 Session，性能接口随后返回 `401`。
- 边界：同一账号在添加 `DiskPulseMonitor` 角色后曾成功登录并读取性能/事件；后续确认稳定 UID 已经是该角色成员，并发 Session 限制为 `0`，二者均不是根因。
- 后续：完整根因和修复见下方“NIS 人员账号执行 Isilon 身份解析后续 PAPI 登录 403”。
- 清理：诊断产生的 Redis 缓存项已删除，失败登录对应客户端已执行安全 logout/close。

### 2026-07-15：NIS 人员账号执行 Isilon 身份解析后续 PAPI 登录 403

- 触发：使用 NIS 人员账号执行 Isilon 配额 `resolve_names=true`、单 UID identity mapping 或 `auth/users/UID:<数字>` 任一身份解析请求，再创建新的 OneFS Session。
- 现象：容量 Session 登录 `201`、注销 `204`，紧接着性能 Session 登录 `403`，提示账号没有 `platform` 服务登录权限；执行 OneFS 身份缓存刷新后只能暂时恢复。
- 排除：角色已包含该 NIS 用户 UID；`Concurrent Session Limit` 为 `0`；不发送 logout 仍会复现；Storage Pool 查询和 `resolve_names=false` 的同量配额查询后，下一次登录均保持 `201`。域控 LDAP 单用户查询正常，但该目录没有 `uidNumber` 等 UNIX UID 属性，数据库内 522 个 LDAP 用户也均无 UID，因此不能用纯 LDAP 把配额 UID 关联到用户名。
- 根因：目标 OneFS 9.11.0.5 在 NIS 人员账号触发任何用户身份解析后，会改变后续登录使用的有效身份映射，使新 token 不再获得该账号原有的 PAPI 角色；安全注销不是根因。仅关闭名称解析虽然避免 403，却丢失 `UID → 用户名` 关联，不能满足用户配额与 LDAP 资料关联需求。
- 修复：创建专用 OneFS 本地服务账号并加入 `DiskPulseMonitor` 只读角色；DiskPulse 改用该账号采集，配额恢复 `resolve_names=true`，再用解析出的用户名关联现有 LDAP 用户。UID-only 和未知 persona 的安全回退仍保留。
- 验证：本地服务账号完成 `201 → 2270 条 resolve_names=true 配额 → logout → 201`，第二个 Session 状态查询为 `200`、性能接口返回 1 条记录；`UID:104407` 正确解析为目录用户名，LDAP 精确查询返回姓名和邮箱。
- 风险：需重启 Celery worker 才能加载配额默认参数；其他 Isilon 集群也应使用 OneFS 本地服务账号，避免外部身份提供者映射影响采集角色。

### 2026-07-16：配额容量被告警列表误显示为使用率

- 触发：在告警列表查看项目或项目组的配额调整历史记录。
- 现象：旧、新硬限额（如 `56320`、`57344` GiB）被显示成告警阈值、触发值和 `57344.00%` 使用率。
- 根因：配额调整记录复用 `storage_alerts.threshold`、`avg_use_ratio` 保存旧、新硬限额；前端未检查 `alert_type`，把所有项目和项目组记录按普通容量告警格式化。
- 修复：前端仅对 `alert_type=alert` 生成使用率告警摘要和展示告警专属字段；`quota_adjustment` 显示原始调整描述及独立类型。
- 验证：聚焦测试从 `8 passed, 1 failed` 变为 `9 passed`，目标页面 ESLint 和生产构建通过。
- 风险：未做真实登录态浏览器复验；历史数据无需迁移，刷新页面后按新逻辑展示。

### 2026-07-16：配额调整成功但未发送飞书通知

- 触发：通过项目组或用户目录接口成功调整配额。
- 现象：系统写入 `quota_adjustment` 记录并发送邮件，但没有生成飞书投递信息或进入飞书队列。
- 根因：配额服务只调用邮件通知；调整记录没有收件人、富文本正文和投递状态，也没有在事务提交后调用现有飞书任务。
- 修复：调整记录补充用户/负责人收件人和新旧软硬限额正文，提交后复用 `deliver_storage_alert_task`；入队异常不影响配额成功结果。
- 验证：聚焦测试从 `2 failed, 13 passed` 变为 `15 passed`，覆盖两类资源和入队失败边界。
- 风险：未连接真实 Redis/Celery 和飞书服务验证实际送达；现有飞书地址 TCP 不可达问题仍需先处理。

### 2026-07-16：配额测试误连接真实 Celery Broker 导致阻塞

- 触发：新增飞书入队逻辑后执行 `pytest backend/test/test_quota_adjustment.py -q`。
- 现象：既有 Isilon 用户配额成功用例在 `.delay()` 连接 Broker 时超过 60 秒未结束，测试被人工终止。
- 根因：该旧用例已 mock 设备和邮件边界，但未隔离新增的 Celery 入队边界。
- 修复：测试中 mock `_enqueue_adjustment_feishu`，聚焦测试不再访问外部 Broker。
- 验证：同一聚焦测试 `15 passed`，耗时约 2 秒。
- 风险：仅修复测试隔离；真实 Broker 与飞书送达仍需部署环境验收。

### 2026-07-17：PowerShell 无法直接解析 pytest 命令

- 触发：在仓库根目录执行 `pytest -q backend/test/test_dashboard_overview.py`。
- 现象：PowerShell 返回 `pytest : The term 'pytest' is not recognized`。
- 根因：项目测试依赖安装在根目录 `.venv`，当前 shell 没有全局 `pytest` 可执行文件。
- 修复：改用 `.\.venv\Scripts\python.exe -m pytest -q backend/test/test_dashboard_overview.py`。
- 验证：Dashboard 后端聚焦测试 `4 passed`。
- 风险：后续 PowerShell 命令应显式使用项目虚拟环境，避免误用系统 Python。

### 2026-07-17：Vitest 聚焦路径重复导致找不到测试

- 触发：在 `frontend` 目录执行 `npm test -- --run frontend/test/unit/components/dashboard-chart.test.js frontend/test/unit/pages/dashboard-page.test.js`。
- 现象：Vitest 报 `No test files found`，并提示 `--run` 被 npm 解析为未知配置。
- 根因：工作目录已经是 `frontend`，参数仍带 `frontend/` 前缀；同时项目 `test` 脚本本身已经执行 `vitest run`。
- 修复：改用 `npm test -- test/unit/components/dashboard-chart.test.js test/unit/pages/dashboard-page.test.js`。
- 验证：目标两个测试文件共 `4 passed`；扩展 Dashboard 与图表契约组合测试共 `13 passed`。
- 风险：从 `frontend` 目录执行聚焦测试时必须使用 `test/...` 相对路径，不重复附加 `--run`。

### 2026-07-17：浅挂载无法读取 SFC scoped style 计算值

- 触发：在 Dashboard 切换加载测试中对 `getComputedStyle(wrapper.element).alignContent` 断言 `start`。
- 现象：Vitest/JSDOM 返回空字符串，页面测试 `3 passed, 1 failed`。
- 根因：当前 `shallowMount` 测试环境不注入 Vue SFC 的 scoped style，不能通过计算样式验证该 CSS 声明。
- 修复：删除不可靠的计算样式断言，改由切换期间页头、三类图表标题和多个分区骨架持续存在的用户可见行为锁定无整页留白结果；生产构建继续验证 CSS 可编译。
- 验证：Dashboard 页面聚焦测试恢复 `4 passed`。
- 风险：CSS 像素级结果仍需登录态浏览器复验；JSDOM 只覆盖 DOM 结构和加载行为。

### 2026-07-17：Dashboard 全局容量趋势因 QuestDB SYMBOL 查询返回空数组

- 触发：使用当前 PostgreSQL 与 QuestDB 配置直接调用 Dashboard 全局容量趋势服务。
- 现象：QuestDB 报 `STRING constant expected`，错误 SQL 包含 `storage_cluster_id IN (2, 1)`；服务按降级策略捕获异常并向前端返回空数组。
- 根因：`storage_cluster_id` 在 QuestDB 中是 `SYMBOL`，接口把 PostgreSQL 数值主键直接拼接进查询，类型不匹配。
- 修复：全局趋势查询使用 expanding bind 参数，并把启用集群 ID 转为字符串后绑定，不再拼接 SQL 标识值。
- 验证：后端聚焦测试 `5 passed`；真实 QuestDB 查询返回 4 个日采样点，范围为 `2026-07-14` 至 `2026-07-17`。
- 风险：项目趋势仍为空；`project_storage_usages` 当前没有记录，且现有采集器未写入项目级时序指标，需要单独补齐采集链路。

### 2026-07-17：合并后旧前端覆盖测试与共享图表生命周期和 Pinia 装配不一致

- 触发：合入前端审计与配额响应式分支后运行前端全量测试。
- 现象：图表覆盖测试仍按同步初始化和固定销毁次数断言；`Progress`、系统设置的浅挂载未注入 Pinia，共计 `8 failed, 333 passed`。
- 根因：共享 ECharts 生命周期改为异步加载，多个属性 watcher 会分别触发更新；配额阈值改由 Pinia store 提供，但旧测试装配未随依赖更新。
- 修复：图表用例等待异步任务完成并验证有效的生命周期行为；通用组件和管理页挂载统一注入独立 Pinia。
- 验证：三个失败文件聚焦测试 `33 passed`，前端全量测试 `341 passed`。
- 风险：测试仍会输出既有的模拟网络和 Vue stub 警告，但不影响退出状态。

### 2026-07-17：后端弃用告警回归测试误捕获无关 SQLite ResourceWarning

- 触发：合并后运行后端全量测试。
- 现象：`schemas.usersSchema` reload 用例捕获其他测试延迟回收连接产生的两个 `ResourceWarning`，结果为 `1 failed, 369 passed`；单文件执行为 `14 passed`。
- 根因：用例名称和目标只检查弃用告警，但断言错误地拒绝了 warning context 内的所有告警，导致全量并发对象回收时出现非目标失败。
- 修复：与同文件另一用例保持一致，仅筛选并断言 `DeprecationWarning`。
- 验证：后端全量测试 `370 passed`。
- 风险：该调整不隐藏弃用告警；SQLite 连接资源管理仍由对应数据库测试单独负责。

### 2026-07-17：限额标签改色后旧静态契约与模板格式失败

- 触发：提交限额与存储类型 `ElTag` 调整前运行聚焦测试和 ESLint。
- 现象：旧测试仍要求六个页面使用 `storage-info-tag` 紫色样式；`GroupListPage.vue` 的单属性标签换行违反 `vue/first-attribute-linebreak`。
- 根因：标签已改为 `danger`、`warning`、`success` 和 `info` 语义类型，但静态测试仍锁定旧共享样式实现；模板换行未遵守当前 ESLint 规则。
- 修复：静态契约改为检查无软限额和存储类型的语义标签，单属性标签恢复同行格式。
- 验证：相关聚焦测试 `4 files / 90 passed`，受影响文件 ESLint 通过。
- 风险：静态契约验证源代码标记，不替代浏览器视觉验收。

### 2026-07-17：全站存储集群与存储类型展示口径不一致

- 触发：以用户目录列表为基准检查项目组、项目及存储资源列表。
- 现象：部分页面把集群和类型合并为一列，部分页面缺少存储类型，类型标签还同时存在 `info` 与 `success` 两种语义色。
- 根因：各列表独立实现存储归属信息，项目列表接口只返回类型集合，缺少可供名称与类型稳定配对的集群摘要。
- 修复：新增共享存储类型标签组件；各相关列表拆分集群和类型列；项目列表接口返回去重、稳定排序的集群摘要。
- 验证：后端项目相关聚焦测试 `24 passed`，前端相关聚焦测试 `8 files / 62 passed`，受影响文件 ESLint 通过。
- 风险：本地应用端口当前拒绝连接，静态和组件测试不替代登录态浏览器中的最终列宽与视觉验收。

### 2026-07-17：覆盖率全量运行中的邮件选择器用例偶发超时

- 触发：首次执行前端全量覆盖率测试。
- 现象：`select-function-coverage.test.js` 的邮件搜索用例超时，后续用户邮件更新事件断言随之失败；普通全量测试此前为 `351 passed`。
- 根因：覆盖率并发运行时该文件的异步邮件搜索超过 `15s`，造成后续断言受前一用例未完成状态影响；与本次存储展示文件无调用关系。
- 处理：未修改无关选择器；单文件覆盖率复跑 `11 passed`，随后全量覆盖率复跑 `57 files / 351 passed` 并达到门禁。
- 风险：该并发时序波动仍可能在资源紧张的环境中复现，后续应单独评估测试隔离或超时配置。

### 2026-07-17：后端全量覆盖率命令因工具超时配置过短被终止

- 触发：通过 shell 工具执行 `.\.venv\Scripts\python.exe -m coverage run -m pytest backend\test -q`，但调用超时误设为约 `5s`。
- 现象：测试进程在全量用例完成前被工具终止，没有生成完整 pytest 与覆盖率结果。
- 根因：shell 工具的执行超时不足以覆盖后端全量测试耗时，属于命令执行配置错误，不是测试用例失败。
- 修复：保持测试命令不变，将 shell 工具超时提高到 `120000ms` 后重新执行，并运行 `.\.venv\Scripts\python.exe -m coverage report` 生成覆盖率报告。
- 验证：复跑完成，pytest 结果为 `386 passed`，覆盖率报告为 `TOTAL 91%`，退出状态成功。
- 风险：后续运行后端全量测试或覆盖率测试时应预留足够工具超时，避免把外层进程终止误判为测试失败。

### 2026-07-17：仓库根目录无法直接运行 QuestDB migration 模块

- 触发：在仓库根目录执行 `.\.venv\Scripts\python.exe -m questdb.migrate history`。
- 现象：Python 返回 `ModuleNotFoundError: No module named 'questdb'`。
- 根因：仓库根目录执行时，`backend` 包根目录不在 `sys.path` 中，无法解析 `questdb` 模块。
- 修复：切换到 `backend` 目录，执行 `..\.venv\Scripts\python.exe -m questdb.migrate history`。
- 验证：命令成功列出 `000000000001` 至 `000000000004 user_storage_usages` 的完整 revision 历史。
- 风险：文档和运维命令必须明确要求从 `backend` 目录执行，或显式配置包含 `backend` 的 `PYTHONPATH`。

### 2026-07-17：应用页脚随内容滚动且未贴合工作区边缘

- 触发：在用户目录页检查底部版权区域的高度、滚动归属和左右边界。
- 现象：页脚高度为 `60px`，位于业务内容 `ElScrollbar` 内，并受主内容左右内边距影响，无法贴合侧栏和浏览器右边缘。
- 根因：`AppFooter` 被放在内容滚动视图末尾，应用壳没有独立的右侧纵向工作区；页脚因此继承内容滚动和留白规则。
- 修复：新增右侧工作区，将 `ElMain` 与 `AppFooter` 调整为上下兄弟节点；页脚高度改为 `40px`，主内容改为占用剩余高度的独立滚动区。
- 验证：RED 聚焦测试 `2 failed, 4 passed`，GREEN 后 `6 passed`；前端全量覆盖率测试 `60 files / 359 passed`，目标 ESLint 和生产构建通过。
- 风险：按用户要求跳过完整浏览器滚动验收；既有窄屏固定侧栏溢出未纳入本次修复。

### 2026-07-17：全站内容区外层间距不一致

- 触发：对 `/usage` 及全站在用列表、管理和详情页面检查内容区上下左右留白。
- 现象：不同页面的外层间距不一致；部分页面叠加页面根 padding、共享布局 padding 与 `ElMain` 默认 `20px`，造成内容与面包屑无法稳定对齐。
- 根因：应用壳与页面样式同时承担外层 gutter，且 Element Plus `ElMain` 默认 padding 未显式清零。
- 修复：将外层 gutter 收敛到 `AppLayout`，桌面统一 `16px`、`<=768px` 统一 `12px`；清除共享布局、页面根节点的重复外层 padding，并显式清零 `ElMain` 默认 padding，保留业务组件内部间距。
- 验证：RED `11 tests | 9 failed, 2 passed`；GREEN `11/11`；目标 ESLint 通过；覆盖率 `61 files / 370 tests passed`（Statements `98.3%`、Branches `88.74%`、Functions `84.17%`、Lines `98.3%`）；生产构建与 `git diff --check` 通过。13 个可加载路由在 `1383x994`、`936x994` 及 `/usage` 移动宽度代表值完成浏览器间距检查。
- 补充环境故障与恢复：旧依赖预构建缓存导致 Vite `504 Outdated Optimize Dep`，停止旧 `5173` 进程后以 `npx vite --host 0.0.0.0 --port 5173 --force` 重启，输出 `Forced re-optimization`；`/ai/chat` 当前桌面已恢复渲染，`.ai-workspace` 存在、gutter 为 `16px`、无 Vite overlay，整页刷新后 console errors 为 `0`。
- 风险：真实 ID 详情页、`320px` viewport 未验证；`375/414` 固定侧栏水平溢出为既有问题。

### 2026-07-17：显式空工具参数被错误归一化为可执行对象

- 触发：模拟 OpenAI 工具 `arguments=""` 与 Claude 工具 `input=[]` 的流式响应。
- 现象：客户端没有抛出参数格式错误，空值被 `or "{}"` 分支替换后可能进入工具执行。
- 根因：代码没有区分“参数字段缺失”与“参数字段显式提供但值为空/非对象”。
- 修复：仅在字段缺失时兼容空对象；显式空字符串进入 `invalid_json`，数组等非对象进入 `non_object`，原始参数不写入审计。
- 验证：后端 AI 聚焦组合测试 `39 passed`，覆盖 OpenAI 和 Claude 两类输入。
- 风险：真实 Provider 的异常流格式仍需部署环境验证。

### 2026-07-17：SSE 终态顺序异常可能遗留生成中消息

- 触发：向前端流模拟 `completed → accepted` 或 `accepted → completed → delta`。
- 现象：旧状态机只统计是否出现过确认和终态，错误顺序仍会 resolve，页面可能留下 `streaming` 助手消息。
- 根因：协议校验没有约束确认必须先到，也没有拒绝终态后的已知事件。
- 修复：客户端要求先收到 `accepted`，终态后任一已知事件立即作为可重试协议错误抛出，页面保留部分内容并清理流状态。
- 验证：工作进程执行前端 AI 聚焦用例 `23 passed`。
- 风险：当前主线程 shell 无法复跑 Vitest，见本日志末条环境限制。

### 2026-07-17：系统管理 DELETE 的 204 响应被误判为工具失败

- 触发：超级管理员调用返回 `204 No Content` 的系统管理删除工具。
- 现象：内部 ASGI 调用成功后 JSON 解析失败，工具返回“工具返回了非 JSON 响应”。
- 根因：工具执行器把所有成功响应都假定为 JSON，未处理 HTTP 204 的无内容语义。
- 修复：仅将 `204` 映射为 `{ok: true, data: null}`，其他非 JSON `2xx` 仍保持原有错误边界。
- 验证：新增删除空响应用例通过，后端 AI 聚焦组合测试 `39 passed`。
- 风险：其他非 JSON 成功响应未被放宽，后续如新增此类接口须显式评估。

### 2026-07-17：受限本地环境阻断 Git 暂存与 Vitest 子进程

- 触发：执行 `git add` 创建 `.git/index.lock`，以及在主线程执行 AI 前端 Vitest 聚焦命令。
- 现象：Git 返回 `Permission denied`；Vitest 在加载配置时因 esbuild 子进程返回 `spawn EPERM`。
- 根因：当前 Windows 受限 shell 不允许相应的 Git 索引写入和子进程创建，不是代码或测试断言失败。
- 修复：后端测试以禁用 pytest cache 的方式完成；前端结果使用工作进程已成功的同一聚焦命令作为验证证据，改动未丢失。
- 验证：后端 `39 passed`、工作进程前端 `23 passed`；Git 工作区仍保留本轮未提交改动。
- 风险：需要具备正常 `.git` 写权限和 esbuild 进程权限的环境才能创建提交并独立复跑前端测试。
### 2026-07-18：遥测运行账本终态与最新成功读取审查缺陷

- 触发：对 `TelemetryCollectionRun` 约束和 `/metrics` 读取路径进行 CodeGraph 审查并添加回归测试。
- 现象：终态记录可缺少 `finished_at`，运行中记录可错误携带终态字段；最新成功查询会读取同一组件/集群的全部历史成功行后在 Python 选择第一行。
- 根因：终态 `CheckConstraint` 只限制部分字段组合，且 CRUD 查询缺少按组件/集群分组的数据库级最新行筛选。
- 修复：将运行中/结束状态写入同一互斥约束，索引改为 `finished_at DESC`；使用 `row_number()` 窗口函数只返回每组最新成功记录。
- 验证：对应 RED 测试分别失败；GREEN 后遥测聚焦 `30 passed`、全量后端 `440 passed`、跨方言迁移编译和 SQLite 升降级通过。
- 风险：真实 PostgreSQL 的执行计划与生产账本规模仍需在部署暗运行阶段观察。

### 2026-07-18：未处理 HTTP 5xx 未进入 RED 指标

- 触发：为未处理路由异常新增 HTTP 指标回归测试。
- 现象：请求返回 `500`，但 `diskpulse_http_requests_total` 与耗时记录函数未被调用。
- 根因：中间件在异常重抛前跳过了正常返回后的指标记录代码。
- 修复：在关闭请求数据库会话的 `finally` 中记录预设的 `500` 响应状态与耗时；探针短路路径保持不创建常规会话。
- 验证：RED 用例失败；GREEN 后关联 API 用例通过，完整后端测试 `440 passed`。
- 风险：生产指标端点的实际 scrape 延迟与并发负载仍需部署环境验收。

### 2026-07-18：Vitest 源文件断言误用 `import.meta.url`

- 触发：执行 `cd frontend; npm exec vitest run test/unit/StorageClusterDetailPage.test.js --coverage.enabled=false`。
- 现象：测试初始化报 `TypeError: The URL must be of scheme file`，无法读取 `StorageClusterDetailPage.vue`。
- 根因：Vitest 转换模块后的 `import.meta.url` 是开发服务器 URL，不保证是 `file:` URL，不能直接传给 Node 的 `fileURLToPath()`。
- 修复：测试改用当前前端工作目录 `process.cwd()` 与 `node:path.resolve()` 定位源文件。
- 验证：关联事件中心聚焦 Vitest 套件重跑通过。
- 风险：该静态断言仅保护懒加载声明与页签边界；实际渲染仍须由浏览器验收覆盖。

### 2026-07-18：隔离 worktree 缺少运行时 `backend/config.yml`

- 触发：在隔离 worktree 的 `backend` 目录执行 `D:\dev\DiskPulse\.venv\Scripts\python.exe -c "from celery_tasks.tasks import forecast_incidents"`。
- 现象：任务模块导入时 `appConfig` 报 `Configuration file not found: ...\\backend\\config.yml`。
- 根因：`backend/config.yml` 是包含部署凭据的被忽略运行时文件，Git worktree 不会复制该文件。
- 修复：未复制或提交真实配置；单元测试继续使用 `backend/config.test.yml` 注入配置。部署/本地 worker 验收前须由操作者以受控方式提供真实运行时配置。
- 验证：不依赖运行时配置的后端聚焦测试、编译和前端聚焦测试均可执行。
- 风险：Celery 任务在真实 Redis、PostgreSQL、QuestDB 配置下的注册和执行仍待部署环境验证。

### 2026-07-18：仓库根目录 Alembic 命令缺少后端模块路径

- 触发：执行计划中的 `D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head`。
- 现象：首次执行在加载 `backend/migrate/env.py` 时返回 `ModuleNotFoundError: No module named 'appConfig'`。
- 根因：迁移环境只依赖 `cd backend` 时隐式存在的模块搜索路径，仓库根目录的 `-c backend/alembic.ini` 调用没有把 `backend` 加入 `sys.path`。
- 修复：`migrate/env.py` 从自身绝对位置解析并加入 `backend` 模块根；重跑后已越过模块导入，按预期停在隔离 worktree 缺少被忽略 `config.yml` 的环境边界。
- 验证：同一命令重跑不再出现 `appConfig` 导入错误；迁移 DDL 的 SQLite 升降级和三方言离线编译继续由自动化测试覆盖。
- 风险：真实 PostgreSQL 升级仍要求部署方提供受控运行时配置与数据库连接。

### 2026-07-18：前端不存在通用 `build` 脚本

- 触发：在 `frontend` 执行 `npm run build`。
- 现象：npm 返回 `Missing script: "build"`。
- 根因：仓库将构建入口显式命名为 `build:test` 和 `build:prod`，未定义通用别名。
- 修复：使用测试模式的实际脚本 `npm run build:test`；构建成功。
- 验证：Vite 完成 2,583 个模块转换并生成测试构建产物；保留既有 `%VITE_APP_TITLE%` 未定义与大 chunk warning。
- 风险：未运行需要部署变量的 `build:prod`，真实发布环境仍应使用受控变量执行生产构建。

### 2026-07-18：应用内浏览器拦截本地 Vite 验收

- 触发：启动本地 Vite 后使用应用内浏览器访问 `http://127.0.0.1:5173/incidents`。
- 现象：首次为 `ERR_CONNECTION_REFUSED`；启动服务后浏览器策略返回 `ERR_BLOCKED_BY_CLIENT`，无法取得页面 DOM、截图或执行交互。
- 根因：当前应用内浏览器客户端阻止本机回环地址访问；不是事件中心路由的前端运行时异常。
- 修复：未绕过浏览器策略或改用未经授权的外部自动化；停止临时 Vite 服务，保留 Vitest 与 Vite 测试模式构建验证。
- 验证：组件聚焦测试和 `npm run build:test` 均通过；应用内浏览器验收待允许本机 URL 后重试。
- 风险：未获得真实浏览器截图、控制台和交互证据，详情抽屉与集群页签需在可访问的本机/部署浏览器补验。

### 2026-07-18：事件中心 Vue 模板未满足属性换行 lint 规则

- 触发：执行事件中心相关 Vue 文件的 `npx eslint`。
- 现象：`vue/max-attributes-per-line` 报告 96 条属性未按项目规则换行的错误。
- 根因：已有事件中心模板与新增详情/关联页签均使用多属性单行写法，未遵循当前 ESLint 配置。
- 修复：仅对事件中心、详情抽屉、关联页签和集群详情四个相关组件执行 ESLint 自动格式化；不改变 API、状态或权限逻辑。
- 验证：相同 scoped ESLint 命令通过，4 个前端聚焦测试继续通过。
- 风险：未执行全仓 ESLint；其他目录的既有格式问题不在本次范围内。

### 2026-07-18：后端 scoped Ruff 检查不可用

- 触发：使用项目虚拟环境执行 `python -m ruff check` 检查本次 Python 文件。
- 现象：解释器返回 `No module named ruff`。
- 根因：当前 `D:\dev\DiskPulse\.venv` 未安装 Ruff，仓库也没有将其作为现有验证依赖。
- 修复：未下载、安装或修改依赖；改用已安装的 `compileall` 和 pytest 聚焦回归。
- 验证：Python 编译与后端聚焦测试通过。
- 风险：未获得 Ruff 的静态规则覆盖；如 CI 引入 Ruff，应在依赖锁定后补跑同一 scoped 检查。

### 2026-07-18：性能异常扫描的资产键被星号解包为列表

- 触发：执行固定性能样本的连续三点异常任务回归测试。
- 现象：扫描在读取对象名称时抛出 `TypeError: unhashable type: 'list'`。
- 根因：循环使用 `for (*identity, metric)`，Python 将前三个资产键放入可变 `list`，后续用作 `names` 字典键时失败。
- 修复：改为显式解包 `cluster_id, object_type, object_id, metric` 并重建元组资产键。
- 验证：事件中心后端测试 `20 passed`，连续三点延迟/IOPS/吞吐异常均被识别。
- 风险：该回归覆盖纯 QuestDB 行转换；真实性能表的厂商对象映射仍需隔离环境回放。

### 2026-07-18：事件中心合并审查发现迁移、连续性与通知通道缺口

- 触发：在整合并行审查分支后执行 Alembic 图检查及固定事件中心回归。
- 现象：并行分支初始存在两份 `000000000010` 迁移；间隔 10 分钟的三条异常被识别为连续；已过期静默仍阻断升级通知；关闭飞书时邮件通道不会发送。
- 根因：两个并行分支各自使用相同 Alembic revision；异常判断只取最近三条分数而未验证时间相邻；通知逻辑只判断静默字段是否为空，且错误地以飞书开关包裹邮件路径。
- 修复：保留主线已发布的 `000000000010_telemetry_failed_error_code`，将 Incident 表迁移顺延为 `000000000011_forecast_incidents`；要求相邻异常点恰隔 5 分钟；按 UTC 当前时间判断静默有效期；拆开飞书和邮件投递条件。
- 验证：迁移拓扑和三条行为 RED 回归均失败后转绿；Alembic `heads` 显示唯一 `000000000011 (head)`，后端全量、前端事件中心聚焦测试和测试模式构建通过。
- 风险：真实 PostgreSQL 升级、Redis/Celery 任务、QuestDB 样本和外部通知通道仍未在隔离环境执行。

### 2026-07-18：隔离 worktree 缺少本地 Python 与前端依赖

- 触发：在 `D:\dev\DiskPulse\.worktrees\review-fixes` 执行后端全量测试和前端 Vitest。
- 现象：`..\.venv\Scripts\python.exe` 不存在；首次 Vitest 无法找到 `frontend/node_modules`。
- 根因：Git worktree 不复制被忽略的本地虚拟环境与 Node 依赖目录。
- 修复：后端显式使用主工作区只读解释器 `D:\dev\DiskPulse\.venv\Scripts\python.exe`；前端在隔离 worktree 执行 `npm ci` 恢复 lockfile 对应依赖。
- 验证：后端全量 `530 passed`，前端 coverage `67 files / 412 passed`、lint 与生产构建通过。
- 风险：依赖目录不应提交；后续新 worktree 仍需按环境初始化步骤准备。
# 2026-07-18：Mock 未登录首屏空白

- **现象**：`VITE_USE_MOCKS=true` 时直接访问 `/`，浏览器控制台出现 `Cannot read properties of undefined (reading 'errorHandlerDisabled')`，页面没有内容。
- **原因**：Mock adapter 的 401 在 Axios 生成 `error.config` 前抛出，响应拦截器二次访问空配置；路由守卫捕获后也没有返回目标。
- **修复**：响应拦截器使用可选链，守卫将认证失败显式重定向到带 `redirect` 的 `/login`。
- **验证**：应用内浏览器重新访问根路由后应显示登录页和四个演示账户。

## 2026-07-18：全量 compileall 误扫描 worktree 虚拟环境

- **触发**：在容量预测治理 worktree 执行 `python -m compileall -q backend`。
- **现象**：第三方 `backend/.venv/Lib/site-packages/isilon_sdk` 的超长模型模块在写入 `__pycache__` 时报告 `FileNotFoundError`。
- **根因**：命令把被忽略的虚拟环境依赖也当作项目源码扫描；失败路径不属于本仓库业务代码。
- **修复**：改用 `python -m compileall -q -x "[\\/]\\.venv[\\/]" backend`，源码编译通过；未修改或提交虚拟环境。
- **风险**：未对虚拟环境第三方包做编译验证；依赖包应由环境初始化和锁定流程单独负责。

## 2026-07-18：容量预测治理审查发现窗口、模型状态与新鲜度缺口

- **触发**：对资源级容量预测与 AI 治理实现执行权限、事务、审计、候选新鲜度和前端状态审查。
- **现象**：同一回测窗口可重复计入三窗口门槛；候选关联模型停用后仍可激活；重复版本抛出数据库异常；旧候选曲线可覆盖当天基线；预测不存在时页面显示错误；领域写操作产生额外通用审计；API 可保存零变化或空白说明计划。
- **根因**：启用门槛只统计行数；激活未复核模型；唯一约束异常未转为领域错误；候选查询未绑定当前 `training_end`；前端把所有请求拒绝统一处理；通用审计未识别新增领域路由；容量计划仅依赖前端表单校验。
- **修复**：增加回测窗口数据库唯一约束和服务校验；激活时复核私有模型；重复版本/窗口返回 `409`；基线按训练日期排序并只叠加同日候选；前端单独处理 `404` 空态；容量预测写路由排除通用重复审计；Pydantic 拒绝零值、非有限值和空白说明。
- **验证**：相关 RED 用例先稳定失败，修复后后端聚焦回归 `92 passed`，前端预测测试 `7 passed`，scoped ESLint、源码编译、三方言迁移编译、生产构建和 `git diff --check` 均通过。
- **风险**：真实 PostgreSQL 并发写入、Celery/Redis 调度、QuestDB 数据与私有 Ollama 仍需隔离环境联调。
