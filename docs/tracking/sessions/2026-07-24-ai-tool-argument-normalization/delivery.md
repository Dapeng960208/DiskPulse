# AI 工具参数名归一化交付

## 范围

- 修复 `list_storage_usages` 因 Provider 传入展示式参数名而在动态工具校验阶段失败的问题。

## 已完成

- 动态工具执行器在 Pydantic 校验前将无歧义的展示式参数名映射到路由字段别名。
- 支持 `use ratio min` → `use_ratio_min` 与 `use_max` → `use_ratio_max`；未知 `null` 占位参数不会阻断查询。
- 保持 `extra="forbid"`：非空未知参数、错误类型和越界值仍由原有校验拒绝。
- 更新 AI 工具参数契约与可复现错误记录。

## 验证

- `cd backend; ..\.venv\Scripts\python.exe -m pytest test\test_ai_tool_argument_normalization.py -q`：RED 阶段 2 项失败，GREEN 阶段 2 项通过。
- `cd backend; ..\.venv\Scripts\python.exe -m coverage run -m pytest test\test_ai_tool_argument_normalization.py test\test_ai_platform.py test\test_ai_services.py -q`：64 项通过。
- `cd backend; ..\.venv\Scripts\python.exe -m coverage report --include='services/ai_tool_service.py' --show-missing`：89%。

## 未验证范围与风险

- 未向外部 AI Provider 发起真实对话调用；兼容行为由内部 ASGI 路径和动态工具回归测试验证。
- 运行中的服务需重新加载源码后才会应用修复。
