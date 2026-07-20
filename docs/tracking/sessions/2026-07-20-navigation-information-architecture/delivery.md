# 开发跟踪记录：导航信息架构调整

- 会话：`2026-07-20-navigation-information-architecture`
- 状态：已交付
- 范围：项目上下文导航、一级容量预测、用户目录关联数据和存储集群二级菜单。

已完成能力见[当前能力](../../../overview/product/current-capabilities.md)。

## 已完成

- 根导航隐藏项目组和用户目录；项目详情 `/project/:id` 集中展示容量概览、项目组、用户目录、成员与权限和项目审计，旧列表与详情深链继续有效。
- 新增一级“容量预测”列表 `/capacity-predictions`；最终预测接口在数据库分页前按当前资源归属和项目权限过滤，排除删除资源，并批量合并当前页候选结果。
- 用户目录详情新增配额历史、容量预测最终结果、关联事件和告警页签；预测发布关闭时，本项目成员仍可读取有权限的关联事件。
- 项目组、用户目录和最终预测三个分页视图只接受最新请求结果；候选生效时模型版本优先显示 `input_quality.candidate_version`。
- Mock 与真实服务对齐分页、项目过滤、发布可见性和关联事件权限边界。
- “系统管理 → 存储集群”调整为无组件菜单分组，包含集群列表、容量池、存储空间和 Qtree（NetApp）；原 URL 与 API 不变。
- TDD 检查点为 `99641ce`、`71fae61`、`98880b6`，GREEN 功能提交为 `3ec04d3`；文档分类合并提交为 `02fa251`，本地 `main` 已快进到该提交。

## 验证

- 后端容量预测治理与事件中心组合：`59 passed`；Python `compileall` 通过。
- 前端任务影响面：`15 files / 89 passed`；合并文档分类后组合为 `16 files / 91 passed`；Mock 文件为 `20 passed`。
- `pnpm test` 与 `pnpm run test:coverage` 均为 `87 files / 557 passed / 11 failed`；11 条是 `main` 已复现的既有测试债务，本任务测试无剩余失败。覆盖率命令未输出最终汇总，不能宣称覆盖率门禁通过。
- `pnpm run lint`、`pnpm run build:prod`、Markdown 相对链接扫描和 `git diff --check` 通过；构建保留既有 `%VITE_APP_TITLE%` 未定义和大 chunk 警告。
- 内置 Browser 验证 `/capacity-predictions`、`/project/1` 及项目内“用户目录”页签正常渲染和交互；控制台仅有既有 Element Plus 废弃 API warning。

## 未验证范围与风险

- 未连接真实 PostgreSQL、QuestDB、Redis、Celery 或存储设备执行部署联调；SQLite 已执行查询，PostgreSQL 仅完成方言编译验证。
- `390px` 下应用壳仍有约 `39px` 页面级横向溢出，属于既有响应式问题。
- 前端全量与覆盖率仍受 11 条既有测试债务阻塞，需独立任务恢复全绿门禁。
