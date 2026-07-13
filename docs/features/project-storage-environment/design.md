# DiskPulse 项目多存储环境统一展示优化方案

> 文档状态：已实施，待生产与外部验证
> 适用范围：`D:\dev\DiskPulse`
> 核心场景：一个项目包含四套相互独立的存储环境，其中两套 Isilon、两套 NetApp。

## 1. 结论

前端、后端、PostgreSQL、QuestDB、采集聚合、告警、扩容、备份和文档都需要同步修改。

目标关系为：

~~~mermaid
erDiagram
    PROJECT ||--o{ PROJECT_STORAGE_ENVIRONMENT : has
    STORAGE_CLUSTER ||--o{ PROJECT_STORAGE_ENVIRONMENT : provides
    PROJECT_STORAGE_ENVIRONMENT ||--o{ GROUP : contains
    STORAGE_CLUSTER ||--o{ VOLUME : owns
    VOLUME ||--o{ QTREE : contains
    GROUP }o--o| VOLUME : binds
    GROUP }o--o| QTREE : binds
    GROUP ||--o{ STORAGE_USAGE : contains
~~~

核心原则：

1. `Project` 表示项目。
2. `ProjectStorageEnvironment` 表示项目的一套独立存储环境。
3. 每套环境只绑定一个 `StorageCluster`。
4. 一个项目可以配置多套环境。
5. 一个项目组只能属于一个环境。
6. 项目组可以绑定一个 Volume 或一个 Qtree。
7. Isilon 直接绑定 Volume/目录配额，不再创建假 Qtree。
8. 环境数据独立统计；项目级合计只作信息展示，不作为环境告警或扩容依据。

### 1.1 可行性结论与实施门槛

方案已在现有 FastAPI、SQLAlchemy、Celery、Vue 3 和 Vitest 技术栈内实施，不需要新增前端依赖，也没有为配置快照新增 Redis 缓存。当前自动化范围已完成，生产数据库审计、migration 演练和外部系统验证仍待执行。

实施成功标准：

- 一个项目的多套环境在关系、当前容量、趋势、告警、扩容、备份和页面状态中均可独立追溯。
- Celery 每轮使用同一份数据库配置快照，下一轮能够读取已经提交的新配置，不发生跨环境陈旧写入。
- 新旧字段兼容期内可回滚；数据审计未通过时不得自动回填或收紧约束。
- 每个生产批次都完成预期 RED、最小 GREEN 和同目标复测；未验证内容不标记为完成。

前置依赖与停止条件：

- 数据审计、生产 `alembic_version`、环境当前态字段和第 7.4 节前端契约未确认时，停止在实施前。
- RED 若由语法、测试装配、依赖缺失或无关回归导致，不算有效 RED，停止修改生产代码。
- 上游 migration、API 或聚合批次未 GREEN 时，下游不得用 speculative mock 契约越级交付。
- 迁移审计发现项目、集群或 Qtree 关系不一致时，生成修复清单并停止自动回填。
- PostgreSQL、QuestDB、Redis 或真实存储设备不可用时，只能完成不依赖它们的自动化验证，相关集成验收保持“待验证”。

## 2. 当前设计问题

| 问题 | 当前实现 | 影响 |
| --- | --- | --- |
| 缺少环境层 | `Project` 直接关联 `Group` | 无法表达同一项目的四套独立存储环境 |
| 项目组只能绑定 Qtree | `Group` 只有 `qtree_id` | Isilon 和 NetApp Volume 级资源无法自然关联 |
| Isilon 使用假 Qtree | 为 Volume 创建 `name='null'` 的 Qtree | 厂商兼容逻辑污染领域模型 |
| 关系字段重复 | Group 同时保存 `project_id`、`storage_cluster_id`、`qtree_id` | 项目、集群、Qtree 可能互相不匹配 |
| 缺少跨资源校验 | Group CRUD 直接写入请求字段 | 可以把 Qtree 关联到错误的集群 |
| 项目统计混合环境 | 按 `Group.project_id` 汇总 | 四套环境无法独立查看、告警和分析 |
| 前端固定展示 Qtree | 列表、详情直接读取 `group.qtree.volume` | Volume 绑定会导致空值或页面异常 |
| 备份目录没有环境层 | `项目/项目组/用户` | 不同环境下同名项目组可能发生目录冲突 |
| 时序数据缺少环境维度 | QuestDB 只有 Project、Group 趋势 | 无法展示某个项目在单独环境中的历史趋势 |

## 3. 领域术语

现有术语文档把 `Project` 和 `Group` 都描述为“项目组”，实施时应调整为：

| 中文术语 | 模型 | 说明 |
| --- | --- | --- |
| 项目 | `Project` | 业务项目，包含多套存储环境 |
| 项目存储环境 | `ProjectStorageEnvironment` | 项目在某个 StorageCluster 上的独立资源空间 |
| 存储集群 | `StorageCluster` | 一套 NetApp 或 Isilon 设备配置 |
| 项目组 | `Group` | 某套项目环境下的业务分组 |
| 存储目标 | `Volume` / `Qtree` | 项目组实际绑定的容量资源 |
| 用户目录 | `StorageUsage` | 项目组下的用户配额和使用记录 |

环境名称不硬编码为枚举，默认可使用集群名称。数据库和 API 使用环境 ID，环境改名不会影响关系。

## 4. PostgreSQL 数据模型

### 4.1 新增项目存储环境表

~~~sql
CREATE TABLE project_storage_environments (
    id                  INTEGER PRIMARY KEY,
    project_id          INTEGER NOT NULL,
    storage_cluster_id  INTEGER NOT NULL,
    name                VARCHAR(128) NOT NULL,
    description         TEXT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    limit               DOUBLE PRECISION NULL,
    soft_limit          DOUBLE PRECISION NULL,
    used                DOUBLE PRECISION NULL,
    use_ratio           DOUBLE PRECISION NULL,
    soft_use_ratio      DOUBLE PRECISION NULL,
    collection_status   VARCHAR(16) NOT NULL DEFAULT 'pending',
    last_collected_at   TIMESTAMP NULL,
    created_at          TIMESTAMP NOT NULL,
    updated_at          TIMESTAMP NOT NULL,

    CONSTRAINT fk_project_storage_environment_project
        FOREIGN KEY (project_id) REFERENCES projects(id),
    CONSTRAINT fk_project_storage_environment_cluster
        FOREIGN KEY (storage_cluster_id) REFERENCES storage_clusters(id),
    CONSTRAINT uq_project_storage_environment_project_name
        UNIQUE (project_id, name),
    CONSTRAINT uq_project_storage_environment_project_cluster
        UNIQUE (project_id, storage_cluster_id),
    CONSTRAINT ck_project_storage_environment_collection_status
        CHECK (collection_status IN ('pending', 'success', 'failed'))
);
~~~

建议索引：

- `(project_id, is_active, id)`
- `(storage_cluster_id, project_id)`
- `(project_id, collection_status, is_active)`

`UNIQUE(project_id, name)` 已提供相同列前缀索引，不再重复创建 `(project_id, name)` 普通索引。所有参与唯一键或索引的字符串使用有界长度；migration 中 FK、UNIQUE、CHECK 和索引均使用稳定名称，SQLite 变更使用 Alembic `batch_alter_table`。

当前态字段说明：

- `limit`、`soft_limit`、`used`、`use_ratio`、`soft_use_ratio` 是环境 summary 和 Project 合计的 PostgreSQL 持久化落点，避免 API 临时拼接多张表。
- `collection_status` 只允许 `pending`、`success`、`failed`，`last_collected_at` 记录最近一次成功采集时间。
- 采集失败时保留上次成功容量和 `last_collected_at`，仅把状态改为 `failed`；错误详情写服务端日志，不把设备返回、凭据或敏感异常文本写入数据库或 API。

删除规则：

- 环境下存在 Group 时禁止删除环境，返回 `409 Conflict`。
- StorageCluster 已绑定项目环境时禁止删除集群。
- 停用环境使用 `is_active=false`，不直接删除历史数据。

### 4.2 修改 Group

新增字段：

~~~text
project_environment_id  FK project_storage_environments.id
volume_id               FK volumes.id，nullable
qtree_id                FK qtrees.id，nullable
~~~

目标状态：

~~~text
groups
  id
  project_environment_id
  volume_id
  qtree_id
  name
  linux_path
  associate_multiple_groups
  enable_monitoring
  ...
~~~

数据库约束：

~~~sql
CONSTRAINT ck_group_single_storage_target
  CHECK (volume_id IS NULL OR qtree_id IS NULL);
CONSTRAINT ck_group_monitored_has_storage_target
  CHECK (enable_monitoring = FALSE OR volume_id IS NOT NULL OR qtree_id IS NOT NULL);
CONSTRAINT uq_group_environment_name
  UNIQUE (project_environment_id, name);
~~~

业务层校验：

- `enable_monitoring=true` 时，`volume_id` 和 `qtree_id` 必须且只能有一个。
- Isilon 环境只允许绑定 Volume。
- NetApp 环境允许绑定 Volume 或 Qtree。
- Volume/Qtree 必须属于环境绑定的 StorageCluster。
- 绑定 Qtree 时，其 Volume 必须属于同一 StorageCluster。
- `project_id` 和 `storage_cluster_id` 不再由前端提交。

迁移期间暂时保留 `groups.project_id` 和 `groups.storage_cluster_id`，仅作为兼容和回滚字段，由后端自动维护。稳定后再删除。

### 4.3 Volume 与 Qtree 唯一标识

建议增加：

~~~text
volumes:
  external_key
  UNIQUE(storage_cluster_id, external_key)

qtrees:
  UNIQUE(volume_id, name)
~~~

`external_key` 来源：

- NetApp：优先使用设备返回的 Volume UUID。
- Isilon：优先使用 quota ID；无法取得时使用规范化目录路径。

### 4.4 StorageUsage

PostgreSQL 不增加更多重复的项目、环境和集群字段，统一从以下关系推导：

~~~text
StorageUsage
  → Group
  → ProjectStorageEnvironment
  → Project / StorageCluster
~~~

增加 `UNIQUE(group_id, user_id)` 约束。

## 5. QuestDB 时序模型

新增环境级趋势表：

~~~text
project_environment_storage_usages
  project_environment_id  SYMBOL
  used                    DOUBLE
  used_ratio              DOUBLE
  updated_at              TIMESTAMP
~~~

主键维度为 `(project_environment_id, updated_at)`。

现有表处理：

- `group_storage_usages` 继续按 Group 记录，不重复增加环境 ID。
- `project_storage_usages` 保留，表示项目所有环境的总合计。
- 新环境趋势表作为项目详情的默认 operational 视图。
- 项目总趋势只作汇总展示，不用于判断某个环境是否需要扩容。

## 6. 聚合规则

### 6.1 项目组

| 绑定方式 | 项目组指标来源 |
| --- | --- |
| Volume | 使用 Volume 的容量指标 |
| Qtree | 使用 Qtree 的容量指标 |
| `associate_multiple_groups=true` | 从该 Group 下的 `StorageUsage` 汇总 |

禁止将同一个 Volume 的完整使用量复制给多个普通 Group，否则项目和环境会重复计算。

### 6.2 项目环境

~~~text
环境 limit       = SUM(环境内有效 Group.limit)
环境 used        = SUM(环境内有效 Group.used)
环境 soft_limit  = SUM(环境内有效 Group.soft_limit)
环境 use_ratio   = used / limit
~~~

每个 StorageCluster 采集完成后，只更新属于该集群的项目环境。

### 6.3 项目合计

~~~text
项目总量 = SUM(项目所有启用环境在同一完整成功轮次的汇总值)
~~~

只有某 Project 的所有启用环境在本轮均成功时，才刷新该 Project 的 current totals 和时间戳。任一启用环境失败或未完成时，该 Project 全部保留上一完整成功轮次的 current totals 和时间戳，禁止用本轮成功环境的部分合计覆盖。

建议执行顺序：

1. 每个 `StoragePulseMonitor` 只更新当前集群和对应环境。
2. 所有集群采集完成后，由任务入口检查每个 Project 的全部启用环境；仅完整成功的 Project 统一计算一次总量。
3. 避免每个集群采集器重复写全局 Project 汇总。

现有硬限额告警行为保持不变，继续使用 `use_ratio`；软限额只展示，不改变告警语义。

### 6.4 Celery 配置读取与事务边界

当前生产入口为 `backend/celery_tasks/tasks/storages.py` 创建的 `StoragePulseMonitor`。现状没有跨 Celery 任务的全局缓存，但同一轮采集存在以下问题：

- 一个 `DBSession` 查询 active `StorageCluster` ORM 后串行运行所有集群，Monitor 构造器又查询并长期保存 ORM 实例；API 在任务运行中提交的配置可能形成新旧关系混用。
- User、StorageUsage、Group、Qtree 依赖懒加载，存在 N+1；多个循环内逐行 `commit()`。
- 单集群异常后继续复用可能已经 failed 的 Session，后续集群会被连带影响；客户端也没有统一 `finally` 关闭。
- Project 汇总由每个 Monitor 重复执行一次，集群越多重复查询和写入越多。
- 分布式锁 TTL 为 120 秒，短于任务 hard limit 180 秒，四集群串行时可能在旧任务未结束前再次获得锁。

首版采用数据库短会话快照，不增加缓存层：

1. 每轮任务创建新的短只读 Session，用一次有界标量 JOIN 读取 active StorageCluster、active ProjectStorageEnvironment、`enable_monitoring=true` 的 Group、Volume/Qtree 目标及聚合所需字段。
2. 使用 SQLAlchemy `mappings()` 折叠为普通不可变 dict/DTO 后立即关闭读取 Session；不得把 ORM 实例带出 Session，也不得把含连接凭据的快照发送到 Redis 或 Celery broker。
3. 快照创建前已经提交的配置本轮生效；快照创建后的变更在下一次成功取得锁并创建快照的采集轮次生效。当前 60 秒只是 nominal beat interval，不是配置传播 SLA。
4. 每个集群使用独立写 Session 和 `with db.begin()`；Monitor 内只 `flush()`，不在循环中 `commit()`。失败时 rollback，`finally` 关闭设备客户端，然后继续无关集群。
5. 快照后 Group 被移动、停用或删除时，写入必须使用 `id + project_environment_id + enable_monitoring=true` 条件；`rowcount=0` 直接跳过，禁止依据旧快照重新创建或写回旧环境。环境汇总同样使用 `id + storage_cluster_id + is_active=true` 条件。
6. PostgreSQL 成功提交后再写 QuestDB。QuestDB 失败记录可重试错误，不回滚 PostgreSQL，也不伪装跨库事务。
7. 所有集群完成后，使用新的短 Session 检查各 Project。只有全部启用环境均成功的 Project 才刷新一次合计；任一启用环境失败或未完成时，该 Project 的 current totals 和时间戳全部保留上一完整成功轮次。
8. 先从设备响应收集用户名/UID，再用一次 `IN` 查询批量解析 User；StorageUsage 关联使用标量映射并复用整轮 Group/目标快照，禁止每集群全量加载 User 或访问 `su.group.qtree` 触发懒加载。
9. 实施时必须保证锁 TTL 大于 hard limit；真实四集群只读计时完成后，再决定是否把集群采集拆成并行子任务。全部集群失败时任务必须失败；部分失败至少输出成功/失败集群汇总。

不修改全局 `SessionLocal.expire_on_commit`。标量快照和短会话已经解决陈旧 ORM 问题，全局切换会扩大 API 行为影响面。首版也不增加 Redis 配置缓存、配置版本号或变更事件；只有出现以下任一证据时再升级：

- 业务要求配置变更具备有界或秒级 SLA，不能等待下一次成功取得锁并创建快照的采集轮次。
- 快照 JOIN 经实测成为瓶颈。
- 单轮采集 p95 超过调度周期，需要并行拆分。
- 必须证明所有环境指标来自严格相同的 collection round。

## 7. API 方案

统一前缀继续使用 `/storage-pulse/api`。

权限契约必须在 G0 冻结。当前仓库没有 project admin/editor/reader 成员模型，首版最小方案为：环境和关联资源写操作仅超级管理员；项目环境读操作允许超级管理员、`Project.in_charge_user_id` 或 `Project.pt_user_id` 对应用户。若产品需要更多项目成员访问，必须先新增并测试成员关系，不能在文档中先声明不存在的角色。

### 7.1 环境接口

| 方法 | 接口 | 说明 |
| --- | --- | --- |
| `GET` | `/projects/{project_id}/storage-environments` | 获取项目环境 |
| `POST` | `/projects/{project_id}/storage-environments` | 新增项目环境 |
| `GET` | `/storage-environments/{environment_id}` | 获取环境详情 |
| `PUT` | `/storage-environments/{environment_id}` | 修改环境 |
| `DELETE` | `/storage-environments/{environment_id}` | 删除空环境 |
| `GET` | `/storage-environments/{environment_id}/summary` | 当前容量汇总 |
| `GET` | `/storage-environments/{environment_id}/realtime` | 环境趋势 |

创建请求：

~~~json
{
  "name": "NetApp-环境-01",
  "storage_cluster_id": 3,
  "description": "项目 A 的第一套 NetApp 环境",
  "is_active": true
}
~~~

响应不得包含 StorageCluster 密码：

~~~json
{
  "id": 10,
  "project_id": 1,
  "name": "NetApp-环境-01",
  "is_active": true,
  "limit": 10240,
  "soft_limit": 9216,
  "used": 6144,
  "use_ratio": 60,
  "soft_use_ratio": 66.67,
  "collection_status": "success",
  "last_collected_at": "2026-07-13T14:00:00",
  "storage_cluster": {
    "id": 3,
    "name": "NetApp-Cluster-01",
    "storage_type": "netapp"
  }
}
~~~

### 7.2 Group 接口

`GET /groups` 增加以下过滤参数：

~~~text
project_id
project_environment_id
storage_cluster_id
volume_id
qtree_id
nameLike
page
size
~~~

创建或修改 Group：

~~~json
{
  "project_environment_id": 10,
  "name": "芯片设计组",
  "volume_id": null,
  "qtree_id": 35,
  "linux_path": "/project/chip-design",
  "associate_multiple_groups": false,
  "enable_monitoring": true
}
~~~

前端不再提交 `project_id` 和 `storage_cluster_id`。

响应增加统一展示字段：

~~~json
{
  "id": 21,
  "name": "芯片设计组",
  "project_environment": {
    "id": 10,
    "name": "NetApp-环境-01"
  },
  "storage_cluster": {
    "id": 3,
    "name": "NetApp-Cluster-01",
    "storage_type": "netapp"
  },
  "storage_target": {
    "type": "qtree",
    "id": 35,
    "name": "IC_design",
    "volume_name": "project_volume"
  }
}
~~~

### 7.3 稳定错误

| 状态码 | 场景 |
| --- | --- |
| `404` | Project、Environment、Cluster、Volume、Qtree 不存在 |
| `409` | 同一项目重复绑定 StorageCluster |
| `409` | 删除仍包含 Group 的环境 |
| `422` | Volume 和 Qtree 同时填写或均未填写 |
| `422` | 存储目标不属于环境对应集群 |
| `422` | Isilon 环境绑定 Qtree |
| `403` | 用户不满足 G0 冻结的超级管理员或项目负责人读取范围 |

本次不顺带重构全站错误 envelope，只保证新接口错误码和文案稳定。

### 7.4 前端契约冻结清单

以下契约未冻结前，对应前端批次不得进入 GREEN。字段命名和 envelope 以最终后端 schema 为准，Mock 必须逐字段匹配，不自行补兼容分支。

| 契约 | 实施前必须确认 |
| --- | --- |
| Project 列表 | 分页 envelope；环境数量、集群类型摘要、总容量/使用量、`pending/success/failed` 和停用环境数量的字段名 |
| Environment 列表 | `/projects/{project_id}/storage-environments` 的 list envelope、排序规则、是否包含当前态和脱敏 StorageCluster 摘要 |
| Environment summary/realtime | summary 当前态字段；realtime 与现有 `RealTimePage` 对齐为 `{ info, data }`，`info` 至少包含环境名、容量、状态和最近成功采集时间 |
| Group | `project_environment_id` 过滤；`project_environment`、脱敏 `storage_cluster`、统一 `storage_target` 响应；创建/修改只接受环境和一个目标 ID |
| StorageUsage/export | 项目、环境、Group、集群和用户过滤参数；列表字段；导出列名与顺序；集群是否只由 Group 推导 |
| Dashboard | 项目/环境筛选参数、endpoint、返回 envelope、系列 key；同名 Group 的稳定唯一 key |
| Alert | 环境列表筛选使用 `related_type=ProjectStorageEnvironment + related_id`，还是独立 `project_environment_id` 参数；周报分组响应 |
| URL 状态 | `?environment_id=` 缺失时选择第一个启用环境；ID 无效、属于其他项目或已停用时回退第一个启用环境并规范化 URL；无启用环境时清除参数并展示空状态 |

`collection_status` 是页面“采集异常”计数的唯一结构化来源；错误详情只读服务端日志，前端不得依赖敏感错误文本。

## 8. 后端修改范围

### 8.1 新增文件

~~~text
backend/schemas/projectStorageEnvironmentSchema.py
backend/crud/projectStorageEnvironmentCrud.py
backend/services/projectStorageEnvironmentService.py
backend/services/groupService.py
backend/routers/project_storage_environment.py
backend/test/test_project_storage_environment.py
backend/test/test_project_storage_environment_migration.py
backend/test/test_group_storage_binding.py
backend/test/test_project_environment_aggregation.py
backend/migrate/versions/<revision>_add_project_storage_environments.py
~~~

### 8.2 修改模块

| 文件/模块 | 修改内容 |
| --- | --- |
| `backend/models.py` | 新增环境模型和当前态/采集状态字段；修改 Project、Group 关系 |
| `backend/main.py` | 注册环境 Router |
| `backend/requirements.txt` | 补充并固定 Alembic 运行依赖；不得依赖开发机隐式安装 |
| `backend/schemas/groupSchema.py` | 增加环境和 Volume 绑定字段 |
| `backend/crud/groupCrud.py` | 支持环境、Volume、Qtree 过滤 |
| `backend/routers/group.py` | 改由 Service 完成跨资源校验 |
| `backend/crud/projectsCrud.py` | 项目汇总按环境聚合 |
| `backend/routers/projects.py` | 项目详情返回环境摘要 |
| `backend/questdb/models.py` | 新增环境趋势表 |
| `backend/crud/questDbCrud.py` | 支持环境趋势查询 |
| `backend/celery_tasks/manager/storagePulseMonitor.py` | 去除假 Qtree，增加环境聚合 |
| `backend/celery_tasks/tasks/storages.py` | 每轮加载一次标量配置快照；隔离每集群事务；全部集群采集后统一汇总一次 Project |
| `backend/celery_tasks/manager/storageAlert.py` | 支持环境维度和 Volume 绑定 |
| `backend/celery_tasks/manager/remoteFileManager.py` | 备份路径增加环境目录 |
| `backend/routers/storage_usage.py` | 扩容逻辑支持 Volume/Qtree |
| `backend/crud/storageClusterCrud.py`、`backend/routers/storage_cluster.py` | 被环境引用时提供稳定删除保护 |
| `backend/crud/volumeCrud.py`、`backend/routers/volumes.py` | 被 Group 引用时提供稳定删除保护 |
| `backend/crud/qtreeCrud.py`、`backend/routers/qtrees.py` | 被 Group 引用时提供稳定删除保护 |
| 导出 CRUD/Schema | 增加项目环境字段 |

### 8.3 存储目标解析

增加一个共享解析函数 `resolve_group_storage_target(group)`，统一返回：

~~~text
target_type
target
volume
storage_cluster
~~~

扩容、告警、详情、采集和邮件都复用这个函数，避免每个调用点分别判断 `volume_id/qtree_id`。

### 8.4 旧监控代码

- 完整实现只放在当前生产入口 `StoragePulseMonitor`。
- `NetAppMonitor`、`IsilonMonitor`、`StoreMonitor` 先确认是否仍有生产入口。
- 未使用则后续删除；本轮只做保证导入和测试不报错的最小兼容。
- 不在多套监控器中复制相同环境聚合逻辑。

## 9. 前端优化方案

### 9.1 项目列表

| 列 | 内容 |
| --- | --- |
| 项目 | 项目名称 |
| 存储环境 | 环境数量，例如 `4` |
| 存储集群 | 两套 Isilon、两套 NetApp 的摘要 |
| 总容量 | 所有环境合计，仅供总览 |
| 总使用量 | 所有环境合计 |
| 环境状态 | 正常、停用、采集异常数量 |
| 操作 | 详情、编辑 |

项目总使用率不能替代环境使用率。

### 9.2 项目详情

项目详情改造成项目工作区：

~~~text
项目 A
四套环境 / 总容量 / 总使用量 / 异常环境

[Isilon-01] [Isilon-02] [NetApp-01] [NetApp-02]

当前环境：
  存储集群信息
  硬限额 / 软限额 / 使用量 / 利用率
  趋势图
  项目组列表
  告警记录
~~~

交互规则：

- 默认选中第一个启用环境。
- 当前环境 ID 写入 URL 查询参数 `?environment_id=10`。
- 刷新或分享链接后保持当前环境。
- 切换环境只请求该环境的摘要、趋势、项目组和告警。
- 环境数量较少，使用页签，不增加全局环境管理菜单。
- 环境新增、编辑、停用入口放在项目详情中。
- 修正当前路由标题“项目组详情”为“项目详情”。

### 9.3 项目环境管理

环境表单字段：

~~~text
环境名称
存储集群
描述
是否启用
~~~

已被当前项目其他环境绑定的集群不可重复选择。

### 9.4 项目组列表与表单

筛选条件调整为：

~~~text
项目
项目环境
存储类型
存储目标类型
Volume/Qtree
项目组名称
~~~

表格增加项目环境、存储类型和统一存储目标列，不再直接读取 `row.qtree.volume.name`，统一使用后端返回的 `row.storage_target`。

表单级联顺序：

~~~text
项目
  → 项目环境
      → 存储目标类型
          → Volume/Qtree
~~~

规则：

- 选择项目后加载其环境。
- 选择环境后自动确定 StorageCluster。
- StorageCluster 只读展示，不允许独立修改。
- Isilon 环境自动固定为 Volume。
- NetApp 环境允许选择 Volume 或 Qtree。
- 上级字段改变时清空所有下级字段。
- Volume/Qtree 查询必须携带 `storage_cluster_id`。
- 提交时只发送 `project_environment_id` 和目标 ID。

### 9.5 用户用量页面

用户用量筛选增加项目、项目环境、项目组、存储集群和用户。

新增用户用量时：

- 先选择项目环境。
- 再选择该环境下的 Group。
- `storage_cluster_id` 从 Group 自动推导。
- 不允许用户独立选择不匹配的 StorageCluster。

导出增加项目、项目环境、存储集群、存储类型、项目组、Volume、Qtree 和 Linux 路径。

### 9.6 Dashboard 与趋势页

Dashboard 调整为 `项目 → 环境 → 项目组`：

- 增加项目和环境筛选。
- 图表系列名称包含环境名。
- 同名 Group 在不同环境中不得合并。
- 项目总览可显示所有环境合计。
- 环境容量图独立显示，不把四套环境拼成一个使用率。

`RealTimePage.vue` 增加 `apiType=project-environment`，同步扩展 `apiMap`、`selectMap`、`relatedTypeMap` 和 validator。

### 9.7 告警、扩容和备份

告警：

- 环境级告警使用 `related_type=ProjectStorageEnvironment`。
- Group 告警展示所属项目和环境。
- 项目周报按环境分节，不只给项目合计。

扩容：

- Group 绑定 Qtree 时扩 Qtree。
- Group 绑定 Volume 时扩 Volume。
- Isilon 使用对应目录配额扩容逻辑。
- 不再通过 `qtree.name='null'` 判断 Volume。

备份路径：

~~~text
旧：
back_up_dir/项目/项目组/用户

新：
back_up_dir/项目/环境/项目组/用户
~~~

已有备份记录保留原始路径，不批量移动历史文件。

## 10. 前端预计修改文件

~~~text
frontend/src/router/routes.js
frontend/src/api/project-api.js
frontend/src/api/group-api.js
frontend/src/api/storage-usage-api.js
frontend/src/api/project-storage-environment-api.js

frontend/src/components/form/ProjectStorageEnvironmentSelect.vue
frontend/src/components/form/StorageClusterSelect.vue
frontend/src/components/form/GroupSelect.vue
frontend/src/components/form/VolumeSelect.vue
frontend/src/components/form/QtreeSelect.vue

frontend/src/pages/project/ProjectListPage.vue
frontend/src/pages/project/ProjectDetailPage.vue
frontend/src/pages/project/components/ProjectTable.vue
frontend/src/pages/project/components/ProjectDiskUsage.vue
frontend/src/pages/project/components/ProjectStorageEnvironmentTable.vue
frontend/src/pages/project/components/ProjectStorageEnvironmentFormDialog.vue

frontend/src/pages/group/GroupListPage.vue
frontend/src/pages/group/GroupDetailPage.vue
frontend/src/pages/group/components/GroupFormDialog.vue

frontend/src/pages/usage/UsageListPage.vue
frontend/src/pages/usage/components/UsageFormDialog.vue
frontend/src/pages/dashboard/DashboardPage.vue
frontend/src/pages/alert/AlertListPage.vue
frontend/src/pages/common/RealTimePage.vue
~~~

不新增 UI 组件库或状态管理依赖。

其中 `project-storage-environment-api.js`、`ProjectStorageEnvironmentSelect.vue`、`ProjectStorageEnvironmentTable.vue` 和 `ProjectStorageEnvironmentFormDialog.vue` 为新增文件，其余为现有文件。`StorageClusterSelect.vue` 需要支持排除当前项目已绑定的集群。`StorageClusterDetailPage.vue` 当前没有该功能的必然调用链；只有需求明确增加“集群反向查看项目环境”时才纳入，首版不修改。

现有测试入口必须同步而不是另起一套测试基础设施：

~~~text
frontend/test/unit/api/modules.test.js
frontend/test/unit/components/select-function-coverage.test.js
frontend/test/unit/components/dialog-function-coverage.test.js
frontend/test/unit/router/routes.test.js
frontend/test/unit/router/routes-dynamic-import.test.js
frontend/test/unit/smoke/components-and-pages.test.js
frontend/test/unit/smoke/surface-regression.test.js
~~~

按四个前端批次计划新增以下聚焦文件；若实现时现有测试文件可以清晰承载同一行为，优先复用现有文件，不为目录对称而新增空壳：

~~~text
frontend/test/unit/project-storage-environment.test.js
frontend/test/unit/group-storage-binding.test.js
frontend/test/unit/project-environment-workspace.test.js
frontend/test/unit/project-environment-usage-alert.test.js
~~~

## 11. 数据迁移方案

### 11.1 迁移前审计

必须统计：

~~~text
Group.project_id 为空数量
Group.storage_cluster_id 为空数量
Group.qtree_id 为空数量
Group 与 Qtree 所属集群不一致数量
name='null' 的 Qtree 数量
同一项目绑定相同集群数量
同一资源关联多个 Group 的数量
重复 StorageUsage(group_id, user_id) 数量
~~~

发现不一致数据时先形成修复清单，不自动猜测所属环境。

### 11.2 M1：Expand 增量结构

1. 创建 `project_storage_environments`。
2. 同表增加环境当前态、`collection_status` 和 `last_collected_at`，初始状态为 `pending`。
3. 给 Group 增加 `project_environment_id`、`volume_id`。
4. Group 新关系字段先允许为空。
5. 不删除旧字段。
6. 创建必要索引。

### 11.3 M2：数据回填

按现有 `(project_id, storage_cluster_id)` 生成环境，默认环境名使用 `StorageCluster.name`。

回填规则：

- 普通 Qtree 保留 `qtree_id`。
- `qtree.name='null'` 转换为 `volume_id=qtree.volume_id`，清空 `qtree_id`。
- Group 没有 StorageCluster 时进入人工处理清单。
- Group 与 Qtree 集群不一致时停止迁移并记录错误。
- 同一项目同一集群只生成一条环境记录。
- 回填只建立关系，不把未知容量猜成 `0`；当前态保持空值和 `pending`，等待该环境首次成功采集。

### 11.4 B/C/F：切换应用

1. 后端新接口上线。
2. 前端切换为环境级 API。
3. 监控和统计改读 `project_environment_id`。
4. 停止创建假 Qtree。
5. 保留旧列用于短期回滚。

### 11.5 M3：收紧约束

- `groups.project_environment_id` 改为 `NOT NULL`。
- 添加唯一和 CHECK 约束。
- API 停止接受旧字段。
- 后续 migration 再删除 Group 中重复的 `project_id/storage_cluster_id`。

当前仓库只跟踪 `f4b2c8d9e701_add_soft_quota_fields.py`，其父 revision `a1d670c60836` 文件缺失。实施前必须完成 G0：核对生产 `alembic_version`，恢复可解释历史链或建立受控 baseline，并补齐受控 Alembic 依赖；禁止直接猜测 `down_revision`。

## 12. 回滚方案

1. 旧 `groups.project_id/storage_cluster_id/qtree_id` 在稳定期内保留。
2. 新增环境表不立即删除。
3. 回滚旧后端和旧前端。
4. 停止新版本采集任务。
5. 不回滚已经生成的 QuestDB 环境趋势数据。
6. 不移动或删除历史备份目录。
7. 只有确认不再需要回滚后，才执行清理 migration。

## 13. TDD 实施顺序与任务 DAG

所有生产修改执行 RED → GREEN → 可选 Refactor。每个 RED 必须实际编译并执行，且失败原因为目标行为缺失；同一目标在 GREEN 后复跑。若实施期使用 Git，RED 和 GREEN 各创建一个当前分支 checkpoint commit，Refactor 仅在测试保持 GREEN 后进行。

~~~mermaid
flowchart LR
    G0["G0 权限来源与迁移链决策"] --> M0["M0 生产数据审计"]
    M0 --> M1["M1 Expand 模型与 migration"]
    M1 --> B1["B1 环境 CRUD"]
    B1 --> B2["B2 Group 绑定与兼容双写"]
    B2 --> M2["M2 数据回填"]
    M2 --> C1["C1 环境/项目聚合与 QuestDB"]
    C1 --> C2["C2 Celery 新鲜读取与事务隔离"]
    B1 --> F1["F1 环境 API/选择器/表单"]
    B2 --> F2["F2 Group 页面与级联"]
    C2 --> F3["F3 项目工作区/趋势/Dashboard"]
    C2 --> F4["F4 Usage/Alert/导出"]
    F1 --> V["V 总验收"]
    F2 --> V
    F3 --> V
    F4 --> V
    C2 --> V
    V --> M3["M3 收紧约束和清理旧列"]
~~~

### G0：开工闸门

- 冻结权限来源。当前仓库只有登录用户和超级管理员，没有完整 project admin/editor/reader 成员模型；若本次不新增成员模型，最小权限只能基于超级管理员、`Project.in_charge_user_id` 和 `Project.pt_user_id`，不得声称存在未实现的四级角色。
- 当前唯一 migration `f4b2c8d9e701_add_soft_quota_fields.py` 的 `down_revision` 为 `a1d670c60836`，但历史 revision 文件不在当前仓库；当前 `.venv` 和 `backend/requirements.txt` 均缺少 Alembic。必须先补齐受控依赖并核对生产 `alembic_version`，决定恢复历史链或建立受控 baseline，禁止猜测修改 `down_revision`。
- 开工门槛：Alembic 可导入，`heads/history` 可解释，数据库和第 7.4 节 API 契约冻结。任一项不满足即停止 M1。

### M0-M2：审计、Expand 与回填

RED 测试与门槛：

- 审计能识别缺失项目/集群、跨集群 Qtree、假 Qtree、重复环境和重复 StorageUsage；发现不一致数据后停止自动回填。
- migration 在 SQLite、PostgreSQL、MySQL 方言下可编译或绑定；唯一键和索引列使用有界 `String(n)`，FK、UNIQUE、CHECK 具名，SQLite 修改使用 `batch_alter_table`。
- `UNIQUE(project_id, name)` 已覆盖相同前缀查询，不重复创建同列索引。
- 并发创建重复环境由数据库 UNIQUE 保底；服务捕获 `IntegrityError`、rollback，并稳定返回 `409`。
- Group 约束既禁止 Volume/Qtree 同时非空，也必须在 `enable_monitoring=true` 时保证至少一个目标；若三方言 CHECK 编译不一致，至少由服务校验和三方言测试保证行为。
- M1 只 Expand；M2 按审计确认结果回填，并验证环境数量、目标转换数量和未处理清单，回填前后计数不一致时停止。

### B1：环境 CRUD

RED 测试：

- 项目可以创建四个不同环境；同一项目不能重复绑定同一集群，不同项目可以绑定同一集群。
- 环境存在 Group 时不能删除；StorageCluster 已被环境引用时不能删除。
- 响应使用专用最小 StorageCluster 引用 schema，精确键只有 `id/name/storage_type`，不得包含密码或连接字段。
- Volume/Qtree 被 Group 引用时删除得到稳定业务错误，不把 FK 异常暴露为 `500`。
- 环境查询严格使用 G0 冻结的权限来源。

### B2：Group 绑定、兼容双写和下游接口

RED 测试：

- Group 可绑定 Volume 或 Qtree；同时提交、均未提交、Isilon 绑定 Qtree、目标集群不匹配均返回稳定 `422`。
- Group 列表可按环境过滤，响应返回统一 `storage_target`；Volume 绑定的详情、扩容、告警和邮件不访问 `group.qtree`。
- 兼容期旧 `project_id/storage_cluster_id` 只由后端从环境推导并双写，前端提交旧字段被拒绝。
- StorageUsage 的集群由 Group 推导；导出、告警、周报和备份路径均能追溯到环境，历史备份仍按原 `destination_path` 查找。

### C1：环境/项目聚合与 QuestDB

RED 测试：

- 两套 Isilon、两套 NetApp 分别更新对应环境；环境 A 不改变环境 B。
- 只有全部启用环境在本轮均成功时，Project 合计才等于这些环境的完整合计；任一启用环境失败或未完成时，Project current totals 和时间戳全部保留上一完整成功轮次。
- Isilon 不再生成假 Qtree，共享资源不会被普通 Group 重复计入。
- 环境当前态写入 PostgreSQL，环境趋势写入 QuestDB；查询返回第 7.4 节冻结的 summary/realtime 契约。

### C2：Celery 新鲜读取与失败隔离

以下 RED 统一优先放入 `backend/test/test_project_environment_aggregation.py`，避免增加重复测试基础设施：

- 配置作用域使用一次有界 SELECT，Group 数量增加不增加查询数。
- 另一 Session 提交配置后，本轮快照保持稳定，下一轮读取新配置。
- 关闭读取 Session 后快照仍可使用，不产生 `DetachedInstanceError` 或隐式 SQL。
- 停用 Cluster、Environment 或 Group 后，下一轮快照排除对应作用域。
- 旧快照不能更新已移动、停用或删除的 Group。
- 单集群异常只回滚该集群，关闭客户端，不影响下一集群提交。
- 全部集群结束后逐 Project 判定一次；只有全部启用环境均成功的 Project 才刷新，任一启用环境失败或未完成的 Project 完整保留上一成功轮次，无关且完整成功的 Project 正常更新。
- QuestDB 失败不回滚已提交 PostgreSQL，后续集群继续。
- 分布式锁 TTL 大于 Celery hard limit。

### F1-F4：前端四批

- F1 API/选择器/环境表单：项目选择后只显示所属环境，环境表单排除已绑定集群，API wrapper 精确命中冻结 endpoint/envelope。
- F2 Group 列表/表单/详情：级联顺序为项目→环境→目标类型→Volume/Qtree；Isilon 固定 Volume；上级变化清空下级；payload 不含独立 `project_id/storage_cluster_id`；统一展示 Volume/Qtree。
- F3 项目列表/工作区/Realtime/Dashboard：默认和无效 URL 回退规则正确；切换只请求当前环境；同名 Group 不跨环境合并；`RealTimePage` validator 同时接受现有 `group` 和新增 `project-environment`。
- F4 Usage/Alert/导出：用量只能选择环境内 Group，集群只读推导；环境筛选、周报分组和导出列与冻结契约一致。

每个前端批次先增加聚焦 Vitest RED，再实施最小 GREEN。新增或修改文件覆盖率以 lines、branches、functions、statements 均不低于 80% 为目标；仓库当前实际全局门禁仍以 `vitest.config.js` 为准：lines、branches、statements 为 70%，尚未设置 functions 门槛。规范中的 90%/95% 是后续目标，不得在本功能中宣称为当前已生效门禁。

### V 与 M3：总验收和收紧

- V 必须通过聚焦测试、全量现有门禁、lint、生产构建、migration 演练和外部浏览器烟测；真实设备和生产数据未验证时保持对应项“待验证”。
- M3 只有在回填计数、兼容窗口和回滚演练通过后才把 `project_environment_id` 收紧为 NOT NULL、停止旧字段双写并另建 migration 清理旧列。
- 任一阶段出现非预期 RED、上游未 GREEN、审计失败或契约变化，立即停止下游并回到对应 owner 收敛，不在调用方堆 fallback。

## 14. 验证命令

后端聚焦测试：

~~~powershell
.\.venv\Scripts\python.exe -m pytest `
  backend\test\test_project_storage_environment_migration.py `
  backend\test\test_project_storage_environment.py `
  backend\test\test_group_storage_binding.py `
  backend\test\test_project_environment_aggregation.py `
  backend\test\test_storage_soft_quota.py
~~~

迁移（仅在 G0 确认 Alembic 可导入且历史链可解释后执行）：

~~~powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini heads
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini history
.\.venv\Scripts\python.exe -m alembic `
  -c backend\alembic.ini upgrade head
~~~

后端回归：

~~~powershell
.\.venv\Scripts\python.exe -m pytest backend\test
~~~

前端聚焦测试：

~~~powershell
Set-Location frontend
npx vitest run `
  test/unit/project-storage-environment.test.js `
  test/unit/group-storage-binding.test.js `
  test/unit/project-environment-workspace.test.js `
  test/unit/project-environment-usage-alert.test.js `
  test/unit/api/modules.test.js `
  --coverage.enabled=false
~~~

前端完整验证：

~~~powershell
Set-Location frontend
npm test
npm run test:coverage
npm run lint
npm run build:prod
~~~

当前 `frontend/package.json` 没有 `type-check` 或 `lint:check` 脚本，不能把它们写成门禁。`npm run test:coverage` 当前执行 lines/branches/statements 70% 的全局门槛，未配置 functions 门槛。

通用检查：

~~~powershell
git diff --check
git status --short --branch
~~~

仓库当前没有 Playwright/E2E 配置或依赖。浏览器验收由 Verification Agent 使用外部浏览器能力执行烟测，前提是前后端和依赖服务可运行；它不是仓库内 Playwright 门禁，不新增依赖。

## 15. 验收标准

- [ ] 一个项目可以配置四套独立 StorageCluster 环境。
- [ ] 两套 Isilon、两套 NetApp 分别展示，不混合使用率。
- [ ] 项目详情可以切换环境并保留 URL 状态。
- [ ] 项目组只能属于一个环境。
- [ ] Isilon 项目组直接绑定 Volume。
- [ ] NetApp 项目组可以绑定 Volume 或 Qtree。
- [ ] 不再创建新的 `name='null'` Qtree。
- [ ] 后端拒绝跨集群资源绑定。
- [ ] 项目组、用户用量、告警、导出、扩容、备份均可追溯到环境。
- [ ] 同名 Group 不跨环境合并。
- [ ] 项目总量在完整成功轮次等于所有启用环境之和。
- [ ] 只有全部启用环境在同一轮均成功时才刷新 Project current totals；失败或未完成时完整保留上一成功轮次及时间戳。
- [ ] 环境级 QuestDB 趋势可查询。
- [ ] migration 可升级并具备回滚路径。
- [ ] SQLite、PostgreSQL、MySQL migration 编译或绑定测试通过。
- [ ] 前后端聚焦测试、全量门禁、构建和 lint 通过。
- [ ] 真实 NetApp/Isilon 环境完成至少一次只读采集验收。

## 16. 实施工作拆分

所有 Agent 都不得回退其他人的已有改动。文件所有权按阶段互斥，Main Coordinator 只负责需求收敛、调度、dirty worktree 检查、冲突复核和最终验收，不直接实现代码、测试或文档。

### Data Migration Agent

独占：

~~~text
backend/models.py
backend/requirements.txt
backend/migrate/versions/<revision>_add_project_storage_environments.py
backend/test/test_project_storage_environment_migration.py
~~~

负责 G0 的迁移链证据、M0 审计、M1 Expand 和 M2 回填。`backend/models.py` 和 migration 是 B1 开工前的串行闸门；其他 Agent 不并发修改。

### Backend API/Service Agent

独占 B1/B2：

~~~text
backend/main.py
backend/schemas/projectStorageEnvironmentSchema.py
backend/schemas/groupSchema.py
backend/crud/projectStorageEnvironmentCrud.py
backend/crud/groupCrud.py
backend/crud/projectsCrud.py
backend/crud/storageClusterCrud.py
backend/crud/volumeCrud.py
backend/crud/qtreeCrud.py
backend/services/projectStorageEnvironmentService.py
backend/services/groupService.py
backend/routers/project_storage_environment.py
backend/routers/group.py
backend/routers/projects.py
backend/routers/storage_usage.py
backend/routers/storage_cluster.py
backend/routers/volumes.py
backend/routers/qtrees.py
backend/test/test_project_storage_environment.py
backend/test/test_group_storage_binding.py
~~~

负责权限、CRUD、稳定错误、目标解析、兼容双写、删除保护和用量/导出接口。`projectStorageEnvironmentCrud.py` 的 API 查询与后续 collection snapshot 由同一 owner 完成，或在 B2 GREEN 后书面交接给 Celery/Aggregation Agent；禁止两人并发编辑。

### Celery/Aggregation Agent

独占 C1/C2：

~~~text
backend/celery_tasks/tasks/storages.py
backend/celery_tasks/manager/storagePulseMonitor.py
backend/celery_tasks/manager/storageAlert.py
backend/celery_tasks/manager/remoteFileManager.py
backend/questdb/models.py
backend/crud/questDbCrud.py
backend/test/test_project_environment_aggregation.py
~~~

负责环境/Project 聚合、QuestDB、配置快照、事务隔离、告警和备份路径。若聚合与 Celery 需要修改同一入口，必须由本 Agent 串行完成，不拆给并行 Agent。只有收到 B2 GREEN 和 `projectStorageEnvironmentCrud.py` 明确交接后才可修改快照读取函数。

### Frontend Agent

独占 `frontend/src/` 和 `frontend/test/` 中第 10 节列出的文件，按 F1-F4 串行推进。不得修改后端契约来迁就页面，契约缺口退回 Backend API/Service Agent。

### Docs Agent

独占：

~~~text
docs/features/project-storage-environment/*
docs/overview/backend-architecture.md
docs/overview/latest-features.md
docs/features/storage-cluster/overview.md
docs/standards/domain-terminology.md
docs/tracking/current-release.md
~~~

`docs/README.md` 当前有用户已有改动，本计划阶段明确排除；正式实施需要更新索引时，必须由 Main Coordinator 重新确认所有权后再交给 Docs Agent。

### Verification Agent

只读执行 migration、后端测试、前端测试、覆盖率、lint、构建、外部浏览器烟测、`git diff --check` 和风险复核，不修改生产文件或测试来让门禁通过。

### 阶段交接

- 每个 Agent 返回 changed files、逐文件修改、RED/GREEN 命令与结果、未验证范围和阻塞。
- 下游开始前由 Main Coordinator 检查上游 GREEN、工作区文件边界和未提交改动。
- 文件需要跨阶段交接时，前一 owner 先停止编辑并报告当前状态；Main Coordinator 确认后再把文件转交下一 owner。

## 17. 文档同步

正式实现时新增：

~~~text
docs/features/project-storage-environment/backend.md
docs/features/project-storage-environment/frontend.md
docs/features/project-storage-environment/test-plan.md
docs/features/project-storage-environment/verification.md
~~~

同步更新：

~~~text
docs/README.md
docs/overview/backend-architecture.md
docs/overview/latest-features.md
docs/features/storage-cluster/overview.md
docs/standards/domain-terminology.md
docs/tracking/current-release.md
~~~

所有未完成能力必须标记“待实现”或“待验证”，不能提前写成已交付。

## 18. 风险与控制

| 风险 | 控制措施 |
| --- | --- |
| 旧 Group 缺少项目或集群 | 迁移前审计，禁止自动猜测 |
| Qtree 与 Group 集群不一致 | 迁移失败并写入错误日志 |
| 假 Qtree 转换错误 | 按 `qtree.volume_id` 回填并核对数量 |
| Project 被部分成功环境覆盖 | 所有集群结束后逐 Project 检查全部启用环境；仅完整成功时刷新，否则保留上一完整成功轮次 |
| 同名项目组备份覆盖 | 新路径增加环境目录 |
| 历史备份无法找到 | 历史记录保留原始 `destination_path` |
| 前后端版本短暂不兼容 | 同一发布窗口部署，数据库先增量升级 |
| 旧监控器重复实现 | 只维护 `StoragePulseMonitor` 主路径 |
| 环境级权限遗漏 | 所有环境查询先校验 Project 上下文 |
| 真实设备行为与 Mock 不同 | 上线前执行 NetApp/Isilon 只读采集验收 |

## 19. 当前状态与未验证范围

截至 2026-07-13，当前分支已完成本设计的核心模型、接口、采集、前端工作区、Dashboard 和 F4 下游适配；剩余实现项仅为 M3，生产迁移和真实外部系统仍未完成验收。

### 19.1 已完成

- M0-M2：完成审计与回填工具、Expand 模型和 migration。`e6a1b2c3d4f5` 已创建 `project_storage_environments`，为 `groups` 增加环境和 Volume 绑定字段；回填脚本支持默认审计、阻塞项检查和显式 `--apply`，相关迁移与回填契约已有自动化测试。
- B1/B2：完成项目存储环境 CRUD、权限校验、重复环境冲突、删除保护，以及 Group 对环境和单一 Volume/Qtree 目标的绑定、过滤和统一目标响应；Isilon 只允许绑定 Volume。
- C1/C2：完成环境和完整轮次 Project 汇总、环境 QuestDB 读写入口、每轮新鲜标量快照、短读取会话、分集群事务和失败隔离。PostgreSQL 先提交，QuestDB 后写入；部分集群失败时保留成功集群结果，只有全部启用环境本轮成功的项目才刷新汇总。
- Celery 主链路读取优化：任务按稳定 ID 和短会话重新读取当前数据库绑定；Group/User/Project/System 告警、项目周报、单次与批量备份、BPM 和删除流程批量预加载关联并复用当前 ORM 快照；Group TOP20 使用一次窗口查询；`enable_monitoring=false` 的 Group 不进入 Group/User 告警。该完成口径不代表整个 `celery_tasks` 目录已消除 N+1。
- F1/F2：完成环境 API wrapper、管理表单与列表，以及项目→环境→目标类型→Volume/Qtree 的项目组级联绑定；Isilon 环境固定选择 Volume。
- F3：完成项目列表环境概览、项目详情环境工作台、`RealTimePage` 环境趋势和 Dashboard 环境维度接入，包括有效环境 URL 保留、无效环境回退、仅加载当前环境、项目/环境筛选、环境独立容量展示，以及使用 `project_environment_id:group_id` 稳定 key 隔离跨环境同名 Group。
- F4：完成 Usage、Alert 和导出的环境筛选、环境内 Group 约束与环境列；监控/扩容下游统一解析 Volume/Qtree 目标，备份路径增加环境目录，项目周报按环境分组。
- V 已完成范围：后端和前端自动化测试、前端 lint 与生产构建已通过。该结论只覆盖仓库自动化门禁，不代表 migration 或外部系统验收完成。

### 19.2 待实现

- M3：仅在生产数据审计、回填计数、migration upgrade/downgrade 和回滚演练通过后执行；届时把 `groups.project_environment_id` 收紧为 `NOT NULL`，停止兼容双写，并通过后续 migration 移除重复的 `project_id/storage_cluster_id` 旧字段。

### 19.3 待验证

- 尚未执行 migration upgrade/downgrade 演练，也未核对生产 `alembic_version` 或执行生产 Alembic upgrade。
- 尚未对生产历史数据执行审计和回填，生产 PostgreSQL 实际数据质量、回填计数和回滚路径仍待确认。
- 尚未执行外部浏览器烟测。
- 尚未连接真实 PostgreSQL、QuestDB、NetApp 或 Isilon 做端到端验收；外部连接、设备资源标识、目录映射、QuestDB 表结构和跨库最终一致性均待验证。
- `StoragePulseMonitor` 仍包含逐 Volume/Group/Project 的查询和 UPDATE；当前结果正确性已有测试覆盖，但真实性能仍需结合生产规模压测后优化。legacy 或未调度 monitor 不在本次完成口径。
- 当前 beat schedule 只启用 60 秒一次的 `storages_schedule_fetching_task`；告警、周报和定时备份条目仍为注释状态，尚未通过真实 Celery beat/worker 调度验收。
