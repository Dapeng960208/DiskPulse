# AI 工具编排与分析工具交付

## 范围

- 定位 AI 对话在成功工具结果后仍重复请求、失败调用未得到改参重试指导的问题。
- 将性能异常、故障分析事件和受控的存储空间性能监控纳入 AI 工具注册。

## 已完成

- 同一对话回合按“工具名 + 规范化参数”复用成功工具结果；工具轨迹以“复用已获取结果”区分，未再次调用业务接口，并强制下一次 Provider 请求不携带工具以总结已有结果。
- 工具参数或请求失败时向模型追加安全改参提示；连续三次失败后使用已有结果进行无工具降级总结并提供“重新查询”。
- 为当前用户暴露性能异常、故障事件和确定性 Incident 诊断；存储空间性能监控仅对超级管理员暴露，响应不包含目录路径。

## 验证

- `\.venv\Scripts\python.exe -m pytest backend\test\test_ai_platform.py backend\test\test_ai_services.py -q -p no:cacheprovider --basetemp=D:\dev\DiskPulse\.tmp\ai-tool-orchestration-full-tests`：47 passed。
- `npm exec vitest run test/unit/ai-pages.test.js`（在 `frontend/`）：19 passed。
- `\.venv\Scripts\python.exe -m py_compile backend\services\ai_chat_service.py backend\routers\forecast_incidents.py backend\routers\volumes.py backend\schemas\volumeSchema.py`：通过。
- `git diff --check`：通过。
- `\.venv\Scripts\python.exe -m pytest backend\test\test_ai_services.py::test_stream_reuses_successful_tool_results_and_repairs_failed_calls -q -p no:cacheprovider --basetemp=D:\dev\DiskPulse\.tmp\ai-tool-reuse-summary-green`：1 passed。

## 未验证范围与风险

- 未连接真实 Provider、Redis、数据库迁移或存储集群；部署前仍需由普通用户和超级管理员分别进行真实 SSE 冒烟。
- 工具结果复用只限当前回合；新回合仍会重新读取实时数据。
