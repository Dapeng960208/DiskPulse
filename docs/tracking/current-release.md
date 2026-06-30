# 当前交付记录

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
- `docs/standards/domain-terminology.md` 仍缺失，属于既有规范引用缺口。
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

### 验证状态

- `cd frontend && npm test`：通过。
- `cd frontend && npm run test:coverage`：通过。
- `cd frontend && npm run build:test`：通过。
- `frontend/src` 当前全局覆盖率结果：
  - `statements`: `89.70%`
  - `branches`: `81.06%`
  - `lines`: `89.70%`
  - `functions`: `47.30%`

### 风险与后续

- 本轮已满足初版全局 `70%+` 覆盖率目标，但 `functions` 指标仍低于 `70%`，后续需要通过更细粒度的页面交互和事件处理测试继续抬升。
- 当前 `vitest` 执行期间仍会输出 Sass legacy JS API 弃用告警，不影响本轮测试通过，但后续升级 Sass/Vite 链路时需要单独消化。
- `npm run build:test` 已通过，但打包结果仍提示存在 `500 kB+` chunk，后续如继续整理前端结构，建议结合路由懒加载和手动拆包一起处理。
- 当前工作区仍存在与本任务无关的后端和仓库级未提交改动，本次未回退也未纳入前端交付范围。
- 前端测试说明已新增到 `docs/guides/frontend-testing-guide.md`，后续新增页面或公共模块时应同步补测试。

## 主题

后端 LDAP 登录登出认证、JWT 保护业务 API 和前端登录流程对齐。

## 已完成

- 新增 LDAP directory 查询、LDAP filter 转义、多 user base 搜索和 STARTTLS-before-bind 行为。
- 新增 HMAC-SHA256 JWT 签发与校验，兼容 `Authorization: <token>` 和 `Authorization: Bearer <token>`。
- 新增 `/storage-pulse/api/users/login`、`/users/logout`、`/users/current/profile`，保持前端 `{ result: ... }` 契约。
- `/storage-pulse/api/**` 除登录、登出和 `OPTIONS` 外默认要求有效 JWT。
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
