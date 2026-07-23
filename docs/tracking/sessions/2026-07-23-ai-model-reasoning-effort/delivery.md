# AI 模型推理强度自动适配交付记录

- 会话：`2026-07-23-ai-model-reasoning-effort`
- 状态：已实现，存在非 AI 前端全量覆盖率基线阻塞
- 分支：`codex/ai-model-reasoning-effort`
- 工作区：`.worktrees/ai-model-reasoning-effort`
- 范围：默认聊天模型、每消息推理设置、模型能力发现、Provider 原生参数适配，以及管理端和聊天端交互。

## 已完成

- 新增平台级默认聊天模型；未显式传 `model_id` 的新会话使用默认模型，没有默认模型时返回明确配置错误；默认模型不能被直接停用、取消聊天权限或删除。
- 新增统一 `reasoning_control` 能力契约和每消息 `reasoning`；能力按动态元数据、官方目录、未知状态的优先级解析，获取失败时只允许 `auto`。
- 扩展 OpenAI、OpenRouter、Ollama、Claude API、Claude Code、DeepSeek、通义千问、豆包、智谱 GLM、Kimi、MiniMax、百度千帆和腾讯混元适配，保持原生强度或开关语义。
- Claude Code 固定依赖 `claude-agent-sdk==0.2.123`，仅允许 DiskPulse MCP 工具，禁用文件、Shell 等内置工具，复用当前用户权限、项目隔离、配额确认、SSE 取消和审计链路。
- AI 中心增加 Provider 预设、默认模型配置、能力状态、能力来源和手动刷新；聊天页增加按模型能力变化的推理强度或思考模式选择。
- 审计记录请求值、解析后的控制类型和实际发送值；不持久化或展示 Provider 返回的思维链内容。
- 本期不包含独立“速度”控制，也不增加管理员默认推理档位。

## 验证结果

- 后端 AI 聚焦与覆盖率：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m coverage run --source=services.ai_reasoning_service,services.ai_client,services.ai_config_service,services.ai_chat_service,services.claude_code_adapter -m pytest test/test_ai_reasoning_effort_red.py test/test_ai_services.py test/test_ai_platform.py test/test_correlation_and_ai_admin_audit.py -q`，159 passed；`coverage report --fail-under=85`，总覆盖率 85%。
- 后端迁移契约：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test/test_vendor_event_definitions_migration.py test/test_vendor_event_definitions_official_expansion_migration.py -q`，8 passed。
- 安全合并后，AI 推理迁移编号调整为 `000000000022`，接在既有 `000000000021` 之后；临时 SQLite 最小旧表已验证 `000000000021 → 000000000022 → 000000000021` 升降级通过。
- 前端 AI 聚焦测试：`pnpm exec vitest run test/unit/ai-reasoning-pages.test.js test/unit/ai-api-stream.test.js test/unit/mock-ai-reasoning.test.js test/unit/ai-pages.test.js test/unit/ai-platform.test.js --coverage.enabled=false`，5 files / 54 tests passed。
- 前端静态与打包：`pnpm run lint` 通过；`pnpm run build:test` 通过，仅保留既有 `VITE_APP_TITLE` 未定义与大 chunk 警告。
- 格式检查：`git diff --check` 通过。

## 未通过或未验证

- `pnpm run test:coverage` 未通过，失败位于既有非 AI 前端基线测试：页面矩阵 27/30、列表动作权限 4 个断言、存储集群健康分析 2 个断言，以及 `CrudApi extends BaseApi` 异步 rejection；本次 AI 聚焦测试不受影响。
- 没有使用真实 OpenAI、OpenRouter、Ollama、Claude、Claude Code 或国内 Provider 凭据做外部联调；Provider 能力动态刷新和真实流式协议仍需部署环境验收。
- 完整 Alembic 从空库升到 head 的 SQLite 验证仍受既有 `000000000019` PostgreSQL interval SQL 阻断；本次已单独验证当前链路最后一步 `000000000021 → 000000000022 → 000000000021`。

## 风险与确认项

- Provider 模型能力和请求协议会随上游变化；动态发现失败时采用关闭式降级，只允许 `auto`，需要通过能力刷新恢复。
- 国内 Provider 同时存在强度、开关、预算和不可调模型；前后端必须以 `reasoning_control` 为唯一契约，不能自行近似映射。
- Claude Code Agent SDK 的真实流式取消、进程内 MCP 工具桥接和 API Key 环境隔离需要部署环境验证。
