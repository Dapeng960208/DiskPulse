# 当前交付记录

## 2026-07-14：集群配置后自动同步卷信息

### 主题

启用的 NetApp 或 Isilon 集群在创建、更新后立即投递对应集群的卷采集任务。

### 已完成

- 存储集群创建、更新接口在事务提交后按最终 `is_active` 状态投递异步采集；未启用集群不投递。
- 复用 `storages_schedule_fetching_task` 和 `StoragePulseMonitor`，新增可选 `storage_cluster_id` 过滤，不新建第二套设备采集逻辑。
- Celery 依赖声明改为 `celery[redis]`，补齐现有 Redis broker/lock 代码的 transport 依赖。

### 验证状态

- RED：集群 CRUD 聚焦测试 3 个用例因缺少调度行为失败；定向快照测试因不支持 `storage_cluster_id` 失败。
- GREEN：`.\.venv\Scripts\python.exe -m pytest backend\test\test_storage_soft_quota.py backend\test\test_core_api.py backend\test\test_storage_collection_trigger.py -q` 通过，`13 passed`。
- `.\.venv\Scripts\python.exe -m pip check` 与 `.\.venv\Scripts\python.exe -m compileall -q backend`：通过。
- 任务范围 coverage：`storage_cluster.py` `92%`、`storageClusterService.py` `100%`，合计 `93%`。

### 风险与后续

- 未连接真实 NetApp、Isilon、Redis 或 Celery worker；真实设备卷数据和任务消费链路待部署环境验证。
- 任务投递失败不会回滚已保存配置，错误写入服务端日志，后续周期采集继续兜底。

## 2026-07-14：项目组标签与直接资源绑定

### 主题

删除项目级存储环境关系，将其收敛为只包含名称的全局 `GroupTag`；`Group` 直接绑定项目、存储集群和标签。

### 已完成

- `group_tags` 只保留 `id`、`name`，名称全局唯一；标签不绑定项目或存储集群，也不保存容量、状态或采集时间。
- `groups` 直接保存非空的 `project_id`、`storage_cluster_id`、`group_tag_id`，并继续严格校验 Volume/Qtree 必须属于所选集群。
- 新增 `/storage-pulse/api/group-tags` 全局 CRUD；标签写操作要求超级管理员，重复名称和删除已引用标签返回 `409`。
- 采集、告警、Usage、备份和周报改为读取 Group 的直接关系；删除环境级 QuestDB、汇总、告警和实时趋势语义。
- 前端新增“项目组标签”管理页和选择器；项目组表单分别选择项目、存储集群、标签，项目详情和 Dashboard 按 Group 直接展示。
- 单一 Alembic baseline 已改写；不提供旧 `project_storage_environments` 数据兼容或回填。

### 验证状态

- 后端 `python -m pytest backend/test -q`：`66 passed`；`python -m compileall -q backend`：通过。
- 前端 `.\\node_modules\\.bin\\vitest.cmd run --testTimeout=15000`：`25` 个测试文件、`126 passed`；`npm run build:prod`：通过。

### 风险与后续

- 使用旧 baseline 的开发数据库不能原地升级，需确认数据可丢弃后重建空库。
- 未连接真实 PostgreSQL、QuestDB、NetApp、Isilon 或 Celery worker 做端到端验证。

## 2026-07-14：QuestDB 版本管控与启动初始化

### 主题

将当前 `7` 张 QuestDB 趋势表纳入独立前向 revision 管控，并替换启动时无版本记录的 `QuestDBBase.metadata.create_all()`。

### 已完成

- 新增 `backend/questdb/migrations/000000000001_initial_schema.sql`，结构与当前 `QuestDBBase.metadata` 一致。
- 新增 `backend/questdb/migrate.py`，提供 `history/current/upgrade`，通过 `diskpulse_schema_migrations` 记录版本、SHA-256 checksum 和应用时间。
- `database.create_tables=true` 时启动自动执行 QuestDB upgrade；重复执行跳过已应用 revision，checksum 漂移和本地未知 revision 会失败。
- QuestDB 采用前向、幂等 migration，不模拟其不支持的 PostgreSQL 主键、事务回滚或 PGWire `DELETE`。

### 验证状态

- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend\test\test_questdb_migrations.py -q`：通过，`12 passed`；任务专用 coverage 配置下 `backend/questdb/migrate.py` statements/branches 综合覆盖率 `98%`。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend\test -q`：通过，`158 passed`、`41` 个既有弃用 warning；`compileall -q backend` 通过。
- PostgreSQL Alembic `heads/history`：通过，唯一 root/head 为 `000000000001`。
- 使用当前配置导入 `main`：启动迁移成功；QuestDB 的 `7` 张业务表逐列与 `QuestDBBase.metadata` 一致，版本账本存在。
- 当前配置 QuestDB：`history/current/upgrade/current` 通过，revision 为 `000000000001`；共 `8` 张表，包括 `7` 张趋势表和 `diskpulse_schema_migrations`；重复升级返回 `up to date`。

### 风险与后续

- 尚未在独立空白 QuestDB 实例执行从 `base` 到 head 的录像式验收；当前实例的首次创建可能由运行中的自动重载服务触发。
- QuestDB migration 不提供自动 downgrade；破坏性回退必须先备份，再使用独立修复 revision 或重建实例。
- 多副本生产部署应由单一迁移节点先执行 `python -m questdb.migrate upgrade`，再启动 API/worker，避免并发执行未来可能不具备天然幂等性的 DDL。

## 2026-07-13：项目存储环境分层、绑定与采集隔离（已废弃）

> 该方案已由 2026-07-14 的 `GroupTag + Group` 直接绑定模型替代，仅保留为历史交付记录。

### 主题

在 `Project` 与存储资源之间引入 `ProjectStorageEnvironment`，统一项目、存储集群、项目组和 Volume/Qtree 的绑定关系，并按项目存储环境提供管理、工作台、汇总和实时趋势能力。

`docs/features/project-storage-environment/design.md` 已按当前绿地实施方案收敛重写；当前分支的实际实施与验收状态以该设计、代码和自动化测试为准。

### 已完成

- 新增 `ProjectStorageEnvironment` 关系模型；Alembic 只保留 root/head `000000000001`，从空库一次创建当前 `14` 张表和 `31` 个索引。`groups.project_environment_id` 从建表起为 `NOT NULL`，不存在重复的 `project_id/storage_cluster_id` 物理列；项目内环境名称、项目与集群组合均保持唯一。
- 新增项目存储环境列表、创建、详情、摘要、实时趋势、更新和删除 API；读操作按超级管理员、项目负责人或 PT 负责人校验项目访问权，写操作要求超级管理员。已绑定项目组的环境拒绝删除。
- 项目组 API 支持按 `project_environment_id` 过滤，并要求写入时选择一个环境以及且仅一个 Volume/Qtree 目标；目标必须属于环境绑定的存储集群，Isilon 环境只允许 Volume。
- 前端完成项目存储环境 CRUD、项目组级联绑定、项目详情工作台和 Dashboard 环境维度接入。项目列表展示环境数量、集群类型和状态统计；工作台按启用环境切换，展示环境摘要、实时趋势和关联项目组，并通过 `environment_id` 保持可分享的当前环境状态；Dashboard 支持项目/环境筛选、环境独立容量展示，并使用 `project_environment_id:group_id` 稳定 key 隔离跨环境同名 Group。
- Usage、Alert 和导出完成环境筛选、环境内 Group 约束与环境列；监控/扩容下游统一解析 Volume/Qtree 目标，备份路径增加环境目录，项目周报按环境分组。
- Celery 存储采集每轮先加载新的、与 ORM session 解耦的标量快照；任务通过稳定 ID 和短会话读取当前数据库绑定，后续按存储集群创建独立 session 和事务。单集群 PostgreSQL 更新提交后再写 QuestDB，QuestDB 写入失败不会回滚已提交的 PostgreSQL 数据。
- Group/User/Project/System 告警、项目周报、单次与批量备份、BPM 和删除流程批量预加载关联并复用当前 ORM 快照；Group TOP20 使用一次窗口查询，`enable_monitoring=false` 的 Group 不进入 Group/User 告警。该口径仅覆盖本次主链路，不代表整个 `celery_tasks` 目录已消除 N+1。
- 采集轮次允许部分集群失败并保留成功集群结果；只有全部集群失败时轮次失败。项目级汇总只在该项目全部启用环境于本轮完整成功时更新，避免部分成功覆盖完整项目统计。
- Isilon 项目组直接绑定 Volume，不再创建或依赖 `name='null'` 的 Qtree；环境汇总按真实 Volume/Qtree/多用户项目组目标去重，多个项目组指向同一目标时只计一次。
- 项目组创建、更新和响应不接受或返回旧 `project_id/storage_cluster_id` 数字字段；保留的项目/集群列表筛选参数通过 `ProjectStorageEnvironment` 关系查询，不做兼容双写。

