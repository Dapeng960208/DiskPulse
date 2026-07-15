# StorageCluster 数据库版本管控与初始化

## 适用范围

PostgreSQL 与 QuestDB 使用独立 revision 链。PostgreSQL 由 Alembic 管理；QuestDB 使用项目内前向迁移执行器，避免 Alembic 默认版本表与 QuestDB 类型、约束和 `DELETE` 能力不兼容。

## PostgreSQL / Alembic

`backend/migrate/versions/` 当前保留：

```text
000000000001_initial_schema.py
000000000002_storage_cluster_transport.py
000000000003_ai_chat.py
000000000004_storage_health.py
```

`000000000001` 是 root baseline；`000000000002` 增加逐集群连接配置；`000000000003` 增加 AI 配置、会话、消息和审计表；`000000000004` 是当前 head，增加存储健康事件字段、约束和索引。

历史版本曾在 `database.create_tables=true` 时先执行 PostgreSQL `create_all()`，可能出现 AI 四表已完整创建、Alembic 仍停在 `000000000002` 的状态。`000000000003` 会核对四表及字段后安全接管；只存在部分表或字段不匹配时会拒绝升级，不得手工修改 `alembic_version` 绕过检查。

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
000000000003_storage_performance_metrics.sql
```

`000000000001` 创建容量趋势表；`000000000002` 补充软限额指标；`000000000003` 增加保留 180 天的存储性能指标表。迁移执行器会先创建 `diskpulse_schema_migrations`，记录 revision、SHA-256 checksum 和应用时间；重复执行会跳过已应用 revision，已应用文件被修改或数据库存在本地未知 revision 时会拒绝继续。

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m questdb.migrate history
..\.venv\Scripts\python.exe -m questdb.migrate current
..\.venv\Scripts\python.exe -m questdb.migrate upgrade
Pop-Location
```

`database.create_tables=true` 时，API 启动只执行 QuestDB `upgrade`。PostgreSQL 必须先通过单一迁移节点执行 Alembic，再启动 API/worker；应用启动不再调用 `create_all()` 绕过版本账本。

QuestDB migration 为前向、幂等 DDL：每个新 revision 必须使用 `IF NOT EXISTS` 等可重试语句，并在所有语句成功后才写版本账本。QuestDB 不支持 PostgreSQL 式事务回滚和 PGWire `DELETE`，因此不提供自动 downgrade；破坏性回退必须先备份，再使用独立修复 revision 或重建实例。

本次 NetApp/Isilon 资源映射不修改 PostgreSQL 或 QuestDB schema，因此不新增 revision。历史 `isilon_cluster` Aggregate 和 `null` Qtree 由成功的设备采集在当前 PostgreSQL 事务内清理；QuestDB 历史指标保留，新采集不再写入占位资源。

## 已验证与待验证

- PostgreSQL 当前唯一 head 为 `000000000004`；已验证从 AI 表由历史 `create_all()` 预建、revision 停在 `000000000002` 的真实 PostgreSQL 环境升级成功。
- SQLite online migration 已验证 `000000000002` upgrade、已有行 `https/false` 回填、新行 `https/true` 默认值和 downgrade；Alembic head 检查通过。
- SQLite、PostgreSQL、MySQL offline SQL 编译通过，并确认新行使用 `DEFAULT true`、旧行执行 `UPDATE false`；尚未在真实 PostgreSQL/MySQL 执行迁移。
- QuestDB migration 契约测试验证初始 revision 与当前 `QuestDBBase.metadata` 的 `7` 张表一致、`000000000002` 可从已有 `000000000001` 环境升级、重复升级安全、checksum 漂移会失败。
- 当前配置指向的 QuestDB 已验证 `current=000000000003`，包含 `diskpulse_schema_migrations` 和存储性能指标表。
- 尚未在空白 QuestDB 实例执行从 `base` 到 head 的独立录像式验收；当前实例的首次创建可能由运行中的自动重载服务触发。
