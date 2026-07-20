# 项目使用量与成员默认权限交付

## 范围

- 项目容量概览固定展示使用量，不再提供限额指标。
- 恢复项目实时容量摘要、趋势图和时间范围筛选，避免空存储树导致概览无信息。
- 锁定添加项目成员时默认使用 `reader` 权限的现有行为。
- 用户目录所属用户自动补齐为当前项目的 `reader`，历史数据通过迁移补齐，已有更高角色不降级。

## 进度

- 已完成实现、聚焦单元测试和浏览器验证。

## 验证

- `pnpm exec vitest run test/unit/project-disk-usage.test.js test/unit/project-members-tab.test.js --coverage.enabled=false`
- `pnpm exec vitest run test/unit/page-coverage-gaps.test.js -t "real-time page coverage gaps" --coverage.enabled=false`
- `pnpm exec eslint src/pages/project/ProjectDetailPage.vue src/pages/project/components/ProjectDiskUsage.vue src/pages/common/RealTimePage.vue test/unit/project-disk-usage.test.js`
- `pnpm run build:prod`
- `git diff --check`
- `.\.venv\Scripts\python.exe -m pytest backend\test\test_project_rbac.py backend\test\test_project_rbac_memberships.py backend\test\test_directory_user_membership_migration.py backend\test\test_capacity_prediction_governance_migration.py backend\test\test_project_rbac_unified_audit_migration.py backend\test\test_router_error_paths.py -q`（27 passed）
- 浏览器 `http://localhost:5173/project/2`：容量概览展示项目 `dijun` 的限额、使用量、利用率和趋势区域；时间范围弹层包含一天、一周、一月、三月快捷项；指标下拉仅有“实时使用量”。
- 浏览器 `http://localhost:5173/project/3`：“成员与权限”打开添加成员弹窗后，项目角色默认显示“只读成员”。

## 未验证范围与风险

- 尚未执行全量前端测试；本次只涉及项目详情容量概览与成员添加默认值。
- 当前配置数据库为 `10.0.91.37:5432/diskpulse`，Alembic 当前版本 `000000000013`；因目标不是本机数据库，本会话未直接执行 `upgrade head`，历史成员需在确认环境后应用 `000000000014` 才会出现在页面。
- 浏览器刷新时记录到既有 `401` 请求、图标解析、ECharts 尺寸及 Element Plus 弃用警告；目标页面仍正常渲染，目标交互不受影响，本次未扩展处理这些既有问题。
