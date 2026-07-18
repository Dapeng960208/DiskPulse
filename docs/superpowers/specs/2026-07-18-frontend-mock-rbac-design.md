# 前端 Mock 数据与四角色演示设计

## 目标

在不修改后端的前提下，为 DiskPulse 前端提供可通过 `VITE_USE_MOCKS=true` 启用的本地演示运行时。默认请求真实 API；Mock 模式提供四个虚构账户、完整关联的存储管理示例数据和项目级 RBAC 展示。

## 设计

- Mock 运行时放在 `frontend/src/mocks/`，由统一 Axios adapter 处理常规 HTTP 请求，并由受控的 `fetch` 包装处理 AI SSE。
- 四个账户为 `demo-superadmin`、`demo-project-admin`、`demo-editor`、`demo-reader`，密码均为 `Demo@2026`。数据和授权只保留在浏览器内存，刷新后重置。
- `superadmin` 可见全局数据和系统管理；其余账户仅看到所属项目数据。`project_admin` 管理成员和项目审计，`editor` 可更新事件，`reader` 只读；限额按钮仅由响应 `capabilities.adjust_quota` 决定。
- 每个业务路由都由种子数据提供至少一个可显示的列表、详情、指标、图表或页签集合；错误页不伪造业务数据。

## 边界与验证

- Mock 不连接 LDAP、真实设备、通知、导出服务或生产后端，也不保存敏感信息。
- 测试覆盖开关、登录/Profile、路由与菜单、项目过滤、能力、内存写、导出和 SSE；采用 RED/GREEN 提交检查点。