### 验证状态

- `& 'D:\dev\DiskPulse\.venv\Scripts\python.exe' -m pytest backend\test -q`：通过，`146` 个测试，`41` 个既有弃用 warning。
- `& 'D:\dev\DiskPulse\.venv\Scripts\python.exe' -m coverage run -m pytest backend\test -q; & 'D:\dev\DiskPulse\.venv\Scripts\python.exe' -m coverage report`：通过，`2892` statements、`444` miss，总覆盖率 `85%`。
- migration 独立审计：versions 恰好 `1` 个，`000000000001` 为 root/head；SQLite upgrade 后与 `Base.metadata` 对比无差异，downgrade 后 `0` 张表；PostgreSQL offline upgrade/downgrade DDL、逆序 drop、`heads/history`、`compileall` 和 diff check 通过，核心迁移测试 `13 passed`。
- MySQL 全 `Base.metadata` 编译审计未通过：当前 `14` 张表中 `13` 张因无长度 `String/VARCHAR` 触发 `CompileError`。本次 baseline 仅声明支持 SQLite/PostgreSQL，未满足后端开发标准的默认三方言编译门禁。
- `cd frontend; .\node_modules\.bin\vitest.cmd run --testTimeout=15000`：通过，`30` 个测试文件、`153` 个测试。
- `cd frontend; .\node_modules\.bin\vitest.cmd run --coverage --testTimeout=15000`：通过；`statements 93.47%`、`branches 83.56%`、`functions 82.11%`、`lines 93.47%`。
- `cd frontend; npm run lint`：通过。
- `cd frontend; npm run build:prod`：通过。

### 风险与后续

- 当前项目仍处于初始开发阶段，不实现历史数据回填、字段兼容窗口或 M3；已删除旧 revision 和回填脚本。
- 已使用删除前 revision 的开发数据库不支持原地升级；确认数据可丢弃后重建空库，再执行 `000000000001`。不得伪造 `alembic_version` 接续旧链。
- 未连接真实 PostgreSQL、QuestDB、NetApp 或 Isilon 做端到端验证；外部连接、实际设备返回、QuestDB 表结构和跨库最终一致性仍需在集成环境验收。
- 当前 baseline 未支持 MySQL：全 metadata 编译时 `14` 张表中 `13` 张失败；若后续把 MySQL 纳入部署范围，需要先统一补齐无长度 `String/VARCHAR` 的长度并重新通过三方言门禁。
- 未执行外部浏览器 smoke；当前结果不包含仓库外浏览器交互或 E2E 验收。
- `StoragePulseMonitor` 的结果正确性已有测试覆盖，但尚未按生产数据规模做性能压测；无生产入口的旧 monitor 已删除。
- 当前 `backend/celery_worker.py` 只启用 60 秒一次的 `storages_schedule_fetching_task`；告警、周报和定时备份 beat 条目仍为注释状态，优化后的路径尚未通过真实 Celery beat/worker 调度验收。
- `npm run build:prod` 虽成功，但仍有既有的 `VITE_APP_TITLE` 未定义和 chunk 大于 `500 kB` warning，本次未处理。
- 本次自动化测试覆盖模型、迁移契约、API、前端交互、采集事务和聚合边界，不等同于生产容量数据验收。

## 2026-07-13：项目未使用字段审计与清理

### 已完成

