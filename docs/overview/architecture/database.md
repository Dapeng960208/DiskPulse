# 数据库架构说明

DiskPulse 将业务事实、时序监控数据和短期运行态分离存储；任何跨存储逻辑都必须明确权威来源、失败语义和数据新鲜度。

| 存储 | 当前职责 | 权威位置 |
| --- | --- | --- |
| PostgreSQL | 用户、项目、存储资源、权限、告警、审计、AI 配置与会话等业务状态。 | `backend/models.py` 与 `backend/migrate/versions/` |
| QuestDB | 容量、性能和其他趋势监控数据。 | `backend/questdb/models.py` 与 `backend/questdb/migrations/` |
| Redis | Celery broker/backend、认证会话、AI 限流、任务锁和短期确认状态。 | 运行时键空间与 `backend/config.yml` 配置 |

## 关系数据

核心资源关系以存储集群、容量池、存储空间、Qtree（NetApp）、项目组和用户目录为主线；项目、用户、项目组标签、权限和审计围绕该主线关联。完整资源术语和字段映射见[存储资源映射](../../features/storage/cluster/resource-mapping.md)，不要在本页复制功能表结构。

## 时序数据与迁移

PostgreSQL 模型变更由 Alembic 前向迁移管理；迁移只负责表、字段、索引和约束。厂商事件关联目录等初始化数据由独立、幂等的初始化入口在迁移完成后写入，不放入 revision DML；该入口只补缺失唯一键，不覆盖管理员维护的数据。QuestDB 使用独立 SQL 前向迁移，`backend/questdb/migrate.py` 按版本和 checksum 执行并记录已应用版本。Redis 不是业务事实的长期存储，依赖 Redis 的授权或确认流程在 Redis 不可用时必须安全失败。

模型、迁移、索引、查询和跨方言兼容规则以[数据库开发规范](../../standards/database/database-development-standard.md)为准；后端请求生命周期、服务边界和任务入口见[后端架构](./backend.md)。
