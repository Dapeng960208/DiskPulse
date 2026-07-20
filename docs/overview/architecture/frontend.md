# 前端架构说明

## 运行入口

`frontend/src/main.js` 创建 Vue 应用、注册 Vue Router 与 Pinia，并加载全局 SCSS、UnoCSS、Element Plus 主题和标准化样式。应用根组件为 `frontend/src/App.vue`。

路由入口是 `frontend/src/router/index.js`：它使用 HTML5 history、在导航前获取当前用户资料，并依据路由可访问性结果进入目标页、403、404 或登录页。路由定义和懒加载页面位于 `frontend/src/router/routes.js`。

## 分层边界

| 层 | 位置 | 职责 |
| --- | --- | --- |
| 页面与布局 | `frontend/src/pages/`、`frontend/src/layouts/` | 页面编排、应用壳和领域交互。 |
| 路由与权限 | `frontend/src/router/` | 路由表、导航守卫、可访问性判断和菜单可见性。 |
| 状态 | `frontend/src/stores/` | 当前用户、应用设置和跨页状态。 |
| API 与请求支持 | `frontend/src/api/` | 按资源域组织的请求封装与响应处理。 |
| 共享组件与样式 | `frontend/src/components/`、`frontend/src/styles/` | 可复用 UI、设计 token 和全局布局。 |

前端只负责体验和入口控制；服务端仍是权限、项目隔离和数据校验的最终边界。详细约束见[前端设计与开发规范](../../standards/frontend/frontend-design-standard.md)，功能页面的事实来源在 `docs/features/experience/`、`docs/features/storage/`、`docs/features/ai/` 等对应专题目录。

## 验证入口

测试、构建和 Mock 启动方式见[前端测试指南](../../guides/frontend/testing.md)。Mock 只能通过受控开关启用，且必须保持真实 API 的数据信封和权限语义。
