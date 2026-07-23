# AI 模型推理能力安全合入记录

- 会话：`2026-07-23-ai-model-reasoning-effort-merge`
- 状态：已完成，待将已验证的合并提交快进到 `main`
- 源分支：`codex/ai-model-reasoning-effort`
- 临时集成分支：`codex/ai-model-reasoning-effort-integration`

## 合并处理

- 主工作区存在未提交的 `frontend/src/pages/incident/IncidentCenterPage.vue` 修改；临时集成 worktree 从 `main` 创建并完成合并，未改写该文件。
- `ai_config_service` 同时保留默认聊天模型保护与事件 AI 处置候选模型引用保护。
- 前端 mock runtime 同时保留 `aiPlatformSettings` 和 `incidentAiSettings`。
- 主分支已占用 Alembic `000000000020`，AI 推理迁移安全重编号为 `000000000022_ai_reasoning_effort.py`，并接在 `000000000021_incident_ai_agent.py` 之后；迁移链契约同步更新为 `019 → 020 → 021 → 022`。

## 验证

- 后端聚焦回归：289 passed，覆盖 AI 推理、AI 工具权限、集群健康分析、预测/Incident、事件 AI 处置和迁移链。
- 临时 SQLite 最小旧表执行 `000000000021 → 000000000022 → 000000000021`，通过。
- 前端 AI 与事件中心聚焦单测：8 files / 64 tests passed。
- `pnpm run lint` 通过；`pnpm run build:test` 通过，仅有既有 `VITE_APP_TITLE` 未定义与大 chunk 警告。

## 未验证范围与风险

- 真实 Provider、Redis、数据库和不同角色的完整 SSE 对话仍需部署环境验收。
- 完整 Alembic 从空 SQLite 库升到 head 仍受既有 `000000000019` PostgreSQL interval SQL 阻断；最后一段迁移链已独立验证。
