# 集群查询 AI 工具权限交付记录

- 会话：`2026-07-23-ai-cluster-query-tools`
- 状态：已完成
- 分支：`codex/ai-model-reasoning-effort`
- 工作区：`.worktrees/ai-model-reasoning-effort`

## 范围

- 将集群详情相关的 JSON 查询注册为 AI 工具：容量趋势与分布、容量池/存储空间/Qtree（NetApp）读查询、性能分析、故障分析、耗尽风险、容量预测、性能异常、关联 Incident 和确定性诊断。
- 这些工具仅向超级管理员注册，并在工具执行期再次拒绝非超级管理员。
- 保持原页面和业务 API 的查询范围、参数校验及数据隔离不变；二进制健康分析导出不注册为 AI 工具。

## 已完成

- 已补充真实集群查询路由的 AI 注册和执行期权限契约测试。
- 已为对应 FastAPI `GET` 路由补充 `ai_exposed`、`ai_system_management`、`ai_name` 和 `ai_description` 元数据。
- 已同步 AI 对话与存储集群专题文档。

## 验证

- `cd backend; D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test/test_ai_platform.py test/test_storage_health_analytics.py test/test_forecast_incident_center.py -q`：156 passed。
- `cd backend; D:\dev\DiskPulse\.venv\Scripts\python.exe -m coverage run --source=services.ai_tool_service -m pytest test/test_ai_platform.py -q`，随后执行 `coverage report --fail-under=85`：24 passed，`services.ai_tool_service` 覆盖率 91%。
- `git diff --check` 通过；未暂存差异中未发现凭据形态的值。

## 风险与部署确认

- 本次仅改变 AI 工具目录与执行门禁；真实 Provider、Redis、数据库和不同角色的完整 SSE 对话未在本地验证，仍需部署环境验收。
- 厂商系统事件、性能和预测结果继续受原路由的数据范围和采集数据完整性约束。
