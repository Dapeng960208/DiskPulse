## 1. 必读顺序

- 任何任务：读 `docs/standards/documentation-standard.md`、`docs/standards/domain-terminology.md`。
- 后端任务：再读 `docs/standards/backend-development-standard.md` 和 `docs/standards/frontend-design-standard.md`。
- 文档命名/放置：读 `docs/standards/document-naming-convention.md`。
- 遇到可复现错误：按 `docs/standards/development-error-summary.md` 记录。
- 需要提交：按 `docs/standards/ai-development-standard.md` 执行。

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
- 可复现错误写入 `docs/tracking/error-log.md`。
- 工作进展、阻塞和交付状态写入 `docs/tracking/current-release.md`。
