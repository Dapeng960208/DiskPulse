# AI 开发与 Git 规范（快速版）

本规范用于 AI 提交代码或文档前快速确认边界、命令和交付口径。

## 1. 任务边界

- 多个需求先分类，按主题分别处理、验证和提交。
- 高影响歧义必须先问；能从代码、文档、配置确认的事实优先自行查证。
- 不混入无关改动，不回退用户已有未提交改动。
- 结束时必须说明改动范围、验证范围、未验证风险。

## 2. 提交前检查

```powershell
git status --porcelain
git diff --check
```

- 提交前必须检查工作区。
- 只暂存当前主题文件，优先 `git add <path>`，避免 `git add .`。
- 工作区有其他未提交改动时，必须确认哪些纳入本次提交。

## 3. 提交信息

格式固定：

```text
type(scope): subject
```

- `type` 常用：`feat`、`fix`、`docs`、`test`、`refactor`、`chore`、`ci`。
- `scope` 写真实范围，例如 `frontend`、`backend`、`docs`、`auth`。
- `subject` 用英文，简短说明核心意图。

## 4. 测试与验证

- 小问题修复跑改动文件或影响模块的聚焦测试。
- 新增功能、高风险共享改动、发布/合并前交付或开发者明确要求时，跑全量测试和覆盖率门禁。
- 测试无法执行时，在最终说明和 `docs/tracking/current-release.md` 写明原因、未验证范围和风险。

## 5. 临时文件

- 本地调试日志、一次性截图、临时导出和验证产物统一放到仓库根 `.tmp/`，不要散落到 `frontend/`、`backend/` 或 `docs/` 源目录。
- 临时文件命名统一使用 `<tool>-<topic>-<timestamp>.<ext>`，例如 `.tmp/playwright-user-workspace-20260615-091500.png`。
- 需要长期保留或纳入交付的文件不得放在 `.tmp/`；应按正式文档、资源或测试资产目录归档。

## 6. 网络或 push 失败

- 网络不可用时仍应完成本地 commit，保证可追溯。
- 可复现失败写入 `docs/tracking/error-log.md`。
- 影响交付节奏时，在 `docs/tracking/current-release.md` 记录“已本地提交，待 push”。