- 审计 `backend/models.py` 的 `14` 个 ORM 模型、`221` 个数据库字段，并追踪后端 CRUD/service/Celery 与前端 `frontend/src` 的生产引用。
- 形成 `docs/tracking/unused-field-audit-2026-07-13.md`：记录 `20` 个无业务读写字段、`4` 个运行时不生效的 QuestDB 重复配置字段和 `1` 个无业务语义的单例配置名称字段。
- 复核 `ProjectStorageEnvironment` 新增字段；身份、绑定、容量、采集状态和最近成功采集时间均有明确链路，未发现可直接删除的环境核心字段。
- 已从 ORM、Pydantic schema 和数据库迁移删除 `20` 个无业务读写字段；备份生命周期继续只使用 `status`。
- 已从 `StorageConf`、配置 API schema 和设置页面删除 `4` 个运行时不生效的 `questdb_*` 字段；QuestDB 连接继续只读取 `backend/config.yml` 的 `database.questdb`。
- 这 `24` 个字段已从当前 ORM 和单一 initial baseline 中移除；没有独立清理 revision、历史数据回填、废弃兼容层或动态重连逻辑。
- `StorageConf.name` 属于单独的无业务语义结构字段，不在本轮指定的两类删除范围内，继续保留。

### 验证状态

- 已通过精确字段搜索核对候选字段的声明、业务读写和前端展示位置。
- 已复核 `backend/appConfig.py`、`backend/questdb/database.py` 和 `backend/dependencies.py`，确认 QuestDB 连接只读取 `config.yml`，不会读取 `StorageConf.questdb_*`。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_backend_schema_contract.py backend/test/test_security_regressions.py backend/test/test_core_api.py -q`：通过，`20` 个测试；其中 baseline 在临时 SQLite 完成 upgrade/downgrade，并通过 PostgreSQL offline DDL 编译检查。MySQL 全 metadata 编译不在通过范围内。
- `cd frontend; npx vitest run test/unit/settings-config.test.js --coverage.enabled=false`：通过，`2` 个测试。
- 最终全量验证：后端 `146 passed`、`41 warnings`，覆盖率 `85%`（`2892` statements、`444` miss）；前端 `30` 个测试文件、`153 passed`，覆盖率 statements `93.47%`、branches `83.56%`、functions `82.11%`、lines `93.47%`。
- `cd frontend; npm run lint`：通过。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads` 和 `history`：通过，唯一 root/head 为 `000000000001`；`compileall -q backend` 通过。
- `cd frontend; npm run build:prod`：通过；仍有既有的 `%VITE_APP_TITLE%` 未定义和大 chunk 警告。
- 尚未在真实 PostgreSQL 空库执行 initial baseline upgrade/downgrade；当前仅完成 SQLite 往返和 PostgreSQL offline DDL 验证。

## 2026-07-13：登录后 profile 请求补齐 Bearer scheme

- 修复前端请求拦截器发送裸 JWT，导致登录成功后 `/users/current/profile` 返回 `401` 的问题。
- 有 token 时统一发送 `Authorization: Bearer <token>`；登录响应和 profile API 契约不变。
- `npx vitest run test/unit/api/support.test.js test/unit/auth-login.test.js`：通过，3 个测试。

## 2026-07-13：LDAP 登录失败日志补齐

### 已完成

- 确认服务账号 STARTTLS、bind 和用户查询正常，`guojianpeng` 可被目录检索到；登录失败发生在用户账号 bind 阶段。
- 用户 STARTTLS 或 bind 被拒绝时记录 LDAP result code/description，异常时仅记录异常类型；日志不包含用户名、DN 或密码。
- LDAP 失败日志改由 `uvicorn.error` 输出，确保开发环境控制台可见。
- 目录查询无匹配用户时补充独立 warning，与用户 bind 被拒绝日志明确区分。
- 登录接口仍统一返回 `401 invalid credentials`，不向客户端泄露认证细节。

### 验证状态

- `..\.venv\Scripts\python.exe -m pytest test\test_auth_ldap.py -q`：通过，7 个测试。

## 2026-07-13：后端运行配置迁移为分类 YAML

### 主题

移除后端应用对 `.env`、`python-dotenv` 和运行时环境变量的依赖，将运行配置统一迁移到按子系统分类的 `backend/config.yml`。

### 已完成

