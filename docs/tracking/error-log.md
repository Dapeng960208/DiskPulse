# 错误记录

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
