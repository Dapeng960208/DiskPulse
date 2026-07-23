# 开发跟踪记录：系统管理导航分类

- 会话：`2026-07-23-system-management-navigation`
- 状态：已交付
- 范围：“系统管理”菜单术语、分类顺序与分区展示。

## 已完成

- “事件关联信息”更名为术语表中的“厂商事件关联目录”。
- “存储集群”保持独立入口；其余入口按“基础配置”“智能治理”“事件与审计”分区排序。
- 原有路由 URL、页面组件和超级管理员权限边界保持不变。
- TDD RED 检查点为 `c2a0743`、`a9fc4b5`，GREEN 功能提交为 `5bf2aa1`。

## 验证

- `cd frontend && pnpm exec vitest run test/unit/router/routes.test.js --coverage.enabled=false`：`1 file / 13 tests passed`。
- `cd frontend && pnpm exec vitest run test/unit/router/routes.test.js test/unit/router/routes-dynamic-import.test.js test/unit/router/index.test.js test/unit/router/accessibility.test.js --coverage.enabled=false`：`4 files / 21 tests passed`。
- `cd frontend && pnpm run lint`：通过。
- `cd frontend && pnpm run build:prod`：通过；保留既有的大 chunk 提示。
- 本地页面验证 `/admin/incidents` 与 `/admin/vendor-event-definitions`：三个分区标题及入口顺序正确，“厂商事件关联目录”点击后路由和高亮正确，页面无横向溢出，控制台无 error。
- `git diff --check`：通过。

## 未验证范围与风险

- 本次不修改后端接口、数据库、权限或业务数据。
- 未运行前端全量测试或全量覆盖率；本次按小范围导航改动执行受影响路由测试。
- 生产构建仍有既有的大 chunk 提示，本次未改变依赖或拆包策略。
