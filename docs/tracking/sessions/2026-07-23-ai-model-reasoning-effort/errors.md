# AI 模型推理强度自动适配错误记录

## 已归类错误

- [前端全量与覆盖率曾保留既有失败](../../errors/frontend/baseline-test-debt.md)：`pnpm run test:coverage` 被非 AI 基线失败阻断，包括页面矩阵 27/30、列表动作权限 4 个断言、存储集群健康分析 2 个断言，以及 `CrudApi extends BaseApi` 异步 rejection。
- [独立后端检查在 worktree 缺少默认配置](../../errors/backend/worktree-config-yml-missing.md)：临时 Alembic SQLite 验证直接导入 `models/database` 时，worktree 缺少 `backend/config.yml`，改为在脚本中显式提供最小测试配置后继续验证。

## 未进入分类事实库

- TDD 红灯和新增测试中的断言修正属于本次开发预期过程，不进入全局错误库。
- 覆盖率命令首次使用错误相对 Python 路径、临时 SQLite 文件句柄释放导致退出时报错，均为本会话脚本修正，无复用价值，不进入全局错误库。
- `pnpm install` 早期 5 秒命令超时，重试后成功，属于一次性环境超时，不进入全局错误库。
