# 近三日前后端代码审查与修复交付

## 范围

- 核验本地与远端开发分支是否均已进入 `main`。
- 审查自 `2026-07-17 00:00:00 +08:00` 起的前后端提交。
- 按严重度逐项执行 TDD 修复并保持问题级提交边界。
- 同步功能文档、会话记录，并将重复问题沉淀为项目约束或 skill。

## 当前状态

已完成。本地分支、远端分支均已是 `main` 的祖先，无需产生空合并；近三日代码问题已按严重度完成问题级提交。

## 分支核验

- 审查开始时 `main` 为 `663e37f`，`origin/main` 为 `5667b81`，本地 `codex/fix-group-update-validation` 与 `main` 同点。
- `git merge-base --is-ancestor origin/main main` 与 `git merge-base --is-ancestor codex/fix-group-update-validation main` 均返回 0。
- 远端仅存在 `origin/main`；开发分支位于独立 worktree，已合入但按本次范围未删除分支或 worktree。

## 审查范围与结论

- 时间窗口：`2026-07-17 00:00:00 +08:00` 至本次审查。
- 审查基线：`585de78cb0fc204472db7f1c1d3d56fcc6727cd1`。
- 覆盖 423 个可达提交、353 个前后端变更文件，约 `+43,708/-3,264`。
- 重点复核：AI 对话与配额确认、预测关联事件、容量预测治理、项目权限与配额、容量单位与迁移、前端路由/共享组件/Mock 和依赖供应链。
- 安全复核未发现新增 secret、注入或 `v-html` 绕过；HTML 渲染继续经 DOMPurify。依赖审计发现的 2 个严重、33 个高危漏洞已清零。

## 修复清单与提交

| 严重度 | 问题 | 处理 | 提交 |
| --- | --- | --- | --- |
| 高 | 用户目录配额 Router 复制“仅超级管理员”预检，错误拒绝项目负责人 | 先补拒绝复现测试，移除重复预检，由 Service 执行项目权限 | `40a1dd3`、`3ecdccf` |
| 高 | 前端依赖含 2 个严重、33 个高危漏洞，pnpm 被误列运行时依赖 | 建立安全门禁，升级工具链和直接依赖，增加安全 override/patch | `0adaa44`、`68c8483` |
| 中 | `ElLink` Boolean prop 传入字符串 `"never"` | 改为 `:underline="false"` | `1e73647` |
| 中 | 事件详情标题后存在全局禁止的描述性副标题 | 删除副标题，保留 Tooltip 中的必要解释 | `c9e683f` |
| 中 | 共享组件、Pinia、认证工具变化后测试替身过时 | 同步公共 stub、插件、mock 和排序预期 | `eeffcf0` |
| 中 | 容量、迁移、嵌套响应和配额测试仍断言旧契约 | 按当前 schema、单位、head 和角色矩阵统一更新 | `b318eb5` |
| 低 | 预测事件 Router 直接导入 ORM User 并查询 | 加分层门禁，将操作者查询移入 Service | `63bd022`、`3165341` |
| 低 | 静态源码正则绑定旧 CSS、赋值语句和 mock 形态 | 改为 payload、事件、导航和可见结果断言 | `f339817` |
| 低 | 异步 `resolves` 断言未 await | 显式等待 Promise 断言 | `cf35c24` |
| 低 | 全量用例通过但 Functions 覆盖率为 78.95% | 增加 API、权限、审计、表单和配额行为测试，恢复至 81.38% | `7057c5d` |

## 改动文件

- 后端实现：`backend/routers/storage_usage.py`、`backend/routers/forecast_incidents.py`、`backend/services/forecastIncidentService.py`。
- 后端测试：容量预测治理与迁移、核心 API、项目组标签、项目 RBAC、项目权限和 Router 分层共 8 个测试文件。
- 前端实现与依赖：`frontend/package.json`、`frontend/pnpm-lock.yaml`、两个 lodash patch、`AccessibleResourceLink.vue`、`IncidentDetailDrawer.vue`。
- 前端测试：API、共享页面、路由、配额、审计、标题策略、容量预测、RBAC、smoke 等 21 个测试文件。
- 文档：前后端标准、本会话交付/错误记录和 7 个错误事实/索引条目。

## 验证

- `backend`：`.venv\Scripts\python.exe -m pytest backend/test -q`，661 passed。
- `frontend`：`pnpm run test:coverage -- --reporter=dot`，100 files / 629 tests passed；Statements 95.79%、Branches 82.94%、Functions 81.38%、Lines 95.79%。
- `frontend`：`pnpm run lint`、`pnpm run build:test` 均通过。
- 依赖：`pnpm run audit:high` 通过，高危/严重为 0；剩余 1 个低危和 5 个中危。
- Python：`.venv\Scripts\python.exe -m compileall backend`、`.venv\Scripts\python.exe -m pip check` 通过。
- Git：`git diff --check` 通过；提交前后均按文件范围核对 staged 内容。

## 未验证范围和风险

- 未执行真实浏览器人工操作、真实 LDAP/Redis/QuestDB/存储设备和生产部署验证；本次依赖自动化契约、构建和静态审查。
- 前端安全审计仍有 1 个低危、5 个中危传递依赖；高危/严重已清零，剩余项需要后续结合上游兼容性升级。
- 全量前端测试仍会输出部分既有负路径日志、jsdom 跨域网络噪声和 smoke 无效 prop 警告，但 629 个断言与覆盖率门禁均通过；这些噪声未作为本次代码审查发现扩展处理。
- `docs/tracking/sessions/2026-07-20-user-quota-adjustment-feedback/` 是本次开始前已有的未跟踪目录，未修改、未暂存、未提交。
