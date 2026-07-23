# 独立后端检查在 worktree 缺少默认配置

## 错误内容

在 feature worktree 中直接运行一次导入 `database` 的临时后端检查。`appConfig.base_config` 在没有显式加载配置时默认读取 worktree 内的 `backend/config.yml`，而环境配置不随 Git worktree 跟踪，因此在查询执行前失败：

```text
FileNotFoundError: Configuration file not found: D:\dev\DiskPulse\.worktrees\event-association-catalog\backend\config.yml
```

该错误表示检查入口未按测试约定初始化配置，不表示目录代码或数据库查询本身失败。

## 解决方案

优先通过 pytest 运行后端检查，复用 `backend/test/conftest.py` 的初始化顺序：在导入 `database` 及其他依赖数据库的模块前，显式执行 `base_config.load(BACKEND_ROOT / "config.test.yml")`。独立 smoke 脚本也必须保持同一顺序，并使用隔离测试库或 SQLite 夹具。

不要把主 worktree 或真实环境的 `config.yml` 复制到 feature worktree，也不要为了通过开发检查而连接或写入真实业务数据库。

## 备注

- 分类：`backend`
- 出现次数：4
- 首次出现：2026-07-21，`2026-07-21-event-association-catalog`
- 最近出现：2026-07-23，`2026-07-23-ai-model-reasoning-effort`
- 出现记录：`sessions/2026-07-21-event-association-catalog/errors.md`
- 出现记录：`sessions/2026-07-23-ai-model-reasoning-effort/errors.md`；临时 Alembic SQLite 验证直接导入 `models/database` 时，worktree 缺少 `backend/config.yml`，改为在脚本中显式提供最小测试配置后继续验证。
