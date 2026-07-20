# 当前交付记录

本文只记录仍在进行的交付、部署前风险和本轮验证；已完成能力见[当前能力](../overview/product/current-capabilities.md)。

## 2026-07-20：导航信息架构调整

### 已完成

- 根导航隐藏项目组和用户目录；项目详情 `/project/:id` 集中展示容量概览、项目组、用户目录、成员与权限和项目审计，旧列表与详情深链继续有效。
- 新增一级“容量预测”列表 `/capacity-predictions`；最终预测接口在数据库分页前按当前资源归属和项目权限过滤，排除删除资源，并批量合并当前页候选结果。
- 用户目录详情新增配额历史、容量预测最终结果、关联事件和告警页签；预测发布关闭时，本项目成员仍可读取有权限的关联事件。
- 项目组、用户目录和最终预测三个分页视图只接受最新请求结果；候选生效时模型版本优先显示 `input_quality.candidate_version`。
- Mock 与真实服务对齐分页、项目过滤、发布可见性和关联事件权限边界。
- “系统管理 → 存储集群”调整为无组件菜单分组，包含集群列表、容量池、存储空间和 Qtree（NetApp）；原 URL 与 API 不变。

### 验证状态

- TDD 检查点为 `99641ce`、`71fae61`、`98880b6`，GREEN 功能提交为 `3ec04d3`；新增回归均先复现目标缺陷再通过。
- 后端容量预测治理与事件中心组合：`59 passed`；Python `compileall` 通过。
- 前端任务影响面：`15 files / 89 passed`；Mock 文件：`20 passed`。
- `pnpm test` 与 `pnpm run test:coverage` 均为 `87 files / 557 passed / 11 failed`；11 条是 `main` 已复现的既有测试债务，本任务测试无剩余失败。覆盖率命令因测试失败未输出最终汇总，不能宣称覆盖率门禁通过。
- `pnpm run lint`、`pnpm run build:prod` 和 `git diff --check` 通过；构建保留既有 `%VITE_APP_TITLE%` 未定义和大 chunk 警告。
- 内置 Browser 验证 `/capacity-predictions`、`/project/1` 及项目内“用户目录”页签正常渲染和交互；控制台仅有既有 Element Plus 废弃 API warning。

### 风险与待验证范围

- `390px` 下应用壳仍有约 `39px` 页面级横向溢出，属于既有响应式问题，不在本轮信息架构最小改动内。
- 未连接真实 PostgreSQL、QuestDB、Redis、Celery 或存储设备执行部署联调；SQLite 已执行查询，PostgreSQL 仅完成方言编译验证。
- 前端全量与覆盖率仍受 11 条既有测试债务阻塞，需独立任务恢复全绿门禁。

## 2026-07-19：文档分类重组

### 已完成

- 延续既有精简边界：历史计划、一次性设计、实施复盘、过期迁移记录和不再适用的工具流程不恢复为当前事实文档。
- 文档统一为概览、规范、功能专题、指南和跟踪五类；功能专题使用 `docs/features/<领域>/<功能>/`，规范按前端、后端、数据库、文档和 Git 分类。
- 补齐产品、系统、前端和数据库概览，并更新 `AGENTS.md` 与开发阅读矩阵。

### 验证状态

- 功能文档和规范文档均位于新的一级、二级目录；本地相对链接已扫描。
- `cd frontend && pnpm exec vitest run test/unit/heading-subtitle-policy.test.js --coverage.enabled=false` 通过（2 个测试）。
- `git diff --check` 通过。

### 风险

- 本节只调整文档、索引和开发阅读约束；历史材料仍可通过 Git 历史追溯，不作为当前事实来源。
