# 统一审计关联上下文补全

## 范围

- 为统一审计 API 补齐当前主体、资源名称与资源到项目的关联摘要。
- 在统一审计列表和详情中清晰区分直接关联与经资源推导的项目关联，并提供可访问时的资源跳转。
- 不变更 `audit_events` 的追加式历史记录，也不改写历史审计值。

## 进度

- 已新增后端 API 契约测试与前端列表呈现测试。
- RED 已确认：API 尚未返回 `actor`、`resource`、`related_projects` 与 `relation_path`；列表仍以原始主体 ID 和资源类型/ID 呈现。
- 已在 API 当前页批量解析主体、直接项目、资源名称及资源反查项目；项目管理员的间接项目结果仅保留其有权项目，避免经共享存储资源枚举其他项目。
- 已将统一审计列表的项目列改为“关联项目”，区分“直接”和“经资源”，并在详情抽屉和独立详情页呈现关联路径；资源和项目在可访问时可跳转。

## 验证

- 基线：`backend/test/test_unified_audit.py` 14 通过；`frontend/test/unit/incident-and-audit-list-layout.test.js` 4 通过。
- RED：`backend/test/test_unified_audit.py` 的新增 API 契约用例按预期失败；`frontend/test/unit/audit-event-table-associations.test.js` 的新增呈现用例按预期失败。
- GREEN：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_unified_audit.py -q --basetemp D:\dev\DiskPulse\.worktrees\audit-association-context\.pytest-temp`，16 通过；随后 `compileall -q backend` 通过。
- GREEN：`pnpm exec vitest run test/unit/audit-event-table-associations.test.js test/unit/incident-and-audit-list-layout.test.js test/unit/mock-runtime.test.js --coverage.enabled=false`，27 通过；改动文件 ESLint 通过，`pnpm run build:prod` 通过。
- 浏览器：Mock 超级管理员登录后访问 `/admin/audit-events`，确认“经资源”行显示 `存储告警 → 存储集群 → 项目组 → 项目`；打开详情后显示资源名称、关联项目与完整关联路径。修复资源链接的 Element Plus `underline` 弃用告警后，复核页无本次改动引入的控制台错误。

## 未验证范围与风险

- 关联名称来自当前仍存在的业务实体；已删除实体只能保留审计记录中的类型和逻辑 ID。
- 未连接部署环境的真实数据库、LDAP 和存储设备；生产数据中的历史资源类型若不在当前支持的资源集合内，会继续以原始类型和逻辑 ID 展示。
