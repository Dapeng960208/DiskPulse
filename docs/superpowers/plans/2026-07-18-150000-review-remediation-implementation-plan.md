# 审查问题修复实施计划

- 批准时间：2026-07-18（用户已明确要求实施；当前环境不提供原生选择对话框，按推荐方案执行）
- 设计依据：[审查问题修复设计](../specs/2026-07-18-review-remediation-design.md)

## 顺序与检查点

1. 为 MySQL 外键删除补 RED 迁移 SQL 断言，提交 `test(migration)`；实现外键删除与注释，运行 GREEN，提交 `fix(migration)`。
2. 为成员默认首页范围补 RED 前端契约测试，提交 `test(frontend)`；实现安全的成员初始状态与注释，运行 GREEN，提交 `fix(frontend)`。
3. 为 Celery 重复投递补 RED 测试，提交 `test(celery)`；实现租约领取与注释，运行 GREEN，提交 `fix(celery)`。
4. 为遥测失败错误码补 RED 测试，提交 `test(telemetry)`；更新终态约束和服务写入并注释，运行 GREEN，提交 `fix(telemetry)`。
5. 为 AI 未知工具补 RED 流测试，提交 `test(ai)`；实现可恢复完成事件与注释，运行 GREEN，提交 `fix(ai)`。
6. 为图表异步卸载和成员操作失败补 RED 前端测试，分别修复并提交对应 GREEN `fix(frontend)` 提交。
7. 运行汇总验证；编写审查复盘表、更新 tracking 文档并提交 `docs(review)`。
8. 将修复分支快进合入 `main`；保留并提交主工作区已有遗留内容，确认所有 worktree 清洁。

## 验证

- 后端：相关 `pytest` 文件、Alembic SQLite 运行及 SQLite/PostgreSQL/MySQL 离线 SQL 编译。
- 前端：相关 Vitest 文件、全量 Vitest 覆盖率门禁、生产构建。
- Git：每次提交前运行 `git diff --check` 与暂存清单检查；最终确认 `git status --short --branch` 无输出。