- 新增 PyYAML 配置加载器，支持点分路径读取、显式测试配置、URL 凭据转义、相对密码文件和非法配置快速失败。
- PostgreSQL、QuestDB、Redis、JWT、LDAP、超级管理员、CORS、建表、连接池和 Isilon 缓存均改读 YAML；手工设备检查脚本继续使用环境变量。
- 本地配置迁入被忽略的 `backend/config.yml`，LDAP 使用 STARTTLS，超级管理员为 `guojianpeng`；旧 `development.env`、`test.env` 已移除。
- 新增 `backend/config.example.yml`、`backend/config.test.yml` 和配置契约测试，移除 `python-dotenv` 依赖。
- 同步认证和后端架构文档；登录 API、JWT 响应、前端契约和数据库结构未变。

### 验证状态

- `.\.venv\Scripts\python.exe -m pytest backend\test\test_app_config.py backend\test\test_auth_ldap.py backend\test\test_auth_api.py backend\test\test_security_regressions.py -q`：通过，28 个测试。
- `.\.venv\Scripts\python.exe -m pytest backend\test -q`：通过，42 个测试。
- `.\.venv\Scripts\python.exe -m coverage run -m pytest backend\test -q; .\.venv\Scripts\python.exe -m coverage report`：通过，总覆盖率 `83%`，`backend/appConfig.py` 覆盖率 `93%`。
- `.\.venv\Scripts\python.exe -m compileall -q backend`、`.\.venv\Scripts\python.exe -m pip check`：通过。
- 静态扫描确认除 `backend/scripts/manual_*_check.py` 外，后端 Python 代码不再读取环境变量；活动代码和功能文档不再引用旧 env 配置键。
- 本地 `backend/config.yml` 已验证可加载，验证过程未输出密码或密钥。

### 风险与后续

- 未连接真实 LDAP、PostgreSQL、QuestDB、Redis、NetApp 或 Isilon；外部服务连通性与证书链待部署环境验证。
- `ldap.group_bases` 当前仅保留配置，不参与角色或权限映射。

## 2026-06-30：后端 pytest 迁移与 80% 覆盖率门禁

### 主题

将后端测试入口从 `unittest` 迁移到 `pytest`，补充核心 CRUD 和汇总逻辑测试，并把当前 `.coveragerc` 后端整体覆盖率门禁提升到 `80%`。

### 已完成

- 新增 `pytest.ini`，默认收集 `backend/test` 下的 `test_*.py` 测试。
- 新增 `backend/test/conftest.py`，统一提供内存 SQLite、数据库会话、FastAPI `TestClient`、认证头和 JWT 撤销状态隔离 fixture。
- 将 `backend/test` 下既有测试改为 pytest 函数/测试类，移除 `unittest.TestCase`、`setUp/tearDown` 和 `self.assert*` 断言风格。
- 新增 `backend/test/test_crud_pytest.py`，覆盖项目、用户、aggregate、volume、qtree、group 的 CRUD、过滤排序、树形汇总、实时数据代理和非法字段拒绝。
- 在 `backend/requirements.txt` 中新增 `pytest==9.1.1`，并将 `.coveragerc` 的 `fail_under` 提升到 `80`。

### 验证状态

- `.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`：通过。
- `.\.venv\Scripts\python.exe -m pytest backend\test`：通过，33 个测试。
- `.\.venv\Scripts\python.exe -m coverage run -m pytest; .\.venv\Scripts\python.exe -m coverage report`：通过，总覆盖率 `82%`。
- `.\.venv\Scripts\python.exe -m compileall -q backend`：通过。

### 风险与后续

- 当前 80% 覆盖率口径沿用 `.coveragerc`，仍排除外部设备客户端、QuestDB、Celery、迁移和手工脚本。
- 测试运行仍会输出 SQLAlchemy/Pydantic 迁移类弃用告警，本轮未处理这些生产代码告警。
- 本轮未连接真实 NetApp/Isilon/LDAP/QuestDB 环境，仅验证自动化测试和内存 SQLite 覆盖路径。

## 2026-06-30：后端安全审查问题修复

### 主题

修复后端安全审查中确认的敏感信息泄露、远程命令拼接、动态查询字段、TLS 默认值、异常响应、认证授权、运行时默认值和测试装配问题。

### 已完成

