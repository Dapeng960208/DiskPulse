# StorageCluster 数据库版本管控与初始化

## 适用范围

PostgreSQL 与 QuestDB 使用独立 revision 链。PostgreSQL 由 Alembic 管理；QuestDB 使用项目内前向迁移执行器，避免 Alembic 默认版本表与 QuestDB 类型、约束和 `DELETE` 能力不兼容。

## PostgreSQL / Alembic

`backend/migrate/versions/` 当前保留：

```text
000000000001_initial_schema.py
000000000002_storage_cluster_transport.py
```

`000000000001` 是 root baseline，从空库创建当前业务表，其中包含 `storage_clusters`、`group_tags` 及 `aggregates`、`volumes`、`qtrees`、`groups`、`storage_usages` 的集群关系。`000000000002` 是当前 head，为 `storage_clusters` 增加非空字段 `protocol` 和 `tls_verify`。

迁移前已有行写入 `protocol='https'`、`tls_verify=false`，保持原连接行为；完成回填后，新行数据库默认值为 `https/true`。HTTP 下 TLS 校验不适用，设备凭据会以明文传输，只应在可信隔离网络中使用。QuestDB 不涉及本次迁移。

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini heads
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini history
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
```

已处于 `000000000001` 的数据库可以正常执行 `upgrade head`。使用已删除旧 revision 链的开发数据库仍不支持原地接续；确认数据可丢弃后重建空数据库，再执行 `upgrade head`，不得手工修改 `alembic_version` 伪造升级路径。

降级到 `000000000001` 会删除逐集群协议和 TLS 校验字段，仅用于测试环境；`downgrade base` 仅用于空库往返验证，不作为保留开发数据的回滚方案。

## QuestDB

`backend/questdb/migrations/` 当前保留：

```text
000000000001_initial_schema.sql
000000000002_add_soft_quota_metrics.sql
```

`000000000001` 从空 QuestDB 创建当前 `7` 张趋势表；`000000000002` 为 Volume、Qtree、Project、Group 和用户用量历史表补充软限额指标。迁移执行器会先创建 `diskpulse_schema_migrations`，记录 revision、SHA-256 checksum 和应用时间；重复执行会跳过已应用 revision，已应用文件被修改或数据库存在本地未知 revision 时会拒绝继续。

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m questdb.migrate history
..\.venv\Scripts\python.exe -m questdb.migrate current
..\.venv\Scripts\python.exe -m questdb.migrate upgrade
Pop-Location
```

`database.create_tables=true` 时，API 启动会在 PostgreSQL `create_all()` 后执行 QuestDB `upgrade`。生产部署仍应先通过单一迁移节点执行命令，再启动 API/worker。

QuestDB migration 为前向、幂等 DDL：每个新 revision 必须使用 `IF NOT EXISTS` 等可重试语句，并在所有语句成功后才写版本账本。QuestDB 不支持 PostgreSQL 式事务回滚和 PGWire `DELETE`，因此不提供自动 downgrade；破坏性回退必须先备份，再使用独立修复 revision 或重建实例。

本次 NetApp/Isilon 资源映射不修改 PostgreSQL 或 QuestDB schema，因此不新增 revision。历史 `isilon_cluster` Aggregate 和 `null` Qtree 由成功的设备采集在当前 PostgreSQL 事务内清理；QuestDB 历史指标保留，新采集不再写入占位资源。

## 已验证与待验证

- PostgreSQL 当前包含 `000000000001` 和 `000000000002` 两个 revision，`000000000002` 为唯一 head。
- SQLite online migration 已验证 `000000000002` upgrade、已有行 `https/false` 回填、新行 `https/true` 默认值和 downgrade；Alembic head 检查通过。
- SQLite、PostgreSQL、MySQL offline SQL 编译通过，并确认新行使用 `DEFAULT true`、旧行执行 `UPDATE false`；尚未在真实 PostgreSQL/MySQL 执行迁移。
- QuestDB migration 契约测试验证初始 revision 与当前 `QuestDBBase.metadata` 的 `7` 张表一致、`000000000002` 可从已有 `000000000001` 环境升级、重复升级安全、checksum 漂移会失败。
- 当前配置指向的 QuestDB 已验证 `current=000000000002`，包含 `7` 张趋势表和 `diskpulse_schema_migrations`；重复 `upgrade` 返回 `up to date`。
- 尚未在空白 QuestDB 实例执行从 `base` 到 head 的独立录像式验收；当前实例的首次创建可能由运行中的自动重载服务触发。
