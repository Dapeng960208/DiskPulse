# DiskPulse 产品概览

DiskPulse 是面向企业存储运维的管理平台，围绕多厂商存储资源采集、容量与性能观察、配额与告警、身份权限及受控 AI 助手提供统一入口。

## 产品范围

- 管理 NetApp 与 PowerScale 存储集群及其容量池、存储空间、Qtree（NetApp）、项目组和用户目录。
- 提供容量趋势、性能、厂商事件、告警、配额调整、备份和大文件等运维能力。
- 通过 LDAP/JWT、项目级权限与审计约束访问；AI 助手只在既有业务 API、权限和工具边界内运行。

当前已可用能力及其事实来源见[当前能力](./current-capabilities.md)。未发布设计、调研和路线图必须在各自专题中显式标识，不能写入本页作为现状。

## 架构入口

| 视图 | 说明 |
| --- | --- |
| [系统架构](../architecture/system.md) | 前端、后端、数据存储、任务和外部存储系统的边界。 |
| [前端架构](../architecture/frontend.md) | Vue 应用、路由、状态与界面分层。 |
| [后端架构](../architecture/backend.md) | FastAPI、服务、任务和 API 入口。 |
| [数据库架构](../architecture/database.md) | PostgreSQL、QuestDB、Redis 与迁移职责。 |

## 功能导航

功能文档按领域和功能两级放置。AI 相关功能统一位于 `docs/features/ai/`，其现有入口为[AI 对话专题](../../features/ai/chat/overview.md)和[AI 存储运维调研](../../features/ai/storage-management/research.md)；存储、身份与权限、组织和前端体验的完整导航见[文档索引](../../README.md)。
