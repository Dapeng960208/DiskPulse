# 错误记录

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
