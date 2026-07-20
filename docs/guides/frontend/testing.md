# 前端测试指南

在 `frontend/` 目录使用 `pnpm` 运行当前项目脚本：

```powershell
pnpm test
pnpm run test:coverage
pnpm exec vitest run <test-file> --coverage.enabled=false
pnpm run lint
pnpm run build:prod
```

- `pnpm test` 运行全量 Vitest；`pnpm run test:coverage` 同时校验四项覆盖率门槛。
- 只改动局部行为时，优先运行受影响的测试文件；共享组件、路由、Mock、状态或 API 契约变更需要扩大验证范围。
- Mock 仅用于演示：`pnpm mock` 启动 Vite mock 模式，不能替代真实后端、权限或外部设备集成验证。
- Dialog、Select、Popover 等 portal 组件测试挂载到 `document.body`，并在用例结束后清理 DOM 和 wrapper。

前端交互、权限和覆盖率要求见[前端设计与开发规范](../../standards/frontend/frontend-design-standard.md)。
