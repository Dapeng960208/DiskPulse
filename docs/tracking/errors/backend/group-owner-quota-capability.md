# 项目负责人未获得项目组配额调整能力

## 错误内容

`backend/test/test_project_scope_authorization.py::test_quota_capabilities_only_enable_the_responsible_group_owner` 中，已配置为项目组负责人的用户读取 `GET /groups/1` 时，`capabilities.adjust_quota` 实际为 `false`，但授权契约要求为 `true`。

## 解决方案

在独立的项目组配额授权修复中，核对 `project_access_service.group_capabilities` 的负责人识别、项目成员角色和测试种子数据的字段契约；修复后同时验证详情、列表和配额写入的授权边界。本会话不改变详情路由或能力计算。

## 备注

- 首次出现：2026-07-20，`2026-07-20-storage-utilization-range-query` 会话。
- 最近出现：2026-07-20；出现次数：1。
- 差异：本次仅修改 `GET /groups/` 的列表筛选参数和 CRUD 条件，`GET /groups/{group_id}` 与能力计算路径未变。
