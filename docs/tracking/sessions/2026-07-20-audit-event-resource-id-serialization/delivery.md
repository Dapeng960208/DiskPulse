# 审计事件资源 ID 序列化修复

## 交付范围

修复统一审计列表在持久化整数资源 ID 时因响应模型类型不一致而失败的问题。

## 完成项

- 为 `GET /storage-pulse/api/v1/audit-events` 添加整数 `resource_id` 的路由级回归测试。
- 在审计输出序列化层将非空资源 ID 规范为字符串，保持数据库字段类型不变。
- 更新项目级 RBAC 与统一审计的接口事实文档，并记录可复现错误。

## 验证

- 红灯：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_unified_audit.py -k "audit_event_list_serializes_numeric_resource_ids_as_strings" -q`，修复前稳定触发 `AuditEventPage` 的 `resource_id` 类型校验错误。
- 绿灯：同一聚焦测试通过（`1 passed, 13 deselected`）。
- 模块回归：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_unified_audit.py -q`（`14 passed`）。
- 静态编译：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m compileall -q backend/services/audit_service.py backend/routers/audit_events.py` 通过。

## 未验证范围与风险

- 未连接真实开发数据库或通过已运行服务进行手工接口验证；本次未修改模型、迁移、查询或权限逻辑。
- 公开 schema 原本已声明 `resource_id` 为字符串，本次仅恢复该契约；依赖未声明整数类型的客户端应不受影响。
