# 统一审计关联上下文补全

## 范围

- 为统一审计 API 补齐当前主体、资源名称与资源到项目的关联摘要。
- 在统一审计列表和详情中清晰区分直接关联与经资源推导的项目关联，并提供可访问时的资源跳转。
- 不变更 `audit_events` 的追加式历史记录，也不改写历史审计值。

## 进度

- 已新增后端 API 契约测试与前端列表呈现测试。
- RED 已确认：API 尚未返回 `actor`、`resource`、`related_projects` 与 `relation_path`；列表仍以原始主体 ID 和资源类型/ID 呈现。

## 验证

- 基线：`backend/test/test_unified_audit.py` 14 通过；`frontend/test/unit/incident-and-audit-list-layout.test.js` 4 通过。
- RED：`backend/test/test_unified_audit.py` 的新增 API 契约用例按预期失败；`frontend/test/unit/audit-event-table-associations.test.js` 的新增呈现用例按预期失败。

## 未验证范围与风险

- 关联名称来自当前仍存在的业务实体；已删除实体只能保留审计记录中的类型和逻辑 ID。
