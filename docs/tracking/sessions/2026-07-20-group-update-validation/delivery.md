# 开发跟踪记录：项目组编辑校验失败

- 会话：`2026-07-20-group-update-validation`
- 状态：已交付
- 范围：修复编辑项目组时回传只读响应字段，导致 `PUT /storage-pulse/api/groups/{group_id}` 返回 `422` 的问题。

## 已完成

- 为项目组编辑表单补充只读响应字段不回传的回归测试。
- 将项目组写入请求改为表单字段白名单，避免回传 `capabilities`、`capacity` 和其他列表只读字段。
- 更新项目组标签功能事实与前端错误分类记录。

## 验证与风险

- `cd frontend && pnpm exec vitest run test/unit/form-dialog-behavior.test.js --coverage.enabled=false` 通过（11 项）。
- `cd frontend && pnpm run lint` 通过。
- `cd frontend && pnpm run build:prod` 通过；保留既有的 `%VITE_APP_TITLE%` 未定义和大包体积提示。
- 未执行完整前端测试或连接真实后端的浏览器联调；本地 mock 首页可渲染，但项目页在自动化会话中未稳定到可操作状态。本次改动仅限项目组表单的请求序列化。
