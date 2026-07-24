# 严格警告模式发现未关闭的 SQLite 连接

## 错误内容

Claude Code、AI 推理和 AI 平台联合回归的 163 项业务断言全部通过，但使用 `pytest -W error` 退出时，pytest 在垃圾回收阶段报告 3 个 `sqlite3.Connection` 未关闭，并以 `PytestUnraisableExceptionWarning` 使命令返回失败。

## 解决方案

定位创建这些 SQLite 连接的测试夹具或临时引擎，在夹具 teardown 中显式关闭会话、连接并调用 `engine.dispose()`。修复前，取消协程警告使用不依赖数据库夹具的适配器测试配合 `-W error` 验证；联合回归仍按项目常规警告策略运行。

## 备注

- 分类：`backend`
- 出现次数：1
- 首次出现：2026-07-24 Main 分支代码审查问题修复会话
- 最近出现：2026-07-24 Main 分支代码审查问题修复会话
- 出现记录：`sessions/2026-07-24-code-review-fixes/errors.md`