- 新增 `backend/test/test_security_regressions.py`，覆盖配置响应去密、存储集群响应去密、异常响应不泄露内部文本、JWT header 校验、NetApp TLS 默认开启和远程 shell 参数引用。
- `/config/storage` 响应改用 public schema，保留内部 full schema 给服务和更新入参使用。
- `StorageCluster` public 响应不再包含 `storage_password`，创建/更新入参仍允许提交密码。
- 通用异常处理不再把内部异常字符串或 Pydantic `errors` 返回给客户端。
- JWT 解码新增 header `alg=HS256`、`typ=JWT` 校验。
- NetApp/Isilon 客户端默认开启 TLS 证书校验，不再全局屏蔽 `InsecureRequestWarning`。
- 远程文件管理和 NetApp quota 扩容命令对路径、用户名、卷名、Qtree 名和目标名做 shell 参数引用，权限值限制为数字模式。
- QuestDB 动态表前缀、指标列和树图 `value_type` 改为白名单；时间和 id 使用绑定参数。
- 列表排序字段统一走 `utils.query.get_sort_column`，非法字段返回 `400`。
- 后台文件任务不再复用请求 Session，改为任务内创建独立数据库会话。
- CORS 默认收紧为本地开发源，部署可通过 `DISKPULSE_CORS_ORIGINS` 配置。
- 启动日志中的 Postgres/QuestDB URL 改为脱敏摘要；`alembic.ini` 移除硬编码内网账号密码，迁移运行时从 `appConfig` 注入 URL。
- 扩容接口改为 Pydantic schema 入参校验，失败返回 `400`，不再记录原始请求体。
- 核心 API 测试装配补齐主路由认证依赖，并使用默认测试 token。
- `Authorization` 请求头收紧为 `Bearer <token>`；裸 token 不再兼容。
- `/users/logout` 要求有效 Bearer token，并撤销当前 JWT 的 `jti`，登出后复用原 token 会返回 `401`。
- 配置接口以及用户、存储资源、项目、扩容、备份删除/回滚等高风险写操作新增超级管理员依赖，超级管理员来源为 `SUPER_ADMIN_USERNAMES`。
- 邮件模板和任务默认值移除历史产品名、内部域名和个人邮箱；默认站点链接使用本地入口，扩容流程链接未配置时为空。
- NetApp/Isilon 手工集成检查脚本移动到 `backend/scripts/manual_*_check.py`，避免被单元测试收集。
- 主库和 QuestDB 连接池默认值改为保守配置，并支持 `DISKPULSE_DB_*`、`DISKPULSE_QUESTDB_*` 环境变量覆盖。
- Isilon 会话 cookie/CSRF 缓存默认关闭，仅 `DISKPULSE_ISILON_SESSION_CACHE=true` 时启用。
- 请求级数据库会话在异常路径执行 rollback 后再关闭。
- 新增 `docs/standards/domain-terminology.md`，并修正前端标准中的真实样式入口路径。

### 验证状态

- `.\.venv\Scripts\python.exe -m unittest backend.test.test_security_regressions backend.test.test_auth_api`：通过，15 个测试。
- `.\.venv\Scripts\python.exe -m unittest discover -s backend\test -p "test_*.py"`：通过，28 个测试。
- `.\.venv\Scripts\python.exe -m compileall -q backend`：通过。
- 静态扫描确认旧内部域名、个人邮箱、硬编码高连接池、`verify=False` 和 `disable_warnings` 不再存在于后端生产代码；`.dict()` 残留仅为测试中的 `unittest.mock.patch.dict`。

### 风险与后续

- 真实 NetApp/Isilon/LDAP/QuestDB 环境未做端到端连通性验证；TLS 默认开启后，自签名环境需要配置可信 CA 或显式受控降级。
- JWT 撤销列表当前为进程内内存状态；多实例部署需要迁移到 Redis 或数据库等共享存储。
- 未配置 `mail_to` 时，历史默认个人收件人已移除，相关告警邮件会缺少默认收件人并需要部署侧显式配置。

## 2026-06-30：NetApp/Isilon 软限额持久化与展示

### 主题

为配额链路新增软限额采集、持久化、API 暴露、导出和前端展示，保留现有硬限额告警口径。

### 已完成

