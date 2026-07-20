# 开发阅读矩阵

本页规定 AI 和人工开发者在开始修改前必须阅读的文档。阅读范围由“实现层 + 功能领域”组成；跨层任务取并集，不以某一层规范代替另一层。

## 所有任务

所有任务必须先阅读：

1. [文档规范](./documentation-standard.md)，确认分类、事实来源和同步范围；
2. [Git 提交与交付规范](../git/git-commit-standard.md)，确认变更边界和交付要求。

涉及产品术语、资源名称、权限、指标或用户文案时，还必须阅读[领域术语表](./domain-terminology.md)。

## 按实现内容阅读

| 开发内容 | 必读规范 | 必读功能文档 |
| --- | --- | --- |
| 前端页面、交互、路由、Mock | [前端规范](../frontend/frontend-design-standard.md) | 目标功能目录中的 `overview.md` 与 `frontend.md` 或等价事实文档。 |
| 后端 API、服务、任务、权限 | [后端规范](../backend/backend-development-standard.md) | 目标功能目录中的 `overview.md` 与 `backend.md` 或等价事实文档。 |
| 模型、查询、索引、迁移、QuestDB、Redis 数据边界 | [数据库规范](../database/database-development-standard.md) 和[后端规范](../backend/backend-development-standard.md) | 目标功能目录及相关架构文档。 |
| 文档新增、移动、删除或链接更新 | [文档规范](./documentation-standard.md) 和[命名与链接](./document-naming-convention.md) | 被修改功能的事实来源。 |
| 测试、排障、部署验收 | 对应实现层规范 | 目标功能专题和对应 `guides/<专业域>/` 文档。 |

涉及存储容量 API、容量树、容量趋势、预测或其前端展示时，必须额外阅读[容量单位 API 契约](../backend/capacity-unit-contract.md)。

## AI 功能的强制组合

AI 功能先定位到 `docs/features/ai/<功能>/`，再按改动层选择规范：

| 场景 | 额外必读文档 |
| --- | --- |
| AI 对话后端、Provider、工具、SSE 服务端、权限或审计 | [后端规范](../backend/backend-development-standard.md) + [AI 对话总览](../../features/ai/chat/overview.md) + [AI 对话后端](../../features/ai/chat/backend.md) |
| AI 对话前端、流式渲染、会话状态或管理页面 | [前端规范](../frontend/frontend-design-standard.md) + [AI 对话总览](../../features/ai/chat/overview.md) + [AI 对话前端](../../features/ai/chat/frontend.md) |
| AI 数据模型、迁移、限流、会话或审计存储 | [数据库规范](../database/database-development-standard.md) + 对应 AI 后端文档 |
| 新的 AI 能力 | 在 `docs/features/ai/` 下创建或选择二级功能目录，并先写入该目录的事实文档；跨领域信息通过链接引用。 |

例如，开发 AI 对话后端且修改会话表时，阅读顺序为：通用规范、后端规范、数据库规范、`features/ai/chat/overview.md`、`features/ai/chat/backend.md`。
