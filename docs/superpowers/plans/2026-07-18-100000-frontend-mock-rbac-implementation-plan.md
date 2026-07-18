# 前端 Mock 数据与四角色演示实施计划

批准时间：2026-07-18

设计：[前端 Mock 数据与四角色演示设计](../specs/2026-07-18-frontend-mock-rbac-design.md)

1. 在独立 `codex/frontend-mock-rbac` worktree 中建立 `VITE_USE_MOCKS` 控制的内存网关与关联种子数据。
2. 接入 Axios、原生 fetch/SSE、登录快捷账户以及与后端 RBAC 合同一致的前端路由和能力控制。
3. 为每个业务路由提供数据读取覆盖；写入仅维护当前会话内存。
4. 先完成 Mock/RBAC 聚焦 RED 用例，再以最小实现达成 GREEN，并执行前端测试、测试构建和 diff 检查。
