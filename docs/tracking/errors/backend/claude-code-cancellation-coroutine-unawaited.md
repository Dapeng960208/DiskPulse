# Claude Code 取消协程未 await

## 错误内容

运行 `test_claude_code_adapter.py` 与其他后端回归时，Python 报告 `RuntimeWarning: coroutine '_ClientState._cancel_client' was never awaited`。

## 解决方案

后续维护 Claude Code 适配器时，应确保 `_ClientState.cancel()` 在事件循环已关闭、取消调度失败或测试替身拒绝调度的路径中关闭或等待已创建的协程；不得仅取消 Future 而留下未调度协程。本会话未修改该适配器，因为警告来自同步到当前 `main` 的既有测试路径，与模型发现需求无关。

## 备注

- 出现次数：1。
- 2026-07-23，`2026-07-23-ai-model-auto-discovery` 会话：同步 `main@9c22ba9` 后执行 Claude Code、预测事件和 AI 模型回归时出现；190 个测试仍全部通过。
