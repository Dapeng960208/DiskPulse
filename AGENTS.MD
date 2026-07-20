## 1. 必读顺序

- 任何任务：先读 `docs/standards/documentation/documentation-standard.md`、`docs/standards/git/git-commit-standard.md`，再按 `docs/standards/documentation/development-reading-guide.md` 选择实现层规范与功能专题。
- 前端任务：读 `docs/standards/frontend/frontend-design-standard.md` 和目标功能目录中的事实文档；后端任务读 `docs/standards/backend/backend-development-standard.md` 和目标功能目录中的事实文档。
- 涉及模型、查询、索引、迁移、QuestDB 或 Redis 数据边界：再读 `docs/standards/database/database-development-standard.md`。
- AI 功能：必须先定位 `docs/features/ai/<功能>/`。开发 AI 后端时，至少读后端规范、该功能的 `overview.md` 与 `backend.md`；开发 AI 前端时，至少读前端规范、该功能的 `overview.md` 与 `frontend.md`。涉及 AI 数据模型或迁移时再读数据库规范。
- 涉及产品术语、资源名称、权限、指标或用户文案：读 `docs/standards/documentation/domain-terminology.md`。
- 文档命名/放置：读 `docs/standards/documentation/document-naming-convention.md`。
- 遇到可复现错误：按 `docs/standards/documentation/development-error-summary.md` 记录。

## 2. 核心原则

- 复杂变更先说明假设、成功标准、依赖、风险和取舍；高影响歧义必须先问。
- 只做当前任务需要的最小改动；不做无关重构、格式化或 speculative fallback。
- 尊重现有架构、命名、目录和测试风格。
- 任何功能、接口、配置、权限、数据库、部署、测试入口或用户可见变化，都要同步 `docs/`。
- 结果必须可验证；未验证的内容不能描述为完成。

## 3. 边界与安全

- 不回退用户已有改动；提交前必须区分当前任务改动和既有未提交改动。
- 多主题需求先分类，按主题分别处理和验证。
- 禁止硬编码真实 secret、token、密码、生产地址和个人凭据。
- 输入必须校验；认证、授权、项目隔离、CSRF/XSS/注入边界不能放宽。
- 用户可见错误要友好，服务端日志保留必要上下文但不得泄露敏感信息。

## 4. 测试策略

- 任务修复或者新增行为必须使用 /tdd-workflow：先补失败测试，再实现，再验证。。
- 小问题修复只跑改动文件或影响模块的聚焦测试，不把全量测试当作日常默认命令。

## 5. Windows 中文 Markdown
- 当前主要开发环境是 Windows + 中文 Markdown；读取中文 `.md` 文件时禁止裸用 `Get-Content`。
- 必须使用 `Get-Content -Encoding UTF8 path\to\file.md`。
- 如仍乱码，先设置 `[Console]::InputEncoding`、`[Console]::OutputEncoding` 和 `$OutputEncoding` 为 UTF-8。
- 仍有问题时，使用 `[System.IO.File]::ReadAllText(<path>, [System.Text.UTF8Encoding]::new($false))`。

## 6. 交付口径

- 最终说明列出改动文件、验证命令、未验证范围和风险。
- 每个开发会话在 `docs/tracking/sessions/<session-id>/` 下维护 `delivery.md` 与 `errors.md`；会话目录名使用 `YYYY-MM-DD-<task-slug>`。
- 可复现错误按 `docs/tracking/README.md` 先归类到 `docs/tracking/errors/<category>/<error-slug>.md`，再更新 `docs/tracking/errors/error-index.md` 的出现次数和排序；同类错误每实际出现一次计数加一。
