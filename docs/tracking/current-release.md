# 当前交付记录

## 2026-06-30：前端体验、可访问性与性能拆包

### 主题

落实前端审查计划，围绕 DiskPulse 管理后台的设计系统、公共组件可访问性、图表加载、页面文案和构建拆包做聚焦改造。

### 已完成

- 新增前端审查合同测试，覆盖应用壳折叠按钮、主题切换、筛选网格、表格错误态/密度、路由术语、ECharts 入口和 Vite 拆包。
- 应用壳侧栏折叠控件改为语义化按钮，补充 `aria-expanded`、`aria-controls`、`aria-label` 和 `focus-visible`。
- `ThemeSwitch` 补充 `aria-label`、`aria-pressed`，恢复 `prefers-reduced-motion` 判断，不再因浏览器不支持 View Transition 输出错误日志。
- `GridContainer`、`QueryForm`、`DataTable` 增强响应式和状态表达，表格支持统一错误态与 `compact` 密度。
- 图表组件改为通过 `frontend/src/lib/echarts.js` 懒加载 ECharts，并复用 `useEchartsChart` 管理初始化、resize 和销毁。
- 概览页、实时详情页新增页面标题、数据范围或最近刷新信息。
- 路由标题和登录页 fallback 文案按 DiskPulse 存储监控术语统一。
- `vite.config.js` 新增 Vue、Element Plus、ECharts 手动拆包配置。
- 新增 `docs/standards/domain-terminology.md`，并修正前端规范中的实际技术栈、样式入口和组件目录说明。

### 验证状态

- `cd frontend && npx vitest run test/unit/frontend-audit-contract.test.js test/unit/frontend-audit-static.test.js test/unit/router/routes.test.js --coverage.enabled=false`：通过。
- `cd frontend && npm run lint`：通过。
- `cd frontend && npm test`：通过，`25` 个测试文件、`121` 个测试。
- `cd frontend && npm run test:coverage`：通过，语句覆盖率 `92.43%`、分支覆盖率 `83.22%`、函数覆盖率 `72.58%`、行覆盖率 `92.43%`。
- `cd frontend && npm run build:test`：通过，主入口 `assets/index-757e3052.js` 为 `31.67 kB`、gzip `8.43 kB`；`echarts`、`element-plus`、`vue-vendor` 和通用 `vendor` 已拆分为独立 chunk。
- Playwright 浏览器烟测：`http://127.0.0.1:5173/login` 在 `375px`、`768px`、`1440px` 视口可渲染；`http://127.0.0.1:5173/` 可渲染概览页骨架和新标题，未接后端时仅出现预期 API `404`。

### 风险与后续

- 未连接真实后端和真实存储设备进行端到端页面验收；本轮验证以组件合同、静态合同、单测、lint 和构建为准。
- 图表视觉细节保持现有图形和数据契约，仅收敛加载入口、生命周期和颜色来源。
- `npm run build:test` 仍保留 Vite 的 `%VITE_APP_TITLE%` 未定义提示和大 vendor chunk 提示；主入口 gzip 已降到规范目标内，后续可继续按业务路由拆页级 chunk。
- 当前改造在独立 worktree `D:\dev\worktrees\DiskPulse\frontend-audit-implementation` 上完成，未回退主工作区既有未提交改动。

## 2026-06-30：NetApp/Isilon 软限额持久化与展示

### 主题

为配额链路新增软限额采集、持久化、API 暴露、导出和前端展示，保留现有硬限额告警口径。

### 已完成

- `StorageUsage`、`Qtree`、`Volume`、`Group`、`Project` 新增 `soft_limit` 和 `soft_use_ratio` 字段。
- `StoragePulseMonitor` 从 NetApp `space.soft_limit` 和 Isilon `thresholds.soft` 获取软限额，linked Isilon 用户继承 default-user 软限额。
- 项目组、项目汇总和 QuestDB 当前态写入同步携带软限额字段；现有告警任务仍按硬利用率 `use_ratio`。
- 用户用量、项目组、Qtree、Volume 列表新增软限额/软利用率列，硬限额列文案明确为“硬限额/硬利用率”。
- 存储使用导出新增“软限额”“软使用率”列。
- 新增 Alembic migration `f4b2c8d9e701_add_soft_quota_fields.py` 和功能文档 `docs/features/storage-quota/overview.md`。

### 验证状态

- `.\.venv\Scripts\python.exe -m unittest backend.test.test_storage_soft_quota`：通过。
- `.\.venv\Scripts\python.exe -m unittest backend.test.test_core_api`：通过。
- `cd frontend && npx vitest run test/unit/utils/quota.test.js --coverage.enabled=false`：通过。
- `cd frontend && npx vitest run test/unit/smoke/surface-regression.test.js --coverage.enabled=false`：通过。

### 风险与后续

- 未连接真实 NetApp/Isilon 设备做端到端采集验证，本次通过 mock quota payload 覆盖字段解析。
- 当前工作区已有 `.gitignore` 修改和多份 `backend/migrate/versions/*` 删除，本次未回退也未纳入修复；新增 migration 的 `down_revision` 接到 Git 中既有链路末端 `a1d670c60836`。
- `docs/standards/domain-terminology.md` 仍缺失，属于既有规范引用缺口。

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