- `StorageUsage`、`Qtree`、`Volume`、`Group`、`Project` 新增 `soft_limit` 和 `soft_use_ratio` 字段。
- `StoragePulseMonitor` 从 NetApp `space.soft_limit` 和 Isilon `thresholds.soft` 获取软限额，linked Isilon 用户继承 default-user 软限额。
- 项目组、项目汇总和 QuestDB 当前态写入同步携带软限额字段；现有告警任务仍按硬利用率 `use_ratio`。
- 用户用量、项目组、Qtree、Volume 列表新增软限额/软利用率列，硬限额列文案明确为“硬限额/硬利用率”。
- 存储使用导出新增“软限额”“软使用率”列。
- 软限额字段已纳入单一 initial baseline；功能说明见 `docs/features/storage-quota/overview.md`。

### 验证状态

- `.\.venv\Scripts\python.exe -m unittest backend.test.test_storage_soft_quota`：通过。
- `.\.venv\Scripts\python.exe -m unittest backend.test.test_core_api`：通过。
- `cd frontend && npx vitest run test/unit/utils/quota.test.js --coverage.enabled=false`：通过。
- `cd frontend && npx vitest run test/unit/smoke/surface-regression.test.js --coverage.enabled=false`：通过。

### 风险与后续

- 未连接真实 NetApp/Isilon 设备做端到端采集验证，本次通过 mock quota payload 覆盖字段解析。
- 旧增量 revision 已删除；初始开发数据库统一从空库执行 `000000000001`，不支持从旧链升级。
- `docs/standards/domain-terminology.md` 已在后续安全修复中补齐。

## 2026-06-30：后端核心接口测试与覆盖率门禁

### 主题

后端核心逻辑审查、核心 API 测试补齐，以及初版核心后端 `70%+` 覆盖率门禁。

### 已完成

- 新增 `backend/test/test_core_api.py`，使用 FastAPI `TestClient`、内存 SQLite 和最小模型种子覆盖核心接口。
- 覆盖认证保护下的用户列表、项目详情与重复创建拒绝、存储集群 CRUD 和 realtime envelope。
- 覆盖 aggregate、volume、qtree、group、storage usage、storage alerts、storage backup records、large files 的列表、状态校验、导出和关键失败路径。
- 修复 `storage-usages/export/` 的 PDF/Excel `Content-Type` 互换问题。
- 修复 `large-files/export/` 的 `.xlsx` 导出返回 `application/pdf` 的问题。
- 新增 `.coveragerc`，按本次确认的“核心后端”口径排除外部设备客户端、QuestDB、Celery、迁移和手动脚本。
- 在 `backend/requirements.txt` 中补充 `coverage==7.13.0`，并已安装到本地 `.venv` 进行验证。
- 将 NetApp 和 Isilon 手动验证脚本改为读取环境变量，避免真实设备地址、账号和密码进入代码库，并避免自动测试误触外部设备。
- 新增 `docs/overview/latest-features.md` 并更新 `docs/README.md` 索引。

### 验证状态

- `.\.venv\Scripts\python.exe -m unittest backend.test.test_core_api`：通过。
- `.\.venv\Scripts\python.exe -m unittest discover -s backend\test -p "test_*.py"`：通过，14 个测试。
- `.\.venv\Scripts\python.exe -m coverage run -m unittest discover -s backend\test -p "test_*.py"; .\.venv\Scripts\python.exe -m coverage report`：通过，核心后端覆盖率 `73%`。

### 风险与后续

- 覆盖率口径为初版核心后端 `70%+`，未把外部设备客户端、QuestDB、Celery worker、迁移脚本和手动探测脚本纳入门禁。
- 部分 CRUD 和 router 仍输出 Pydantic v2 `dict()` 弃用告警，当前不影响测试通过，后续可单独改为 `model_dump()`。
- `docs/standards/domain-terminology.md` 已在后续安全修复中补齐。
- 当前工作区仍存在与本任务无关的未跟踪前端测试文件，本次未纳入也未回退。

## 2026-06-30：前端清理、结构整理与测试补齐

### 主题

前端冗余代码清理、中度结构整理，以及基于 `Vitest` 的测试体系补齐。

### 已完成

