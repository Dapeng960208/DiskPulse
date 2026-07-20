# 数据库开发规范

本规范适用于数据模型、查询、索引、迁移、时序数据和 Redis 数据边界的变更。此类任务除本规范外，还必须阅读[后端开发规范](../backend/backend-development-standard.md)、[文档规范](../documentation/documentation-standard.md)、[Git 提交规范](../git/git-commit-standard.md)及对应功能专题。

## 数据存储边界

| 存储 | 权威位置 | 职责 |
| --- | --- | --- |
| PostgreSQL | `backend/models.py`、`backend/migrate/versions/` | 业务实体、关系、权限、审计和配置状态。 |
| QuestDB | `backend/questdb/models.py`、`backend/questdb/migrations/` | 容量、性能和其他时序监控数据。 |
| Redis | 运行时键空间 | Celery broker/backend、认证会话、AI 限流和短期确认状态；不是业务事实的长期存储。 |

同一事实只能有一个权威存储。跨存储读取必须明确新鲜度、回退和失败语义，不能将 Redis 缓存或时序快照误写成关系数据的事实来源。

## 模型与迁移

- 新增、删除或修改 PostgreSQL 模型字段时，同步更新 SQLAlchemy 模型、Alembic 迁移、schema、序列化、功能专题和测试。
- Alembic revision id 不得超过 32 个字符；已发布 revision 不可改写或复用，出现分支时以当前 heads 为准创建新的前向迁移。
- QuestDB 迁移是 `backend/questdb/migrations/` 下的前向 SQL 文件，由 `backend/questdb/migrate.py` 按版本和 checksum 执行。已应用文件不可修改；新增迁移必须遵守既有文件名格式。
- Redis 键必须有明确命名空间、TTL、失效行为和不可用时的安全语义。认证、确认或写操作授权依赖 Redis 时，Redis 不可用必须拒绝高风险操作。
- 不得把真实凭据、token、密码或生产地址写入迁移、种子数据、测试夹具或文档示例。

## 数据完整性、事务与查询

- 所有查询使用 SQLAlchemy 参数化表达式，不拼接 SQL 字符串。
- 写操作必须界定 commit、rollback 和异常转换；`IntegrityError` 等数据库异常必须先 rollback，再返回稳定且不泄露敏感信息的错误。
- 项目范围的数据读写必须携带项目过滤和授权校验；数据库层的查询优化不能绕过隔离边界。
- 列表接口在数据库分页和 count 后再返回当前页。列表摘要只读取展示所需字段；关联统计应按当前页主键批量补齐，不得把详情页的深加载集合搬到列表页。
- 新增高频过滤、排序、关联查找或物化读取路径时，评估并实现对应索引。项目隔离字段优先作为组合索引前缀。

## 兼容性与验证

- PostgreSQL 迁移默认兼容 SQLite、PostgreSQL 与 MySQL；使用方言无关的 SQLAlchemy 类型、绑定参数和 DDL/DML 表达式。必须分支时，明确每个方言的兼容策略。
- 涉及迁移时验证迁移链可应用；涉及方言差异时补 SQLite、PostgreSQL、MySQL 的 SQL 编译或参数绑定回归，或明确未验证风险。
- 涉及列表、分析、搜索或统计性能时，测试分页、过滤、索引或物化读取路径，防止回退到详情级深加载。
