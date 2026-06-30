# StoragePulse

专为芯片行业设计的存储资源监控与管理平台，基于 NetApp 存储架构，提供聚合、Volume、Qtree 等存储资源的全生命周期管理。

技术栈：Vue 3 + Vite + Element Plus + Vue Router + Pinia

## 快速开始

```bash
pnpm install
pnpm dev
```

## 构建

```bash
pnpm build:test   # 测试环境
pnpm build:prod   # 生产环境
```

## 文档

详细文档见 [`docs/`](./docs/) 目录：

- [项目结构规范](./docs/PROJECT_STRUCTURE.md)
- [UI 设计规范](./docs/UI_DESIGN_GUIDE.md)

## 权限说明

- 普通用户：访问 `/`、`/usage`、`/projects`、`/groups`、`/alerts`
- 管理员（`diskpulse:admin`）：额外访问 `/admin/*` 下所有功能
