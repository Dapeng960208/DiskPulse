# DiskPulse 文档索引

本文档目录是项目文档的唯一入口。专题文档不直接放在 `docs/` 根目录，按用途进入对应子目录。

## 目录结构

```text
docs/
  README.md
  overview/
  features/
  guides/
  standards/
  tracking/
```

## 概览

| 文档 | 说明 |
| --- | --- |
| [overview/backend-architecture.md](./overview/backend-architecture.md) | 后端架构、数据层、任务流和维护边界。 |
| [overview/latest-features.md](./overview/latest-features.md) | 最新功能、用户可见修复和测试覆盖进展。 |

## 指南

| 文档 | 说明 |
| --- | --- |
| [guides/frontend-testing-guide.md](./guides/frontend-testing-guide.md) | 前端测试命令、覆盖率门禁和 mock 约定。 |

## 功能专题

| 专题 | 文档 |
| --- | --- |
| LDAP 认证 | [features/authentication/backend.md](./features/authentication/backend.md) |
| 用户信息管理 | [features/user-management/overview.md](./features/user-management/overview.md) |
| 项目组标签 | [features/group-tag/design.md](./features/group-tag/design.md) |
| 存储集群 | [features/storage-cluster/overview.md](./features/storage-cluster/overview.md) |
| 存储配额软限额 | [features/storage-quota/overview.md](./features/storage-quota/overview.md) |
| AI 对话与管理中心 | [总览](./features/ai-chat/overview.md) · [后端实现](./features/ai-chat/backend.md) · [前端实现](./features/ai-chat/frontend.md) |

## 规范

| 文档 | 说明 |
| --- | --- |
| [standards/documentation-standard.md](./standards/documentation-standard.md) | 文档更新和放置规则。 |
| [standards/domain-terminology.md](./standards/domain-terminology.md) | DiskPulse 领域术语和权限命名约定。 |
| [standards/document-naming-convention.md](./standards/document-naming-convention.md) | 文档命名和目录约定。 |
| [standards/backend-development-standard.md](./standards/backend-development-standard.md) | 后端开发规范。 |
| [standards/frontend-design-standard.md](./standards/frontend-design-standard.md) | 前端设计规范。 |
| [standards/ai-development-standard.md](./standards/ai-development-standard.md) | AI 协作开发规范。 |
| [standards/development-error-summary.md](./standards/development-error-summary.md) | 错误记录格式参考。 |

## 跟踪记录

| 文档 | 说明 |
| --- | --- |
| [tracking/current-release.md](./tracking/current-release.md) | 当前交付、风险和验证状态。 |
| [tracking/error-log.md](./tracking/error-log.md) | 可复现错误、环境问题和规范缺口记录。 |
| [tracking/backend-schema-review-2026-06-30.md](./tracking/backend-schema-review-2026-06-30.md) | 后端 schema 审查记录。 |
| [tracking/unused-field-audit-2026-07-13.md](./tracking/unused-field-audit-2026-07-13.md) | ORM 未使用字段、无效重复配置和后续清理范围审计。 |

## 维护规则

- 新增专题文档优先放入 `features/<feature>/`。
- 项目级稳定说明放入 `overview/`。
- 部署、迁移、排障、验收类文档放入 `guides/`。
- 当前交付、风险和错误记录放入 `tracking/`。
- 文件名和目录名使用英文 `kebab-case`。
