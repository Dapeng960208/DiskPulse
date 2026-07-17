<!-- Hallmark pre-emit critique P5 H5 E4 S5 R5 V4. -->

# 应用内容区统一间距设计

## 状态

- 已实现并完成自动化与代表性浏览器验证（2026-07-17）。
- RED 聚焦合同为 `11 tests | 9 failed, 2 passed`；GREEN 为 `11/11`。
- 目标 Vue 文件与间距合同 ESLint 通过；覆盖率为 `61 files / 370 tests passed`，Statements `98.3%`、Branches `88.74%`、Functions `84.17%`、Lines `98.3%`；`build:prod` 成功，保留既有大于 `500k` chunk 警告；`git diff --check` 通过。
- 浏览器验证覆盖 13 个可加载在用路由在 `1383x994` 与 `936x994` 的四边 `16px`、`ElMain` 无外层 padding、面包屑左右 `16px` 和无文档级横/纵溢出；`/ai/chat` 在刷新旧依赖预构建缓存后的当前桌面额外验证，`.ai-workspace` 存在、gutter 为 `16px`、无 Vite overlay，整页刷新后 console errors 为 `0`；`/usage` 在 `375/414/768` 验证移动端 `12px` gutter 与面包屑对齐。
- 真实 ID 详情页未进行浏览器打开；`320px` 视口未生效，窄屏固定侧栏在 `375/414` 的水平溢出属于既有风险。
- 本文只定义前端应用壳与页面外层间距，不涉及后端、API 或数据结构变化。

## 目标

- 由应用壳统一控制可滚动路由内容的上、右、下、左外层留白，消除页面自行叠加外边距造成的间距不一致。
- 桌面端四边统一使用 `16px`（`var(--spacing-lg)`）；视口宽度不超过 `768px` 时统一使用 `12px`（`var(--spacing-md)`）。
- 保留筛选表单、数据表格、卡片、业务表单及页面内部布局的既有内边距和间距，不以全局收紧替代页面结构设计。

## 布局决策

- `AppMain` 的内容滚动容器拥有唯一一层页面外部 gutter，并根据 `768px` 断点切换 `16px` 与 `12px`。
- `AppMain` 不再叠加独立的横向外层 padding，避免滚动容器与主内容组件重复留白。
- 面包屑保持独立的全宽表面，其左右 padding 与当前断点的内容 gutter 一致；面包屑不计入可滚动路由内容的四边 padding。
- `page-layout.scss` 与 `page-container` 只负责布局方式、区块 gap 和高度，不再声明页面外层 padding。
- 页面组件只移除与应用壳 gutter 重复的最外层 padding；不得删除 `QueryForm`、`DataTable`、卡片和业务表单的内部 padding。
- 保留明确的页面内部节奏：列表区块间距 `12px`、概览仪表盘网格间距 `20px`、项目详情页签内容间距 `16px`。

## 在用页面范围

静态路由矩阵以 `frontend/src/router/routes.js` 中使用 `AppLayout` 的路由为准，共 22 条：

| 分类 | 路由 |
| --- | --- |
| 主菜单页面 | `/`、`/usage`、`/projects`、`/groups`、`/alerts`、`/ai/chat` |
| 可达详情页面 | `/usage/:id`、`/project/:id`、`/group/:id` |
| 系统管理页面 | `/admin/group-tags`、`/admin/storage-clusters`、`/admin/aggregates`、`/admin/volumes`、`/admin/qtrees` |
| 系统管理详情 | `/admin/storage-cluster/:id`、`/admin/aggregate/:id`、`/admin/volume/:id`、`/admin/qtree/:id` |
| 权限页面 | `/admin/users`、`/admin/settings`、`/admin/ai-center`、`/admin/ai-center/audits/:id` |

以下页面不在本次范围内：独立登录页 `/login`、错误页 `/403` 与 `/404`，以及当前隐藏且不作为在用入口的 `/admin/backup`。未知路径仅重定向到 `/404`，不单独计入。

## 实现边界

- 应用壳负责统一外层 gutter；共享页面布局样式负责内部排列；业务组件继续负责自身信息层级与交互区域的 padding。
- 逐页检查并只删除重复的页面最外层 padding，不顺带重构卡片、筛选栏、表格、表单、页签或响应式导航。
- 页面级不得新增横向滚动；宽表格仍只允许在其表格容器内部横向滚动。
- 不修改路由可见性、权限判断、页面业务行为、后端接口、请求参数或数据模型。

## TDD 与验证计划

1. 先增加失败合同测试，锁定应用壳唯一 gutter、桌面/移动断点、面包屑独立 padding，以及共享页面布局不再提供外层 padding。
2. 建立 22 条路由的静态矩阵，检查每个页面是否存在重复最外层 padding，并为移除项补充对应静态合同。
3. 完成最小样式调整后运行聚焦 Vitest、目标 ESLint、生产构建与 `git diff --check`。
4. 在 `1383x994` 和 `936x994` 视口逐页检查在用菜单、管理、权限和可达详情页面，确认四边留白一致且内部间距未被误删。
5. 使用 `320px`、`375px`、`414px` 和 `768px` 代表宽度检查响应式 gutter、面包屑对齐、页面横向溢出和表格内部滚动。

详情页浏览器验收需要真实可访问 ID。若环境无法提供有效 ID，则以共享组件、静态路由矩阵和样式合同覆盖详情页，并在交付记录中明确列出未完成的真实数据浏览器场景，不得描述为已验证。

## 验收标准

- 所有在用 `AppLayout` 页面在同一断点下拥有一致的四边外层留白：桌面 `16px`，不超过 `768px` 时 `12px`。
- 面包屑左右边缘与路由内容对齐，同时保持独立全宽背景；内容滚动时不产生第二层水平 padding。
- 页面共享布局和页面根节点不再重复提供外层 padding，筛选、表格、卡片、表单及指定内部 gap 保持不变。
- 页面级无新增水平溢出；宽表格只在表格容器内滚动。
- 自动化、静态路由矩阵和浏览器检查结果均被如实记录；缺少真实详情 ID 的验证缺口明确可见。
