# 未使用字段审计（2026-07-13）

## 结论

- 本轮静态审计覆盖 `backend/models.py` 中 `14` 个 ORM 模型、`221` 个数据库字段，以及后端 router/CRUD/service/Celery、前端 `frontend/src` 的字段读写链路。
- 共识别 `25` 个清理候选：本轮已安全删除 `20` 个没有业务读写的字段和 `4` 个运行时不生效的 QuestDB 重复配置字段；`1` 个没有业务语义的单例配置名称字段继续保留。
- `ProjectStorageEnvironment` 的身份、绑定、容量、状态和采集时间字段均有明确链路；本次没有发现可直接归入“未使用”的环境核心字段。
- 清理已同步 ORM、Pydantic schema、配置 API、管理设置页和单一 Alembic initial baseline；项目仍在开发阶段，没有历史数据回填、字段废弃周期或外部兼容过渡代码。

## 审计口径

以下情况才计为字段被业务使用：

- CRUD、service 或 Celery 对字段进行查询、过滤、更新或业务判断。
- 前端页面读取、展示、筛选或提交字段。
- 字段承担已记录的运行时语义，例如采集状态、告警状态或最近成功采集时间。

仅出现在 ORM 定义、Pydantic schema、Alembic migration、测试或文档中，不单独视为业务使用。审计未连接真实数据库，也未统计仓库外 API 消费者。

## 确认没有业务读写的字段

共 `20` 个。

| 模型 | 字段 | 证据 | 处置 |
| --- | --- | --- | --- |
| `Project` | `ncpus`、`max_jobs`、`cpuf`、`max_mem`、`mem`、`mem_reserved`、`slot`、`slot_reserved`、`run_jobs`、`ssusp_jobs`、`ususp_jobs`、`pend_jobs` | 仅由 ORM 和 `projectsSchema.py` 暴露；`ProjectUpdate`、`projectsCrud.py`、Celery 和前端均不读写这些字段。 | 已从 ORM、API schema 和迁移中删除。 |
| `User` | `run_jobs`、`ssusp_jobs`、`pend_jobs`、`done_jobs`、`exit_jobs` | `UserBase` 接收并校验这些字段，但 `usersCrud.create_user()` 不写入，更新接口、Celery 和前端也不消费。 | 已删除字段、schema 默认值、校验器和迁移列。 |
| `Host` | `status`、`updated_at` | 当前有效后台链路只通过 `Group.monitor_host_id` 读取 `Host.ip`；没有任何状态更新、过滤或展示。 | 保留 `Host.id`、`Host.name`、`Host.ip`，已删除这两个字段。 |
| `StorageBackUpRecord` | `is_deleted` | 备份生命周期完全由 `status` 表示；该字段只存在于 ORM 和响应 schema，没有查询、写入或前端展示。 | 已删除字段和 schema 声明，生命周期继续使用 `status`。 |

## 运行时不生效的重复配置字段

共 `4` 个：

```text
StorageConf.questdb_host
StorageConf.questdb_port
StorageConf.questdb_user
StorageConf.questdb_password
```

清理前这些字段可通过管理页面和 `/config/storage` 保存，但 QuestDB engine 实际由 `backend/appConfig.py` 从 `config.yml` 的 `database.questdb` 构建。`QuestDBSession(config=...)` 虽接收数据库配置对象，建立连接时仍直接使用全局 `QuestDBSessionLocal`，不会读取上述四个字段。

现已以后端 YAML 为唯一 QuestDB 连接配置源，并从 `StorageConf`、配置 API schema、设置页面和 initial baseline 删除这四个无效字段；没有新增第二套动态重连逻辑。

## 无业务语义的结构字段

`StorageConf.name` 只在创建首条配置时写入固定值 `storage conf`，配置读取始终使用 `first()`，没有按名称查询、选择或展示。该字段不参与任何业务判断，但不属于本轮指定的两类字段，继续保留，后续可单独删除。

## 已复核但暂不列入清理

| 字段 | 保留原因 |
| --- | --- |
| `ProjectStorageEnvironment.created_at`、`ProjectStorageEnvironment.updated_at` | 当前主要用于 API 审计元数据；没有前端展示。若确定不需要创建/修改审计，可在实施清理时一并删除，但本轮不把标准审计时间戳判定为确认未用。 |
| `ProjectStorageEnvironment.last_collected_at` | 记录最近一次成功采集时间；采集失败时仍需保留上次成功时间，属于已明确的运行时语义。 |
| `Host.name` | 前端 `HostsSelect.vue` 需要主机名，但后端当前未挂载 `/hosts` router。应先决定恢复 Host 管理接口还是让选择器改用现有数据源，再决定字段去留。 |
| `StorageUsage.birth_time` | 采集解析会写入，虽然当前页面未展示，仍属于已落库的文件元数据，不是完全未使用字段。 |

## 跟踪状态

- [x] 完成 ORM 字段清单和生产代码静态扫描。
- [x] 人工复核低引用字段的 CRUD、Celery、配置和前端链路。
- [x] 复核项目存储环境新增字段，未发现未使用的环境核心字段。
- [x] 明确开发阶段不考虑历史数据回填、字段废弃周期和外部兼容过渡。
- [x] 删除 `24` 个确认字段并同步 schema、前端、迁移和聚焦测试。
- [ ] 单独决定是否删除 `StorageConf.name`。

## 验证

- RED：后端字段契约因旧字段仍存在而失败；前端设置页契约因仍显示“时序数据库配置”而失败。
- GREEN：确认删除字段未进入 ORM 和 `000000000001`；单一 baseline 在 SQLite upgrade 后与 `Base.metadata` 无差异，PostgreSQL offline DDL 编译通过。
- GREEN：`cd frontend; npx vitest run test/unit/settings-config.test.js --coverage.enabled=false` 通过，`2` 个测试。
- 最终全量验证：后端 `146 passed`、`41 warnings`，覆盖率 `85%`（`2892` statements、`444` miss）；前端 `30` 个测试文件、`153 passed`，覆盖率 statements `93.47%`、branches `83.56%`、functions `82.11%`、lines `93.47%`。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads` 和 `history` 通过，唯一 root/head 为 `000000000001`；`compileall -q backend`、`cd frontend; npm run lint` 和 `cd frontend; npm run build:prod` 通过。
- 尚未在真实 PostgreSQL 空库执行 initial baseline upgrade/downgrade。
