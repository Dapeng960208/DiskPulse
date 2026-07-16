# 错误记录

### 2026-07-16：存储告警实施基线存在三个既有回归失败

- 触发：在独立 Worktree 开始功能实施前执行 `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend\test -q` 和 `npm test`。
- 现象：后端为 `283 passed, 1 failed`，`test_storage_health_migration_backfills_attributable_alerts_on_sqlite` 实际得到 `(None, "diskpulse", "info")`；前端为 `194 passed, 2 failed`，`storage-resource-terminology.test.js` 找不到 `label="存储目标"` 和 `label="访问协议"`。
- 根因：后端测试按迁移文件名取最后一个迁移，新增 `000000000005` 后不再执行待测的 `000000000004` 回填；前端两个术语断言已与当前页面删除的列和详情摘要不一致。三项均可在功能代码改动前稳定复现。
- 处理：按存储告警实施计划的基线门禁暂停；用户确认继续后，后端测试改为按明确 revision 定位待测迁移，前端术语测试同步当前页面契约，修复提交为 `d16e8f1`。
- 验证：修复后后端全量 `284 passed`；前端全量 39 个测试文件、`196 passed`。`npm ci` 成功，Alembic `heads/history` 成功且唯一 head 为 `000000000005`，CodeGraph 索引为最新。
- 风险：本条只确认既有基线恢复；存储告警接口、迁移、任务和页面仍处于待实现状态，必须按本功能 RED/GREEN 验证单独验收。

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
