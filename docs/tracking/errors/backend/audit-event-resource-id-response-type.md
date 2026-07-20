# 审计事件资源 ID 响应类型不一致

## 错误内容

`GET /storage-pulse/api/v1/audit-events` 从数据库读到整数型 `resource_id` 后直接传入声明为 `string | null` 的 `AuditEventOut`，构造 `AuditEventPage` 时触发 Pydantic `string_type` 校验错误，列表请求返回服务器错误。

## 解决方案

保持 `AuditEvent.resource_id` 的数据库整数类型不变，在 `serialize_audit_event` 中仅将非空资源 ID 转换为字符串，使列表和详情接口都符合公开响应契约。

## 备注

- 分类：`backend`
- 出现次数：1
- 首次与最近出现：2026-07-20 审计事件资源 ID 序列化会话
- 出现记录：`sessions/2026-07-20-audit-event-resource-id-serialization/errors.md`
