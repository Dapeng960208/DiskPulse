# 项目详情项目组列表操作恢复

## 范围

恢复项目详情“项目组”页签右侧操作列中的添加项目组、编辑和调整额度入口。

## 已完成

- 超级管理员可在表头添加项目组，并在行内编辑项目组。
- 服务端为项目组行授予 `capabilities.adjust_quota` 时显示“调整额度”。
- 复用现有项目组表单与额度调整弹窗；任一写入提交后刷新当前项目组列表。
- 增加项目组页签操作列和权限门禁回归测试，并更新既有页签测试的挂载上下文。

## 验证

- `cd frontend && pnpm exec vitest run test/unit/project-context-tabs.test.js test/unit/project-groups-tab-actions.test.js --coverage.enabled=false`
- `cd frontend && pnpm exec eslint src/pages/project/components/ProjectGroupsTab.vue`
- `cd frontend && pnpm run build:test`
- `git diff --check`

## 未验证范围和风险

- 本机浏览器未持有已登录的超级管理员会话；访问本地应用被重定向至登录页，项目详情中的真实按钮和弹窗交互未作浏览器验证。
- 后端写接口和行级额度授权未改动，仍由现有服务端权限边界执行。
