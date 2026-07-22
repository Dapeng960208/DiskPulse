# DiskPulse 文档索引

`docs/` 是项目文档的唯一入口。每个事实只保留一个来源；跨领域关联只能通过相对 Markdown 链接引用，不能复制接口、权限、配置或验证结论。

## 分类规则

文档按“一级领域 / 二级主题”组织。一级领域说明文档职责，二级主题说明具体功能或专业域：

| 一级领域 | 二级主题规则 | 用途 |
| --- | --- | --- |
| 概览 | `product`、`architecture` | 稳定的产品与架构入口。 |
| 规范 | `frontend`、`backend`、`database`、`documentation`、`git` | 开发、文档与交付的强制约束。 |
| 功能专题 | `<领域>/<功能>` | 事实来源；同一功能的概览、前端、后端和运维说明放在同一二级功能目录。 |
| 指南 | `<专业域>/<操作主题>` | 可执行的测试、部署、排障或验收步骤。 |
| 跟踪 | 固定文件 | 短期交付状态和可复现错误。 |

功能专题的一级领域当前固定为：`ai`、`storage`、`identity`、`organization`、`experience`。新功能先归入现有领域，再在其下新建语义明确的二级功能目录；没有合适领域时，先更新本索引与[文档规范](./standards/documentation/documentation-standard.md)再创建目录。

AI 相关文档必须进入 `docs/features/ai/<功能>/`。不得在 `docs/features/` 下新建 `ai-*` 平铺目录；例如对话能力放在 `ai/chat/`，新的 AI 功能应在 `ai/` 下建立自己的二级功能目录。

## 开发前入口

所有任务先阅读[文档规范](./standards/documentation/documentation-standard.md)和[Git 提交规范](./standards/git/git-commit-standard.md)，再按[开发阅读矩阵](./standards/documentation/development-reading-guide.md)选择实现层规范与功能专题。

例如，开发 AI 对话后端时必须阅读[后端规范](./standards/backend/backend-development-standard.md)和[AI 对话专题](./features/ai/chat/overview.md)及其[后端说明](./features/ai/chat/backend.md)；涉及模型或迁移时再阅读[数据库规范](./standards/database/database-development-standard.md)。

## 概览

| 文档 | 说明 |
| --- | --- |
| [产品概览](./overview/product/overview.md) | 产品范围、主要入口和专题导航。 |
| [当前能力](./overview/product/current-capabilities.md) | 已可用能力及其唯一事实来源。 |
| [系统架构](./overview/architecture/system.md) | 前端、后端、数据与任务的整体边界。 |
| [前端架构](./overview/architecture/frontend.md) | Vue 应用、路由、状态和 UI 分层。 |
| [后端架构](./overview/architecture/backend.md) | FastAPI、API、任务和服务端运行边界。 |
| [数据库架构](./overview/architecture/database.md) | PostgreSQL、QuestDB、Redis 与迁移职责。 |

## 功能专题

| 一级领域 | 二级功能与文档 |
| --- | --- |
| AI | [对话与管理中心](./features/ai/chat/overview.md) · [四维容量耗尽风险](./features/ai/capacity-prediction/overview.md) · [流式工具轨迹](./features/ai/chat/streaming-tool-trace-reconciliation.md) · [智能存储运维调研](./features/ai/storage-management/research.md) |
| 存储 | [存储集群](./features/storage/cluster/overview.md) · [厂商事件关联](./features/storage/event-association/overview.md) · [配额](./features/storage/quota/overview.md) · [告警](./features/storage/alerts/design.md) · [趋势](./features/storage/trends/design.md) · [可观测性](./features/storage/observability/overview.md) · [事件中心](./features/storage/incident-center/overview.md) |
| 身份与权限 | [认证](./features/identity/authentication/backend.md) · [用户管理](./features/identity/user-management/overview.md) · [项目级 RBAC 与审计](./features/identity/project-rbac/backend.md) |
| 组织 | [项目组标签](./features/organization/group-tags/design.md) |
| 前端体验 | [应用壳](./features/experience/application-shell/design.md) · [Dashboard](./features/experience/dashboard/design.md) · [Mock 运行时](./features/experience/mock-runtime/frontend.md) |

## 规范、指南与跟踪

| 分类 | 文档 |
| --- | --- |
| 前端规范 | [前端设计与开发规范](./standards/frontend/frontend-design-standard.md) |
| 后端规范 | [后端开发规范](./standards/backend/backend-development-standard.md) · [容量单位 API 契约](./standards/backend/capacity-unit-contract.md) |
| 数据库规范 | [数据库开发规范](./standards/database/database-development-standard.md) |
| 文档规范 | [文档规范](./standards/documentation/documentation-standard.md) · [命名与链接](./standards/documentation/document-naming-convention.md) · [开发阅读矩阵](./standards/documentation/development-reading-guide.md) · [领域术语](./standards/documentation/domain-terminology.md) · [错误记录规则](./standards/documentation/development-error-summary.md) |
| Git 规范 | [Git 提交与交付规范](./standards/git/git-commit-standard.md) |
| 指南 | [前端测试](./guides/frontend/testing.md) · [存储性能与事件排障](./guides/storage/performance-event-troubleshooting.md) |
| 跟踪 | [开发跟踪索引](./tracking/README.md) · [错误总表](./tracking/errors/error-index.md) |
