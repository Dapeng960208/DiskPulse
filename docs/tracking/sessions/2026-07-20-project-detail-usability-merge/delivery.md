# 项目详情可用性主分支合并交付

## 范围

- 将 `codex/project-detail-usability` 的 4 个已验证提交合入本地 `main`。
- 保留 `main` 既有的项目成员自动只读权限、AI 历史能力和 QuestDB 遥测相关更新。

## 当前状态

已完成：合并提交已创建，已合入的功能工作区和本地分支均已删除。

## 验证

- `cd frontend && npx vitest run test/unit/project-context-tabs.test.js test/unit/project-disk-usage.test.js test/unit/project-storage-distribution.test.js test/unit/project-members-tab.test.js test/unit/project-detail-breadcrumbs.test.js test/unit/utils/breadcrumbs.test.js test/unit/stores/breadcrumbs.test.js test/unit/chart-coverage-gaps.test.js test/unit/mock-runtime.test.js --coverage.enabled=false`：9 文件、51 项通过。
- `git diff --check`：通过。
- `git worktree list --porcelain`：仅保留主工作区；`codex/project-detail-usability` 已删除。

## 安全措施

- 合并前的 `main` 未提交代码和未跟踪文件已保存到名为 `codex: safeguard main before project-detail-usability merge` 的 stash；为避免覆盖合并结果，未自动恢复。
