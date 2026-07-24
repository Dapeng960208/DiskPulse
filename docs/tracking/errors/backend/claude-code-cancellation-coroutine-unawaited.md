# Claude Code 取消协程未 await

## 错误内容

运行 `test_claude_code_adapter.py` 与其他后端回归时，Python 报告 `RuntimeWarning: coroutine '_ClientState._cancel_client' was never awaited`。

## 解决方案

`_ClientState.cancel()` 通过 `loop.call_soon_threadsafe` 先把普通回调交给事件循环，只在回调实际执行后创建取消协程。事件循环关闭、拒绝调度或不再执行回调时不会产生无人接管的协程；聚焦测试使用 `-W error` 验证取消路径不再产生该警告。

## 备注

- 出现次数：2。
- 2026-07-23，`2026-07-23-ai-model-auto-discovery` 会话：同步 `main@9c22ba9` 后执行 Claude Code、预测事件和 AI 模型回归时出现；190 个测试仍全部通过。
- 2026-07-24，`2026-07-24-code-review-fixes` 会话：代码审查聚焦回归再次稳定复现；将协程创建移入事件循环线程后，适配器测试在 `-W error` 下 11 项全部通过。
