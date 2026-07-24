# 开发跟踪记录：AI 工具响应黑名单

- 会话：`2026-07-24-ai-tool-response-blacklist`
- 状态：已交付
- 范围：为 AI 暴露的接口增加响应字段黑名单，并限制用户、项目、项目组、用户目录及系统管理工具返回的用户关联和内部敏感信息。

## 已完成

- 已确认 AI 工具通过 `services/ai_tool_service.py` 将业务接口响应传给模型。
- `AIToolDefinition` 增加 `blacklist_fields`，从路由的 `openapi_extra.ai_blacklist_fields` 读取并校验。
- 工具服务在响应归一化后递归移除黑名单字段，再将结果交给 Provider。
- 用户工具的黑名单从 `usersSchema.User` 自动派生，仅保留 `rd_username`；项目、项目组工具移除负责人、收件人和项目组通知关联字段。
- 已更新 AI 对话后端专题，明确配置格式、执行时机和失败行为。
- 用户目录、审计、告警、Incident、存储配置、存储集群及 AI 模型工具均补充路由级黑名单；目录工具不再向 Provider 发送用户对象、用户 ID、目录路径、文件系统标识或嵌套负责人信息。
- 大文件和离职备份记录保持原业务路由不变，但移除 `ai_exposed`，不再注册为 AI 对话工具。
- 新增回归测试，覆盖上述黑名单和两条工具的未注册约束；既有系统管理工具测试同步移除离职备份记录预期。

## 验证

- 基线：`D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_platform.py -q` 通过（31 项）。
- RED：`D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_platform.py -q -k 'filters_route_configured_response_fields or privacy_blacklists'` 按预期失败（2 项）；工具定义尚未提供 `blacklist_fields`。
- GREEN：同一命令通过（2 项）。
- 聚焦回归：`D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_platform.py test\\test_ai_services.py -q` 通过（61 项）。
- 覆盖率：`D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m coverage run --source=services.ai_tool_service -m pytest test\\test_ai_platform.py test\\test_ai_services.py -q`，随后执行 `D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m coverage report --fail-under=85 services\\ai_tool_service.py`；61 项通过，`services.ai_tool_service.py` 覆盖率 87%。
- 后续 RED：`D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_platform.py -k sensitive_ai_tools_have_response_blacklists_or_are_not_registered -q` 按预期失败；用户目录工具尚未声明黑名单。
- 后续 GREEN：同一命令通过（1 项）。
- 后续聚焦回归：`D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m pytest test\\test_ai_platform.py test\\test_ai_services.py -q` 通过（62 项）。
- 后续覆盖率：`D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m coverage run --source=services.ai_tool_service -m pytest test\\test_ai_platform.py test\\test_ai_services.py -q`，随后执行 `D:\\dev\\DiskPulse\\.venv\\Scripts\\python.exe -m coverage report --fail-under=85 services\\ai_tool_service.py`；62 项通过，`services.ai_tool_service.py` 覆盖率 87%。

## 未验证范围与风险

- 未执行真实 Provider、Redis 或生产 LDAP/数据库的端到端对话；本次变更只修改进程内工具响应投影，权限与业务接口仍由原有 ASGI 调用链校验。