- 删除未接入当前前端入口或路由的历史残留目录：`frontend/src/pages_backup/**`、`frontend/src/pages/storage/**`。
- 删除空文件 `frontend/src/components/form/FormDialog.vue`，并清理未被当前路由使用的重复页面与无效工具文件。
- 抽取共享逻辑到 `frontend/src/utils/time-range.js` 与 `frontend/src/router/support/accessibility.js`，同步收敛重复的查询、时间范围和路由可访问性处理。
- 继续抽取选择器共享逻辑到 `frontend/src/composables/select-model.js`，统一 `modelValue` 归一化、`v-model` 发射和单选/多选值展开处理。
- 将 `ProjectSelect`、`AggregateSelect`、`StorageClusterSelect`、`VolumeSelect`、`GroupSelect`、`QtreeSelect`、`StorageUsageSelect`、`AccountSelect`、`HostsSelect`、`RdUserSelect`、`MailSelect`、`UserMail` 的重复同步状态机改为复用公共 composable，并删除失效的默认回填残留代码。
- 清理明显影响可读性的无用 `import`、调试输出与重复 helper，保持现有页面路径和路由契约不变。
- 在 `frontend/package.json` 中新增 `npm test`、`npm run test:coverage`、`npm run test:watch` 脚本。
- 新增 `frontend/vitest.config.js`、`frontend/test/setup.js`、`frontend/test/helpers/mount.js` 以及覆盖 `utils`、`api`、`composables`、`stores`、`router` 和活跃页面 smoke 的测试用例。
- 新增针对高函数缺口区域的聚焦测试，包括路由懒加载、基础 API 包装、表单对话框事件链和表单选择器搜索/回填行为测试。

### 验证状态

- `cd frontend && npm test`：通过。
- `cd frontend && npm run test:coverage`：通过。
- `cd frontend && npm run build:test`：通过。
- `frontend/src` 当前全局覆盖率结果：
  - `statements`: `91.90%`
  - `branches`: `84.31%`
  - `lines`: `91.90%`
  - `functions`: `71.23%`

### 风险与后续

- 本轮已满足初版全局 `70%+` 覆盖率目标；剩余函数缺口主要集中在图表组件、少量列表页事件处理和部分未细测的表单选择器上，后续可继续按覆盖率报告定点补强。
- 当前 `vitest` 执行期间仍会输出 Sass legacy JS API 弃用告警，不影响本轮测试通过，但后续升级 Sass/Vite 链路时需要单独消化。
- `npm run build:test` 已通过，但打包结果仍提示存在 `500 kB+` chunk，后续如继续整理前端结构，建议结合路由懒加载和手动拆包一起处理。
- 当前工作区仍存在与本任务无关的后端和仓库级未提交改动，本次未回退也未纳入前端交付范围。
- 前端测试说明已新增到 `docs/guides/frontend-testing-guide.md`，后续新增页面或公共模块时应同步补测试。

## 主题

后端 LDAP 登录登出认证、JWT 保护业务 API 和前端登录流程对齐。

## 已完成

- 新增 LDAP directory 查询、LDAP filter 转义、多 user base 搜索和 STARTTLS-before-bind 行为。
- 新增 HMAC-SHA256 JWT 签发与校验；当前安全契约要求 `Authorization: Bearer <token>`。
- 新增 `/storage-pulse/api/users/login`、`/users/logout`、`/users/current/profile`，保持前端 `{ result: ... }` 契约。
- `/storage-pulse/api/**` 除登录和 `OPTIONS` 外默认要求有效 JWT；登出接口同样要求有效 Bearer token。
- 移除前端登录页本地 `superadmin` 绕过，所有账号统一走后端登录接口。
- 新增后端认证测试和前端登录流程测试。
- 同步认证文档、配置示例和依赖声明。

## 未包含

- 未新增数据库字段或 Alembic migration，继续复用 `users.rd_username`。
- 未接入真实 LDAP 做端到端连通性验证；真实环境需配置 `LDAP_SERVER_URL`、bind 凭据、user bases 和 TLS 参数。
- 未处理当前工作区中与本任务无关的既有未提交改动。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test.test_auth_ldap backend.test.test_auth_api
.\.venv\Scripts\python.exe -m unittest discover backend/test
.\.venv\Scripts\python.exe -m compileall -q backend
.\.venv\Scripts\python.exe -m pip check
cd frontend
npx vitest run test/unit/auth-login.test.js --coverage.enabled=false
npm test -- --coverage.enabled=false
```
