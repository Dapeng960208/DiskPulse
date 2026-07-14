# StorageCluster 数据库初始化

## 适用范围

项目处于初始开发阶段，不保留历史数据、增量 revision 或向前兼容迁移。PostgreSQL 与 QuestDB 使用独立初始化流程。

## PostgreSQL / Alembic

`backend/migrate/versions/` 只保留：

```text
000000000001_initial_schema.py
```

该 root/head baseline 从空库创建当前 `14` 张业务表和 `31` 个索引，其中包含 `storage_clusters` 及 `aggregates`、`volumes`、`qtrees`、`project_storage_environments`、`storage_usages` 的集群关系。

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini heads
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini history
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
```

已使用删除前 revision 的开发数据库不支持原地升级。确认数据可丢弃后重建空数据库，再执行 `upgrade head`；不得通过手工修改 `alembic_version` 伪造升级路径。

`downgrade base` 仅用于空库往返验证，不作为保留开发数据的回滚方案。

## QuestDB

QuestDB 不属于 Alembic 管理范围。存储集群和项目环境趋势表由 `backend/questdb/models.py` 及 QuestDB 初始化流程维护；PostgreSQL 的 `upgrade/downgrade` 不创建、修改或删除 QuestDB 表。

本阶段不迁移或回填历史 QuestDB 数据。真实 QuestDB 的表结构、连接和读写需要在集成环境单独验收。

## 已验证与待验证

- versions 恰好 `1` 个，`000000000001` 为 root/head。
- SQLite upgrade 后与 `Base.metadata` 对比无差异，downgrade 后为 `0` 张表。
- PostgreSQL offline upgrade/downgrade DDL 编译和逆序 drop 审计通过。
- 尚未在真实 PostgreSQL 或 QuestDB 环境执行端到端初始化。
