# AI 空 choices 流式帧修复交付记录

## 范围

- 修复 OpenAI 兼容 Provider 的 SSE 状态帧 `choices: []` 触发的 `IndexError`。

## 完成项

- 空 `choices` 帧不再访问首个元素，而是作为无内容状态帧跳过。
- 后续正常文本和工具调用帧仍按原有协议解析。
- 新增 Provider 流式回归，覆盖空状态帧后继续输出文本的场景。

## 验证

- RED：新增回归在旧实现下因 `choices[0]` 越界失败。
- GREEN：`D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_services.py test\\test_ai_platform.py -q`，45 项通过；`python -m compileall -q services\\ai_client.py` 通过。

## 风险与未验证范围

- 未再次调用真实 Provider，避免产生额外外部请求；本地带 `--reload` 的后端会自动载入实现。真实 Provider 的后续状态帧将被安全跳过。
