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

方案已在现有 FastAPI、SQLAlchemy、Celery、Vue 3 和 Vitest 技术栈内实施，不需要新增前端依赖，也没有为配置快照新增 Redis 缓存。项目仍处于初始开发阶段，PostgreSQL 使用单一初始基线 migration；真实 PostgreSQL、QuestDB 和存储设备验证仍待执行。

实施成功标准：

- 一个项目的多套环境在关系、当前容量、趋势、告警、扩容、备份和页面状态中均可独立追溯。
- Celery 每轮使用同一份数据库配置快照，下一轮能够读取已经提交的新配置，不发生跨环境陈旧写入。
- `Group` 从建表起只保存严格环境关系和单一 Volume/Qtree 目标，不保留重复项目/集群字段或兼容双写。
- 每个生产批次都完成预期 RED、最小 GREEN 和同目标复测；未验证内容不标记为完成。

前置依赖与停止条件：

- 单一 baseline、环境当前态字段和第 7.4 节前端契约未确认时，停止在实施前。
- RED 若由语法、测试装配、依赖缺失或无关回归导致，不算有效 RED，停止修改生产代码。
- 上游 migration、API 或聚合批次未 GREEN 时，下游不得用 speculative mock 契约越级交付。
- 非空开发数据库不得直接套用已删除的历史 revision；先确认可清空后重建。
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
    is_active           BOOLEAN NOT NULL,
    limit               DOUBLE PRECISION NULL,
    soft_limit          DOUBLE PRECISION NULL,
    used                DOUBLE PRECISION NULL,
    use_ratio           DOUBLE PRECISION NULL,
    soft_use_ratio      DOUBLE PRECISION NULL,
    collection_status   VARCHAR(16) NOT NULL,
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

`UNIQUE(project_id, name)` 已提供相同列前缀索引，不再重复创建 `(project_id, name)` 普通索引。单一 baseline 使用静态、显式的 `create_table/create_index`，FK、UNIQUE、CHECK 和索引名称与最终 ORM schema 一致；数据库 DDL 不写入 ORM 的 Python 侧默认值。

当前态字段说明：

- `limit`、`soft_limit`、`used`、`use_ratio`、`soft_use_ratio` 是环境 summary 和 Project 合计的 PostgreSQL 持久化落点，避免 API 临时拼接多张表。
- `collection_status` 只允许 `pending`、`success`、`failed`，`last_collected_at` 记录最近一次成功采集时间。
- 采集失败时保留上次成功容量和 `last_collected_at`，仅把状态改为 `failed`；错误详情写服务端日志，不把设备返回、凭据或敏感异常文本写入数据库或 API。

删除规则：

- 环境下存在 Group 时禁止删除环境，返回 `409 Conflict`。
- StorageCluster 已绑定项目环境时禁止删除集群。
- 停用环境使用 `is_active=false`，不直接删除历史数据。

### 4.2 修改 Group

最终关系字段：

~~~text
project_environment_id  FK project_storage_environments.id，NOT NULL
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

`groups` 不包含 `project_id` 或 `storage_cluster_id` 物理列；项目和集群只能经 `ProjectStorageEnvironment` 推导。创建、更新和响应 schema 均不接受或返回这两个旧数字字段，列表查询参数如使用 `project_id/storage_cluster_id`，由后端 JOIN 环境表过滤。

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
backend/migrate/versions/000000000001_initial_schema.py
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
- 已删除无生产入口的 `NetAppMonitor`、`IsilonMonitor`、`StoreMonitor`，不保留旧监控兼容实现。
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

## 11. 数据库初始化方案

### 11.1 PostgreSQL / Alembic baseline

- `backend/migrate/versions/` 仅保留 `000000000001_initial_schema.py`。
- `revision = "000000000001"`，`down_revision = None`。
- baseline 以静态、显式 DDL 一次创建当前 `14` 张 PostgreSQL 业务表及索引；`groups.project_environment_id` 从建表起为 `NOT NULL`，不存在 `groups.project_id/storage_cluster_id`。
- baseline 只适用于空数据库，不包含 DML、历史数据转换、默认环境生成、假 Qtree 转换或兼容字段。
- 已使用删除前 revision 的开发数据库不支持原地升级；确认数据可丢弃后删除并重建空库，再执行 `upgrade head`。

### 11.2 QuestDB 边界

QuestDB 不属于 Alembic 管理范围。环境趋势表由 `backend/questdb/models.py` 和 QuestDB 初始化流程维护，不写入 `000000000001`，也不在本功能中迁移或回填历史 QuestDB 数据。

## 12. 回滚方案

1. 停止 API、Celery beat 和 worker，避免重建期间继续写入。
2. 初始开发数据库按与目标代码匹配的 baseline 重建；不恢复或伪造已经删除的 revision 链。
3. `downgrade base` 仅用于空库 migration 往返验证，不作为保留开发数据的回滚工具。
4. QuestDB schema 和数据独立管理，Alembic downgrade 不处理 QuestDB。
5. 真实备份目录和外部设备数据不随本地数据库重建删除。

## 13. TDD 实施顺序与任务 DAG

所有生产修改执行 RED → GREEN → 可选 Refactor。每个 RED 必须实际编译并执行，且失败原因为目标行为缺失；同一目标在 GREEN 后复跑。若实施期使用 Git，RED 和 GREEN 各创建一个当前分支 checkpoint commit，Refactor 仅在测试保持 GREEN 后进行。

~~~mermaid
flowchart LR
    G0["G0 权限与单一 baseline"] --> B1["B1 环境 CRUD"]
    B1 --> B2["B2 Group 严格绑定"]
    B2 --> C1["C1 环境/项目聚合与 QuestDB"]
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
~~~

### G0：开工闸门

- 冻结权限来源。当前仓库只有登录用户和超级管理员，没有完整 project admin/editor/reader 成员模型；若本次不新增成员模型，最小权限只能基于超级管理员、`Project.in_charge_user_id` 和 `Project.pt_user_id`，不得声称存在未实现的四级角色。
- 开工门槛：Alembic 可导入，`heads/history` 只显示 `000000000001` 单一 root/head，空 SQLite upgrade/downgrade 与 ORM 元数据无差异，数据库和第 7.4 节 API 契约冻结。

### Schema baseline：严格模型与空库初始化

RED 测试与门槛：

- `groups` 不含 `project_id/storage_cluster_id`，`project_environment_id` 为 `NOT NULL`，唯一和目标 CHECK 约束存在。
- migration 在空 SQLite 可 upgrade/downgrade，upgrade 后 `alembic.autogenerate.compare_metadata(...)` 为空；PostgreSQL DDL 可编译。MySQL 全 `Base.metadata` 编译审计中，当前 `14` 张表有 `13` 张因无长度 `String/VARCHAR` 触发 `CompileError`；本次只声明支持 SQLite/PostgreSQL，不把默认三方言门禁描述为通过。
- `UNIQUE(project_id, name)` 已覆盖相同前缀查询，不重复创建同列索引。
- 并发创建重复环境由数据库 UNIQUE 保底；服务捕获 `IntegrityError`、rollback，并稳定返回 `409`。
- Group 约束既禁止 Volume/Qtree 同时非空，也在 `enable_monitoring=true` 时保证至少一个目标；服务层同步执行同一业务校验。
- 不创建回填脚本、不接受旧字段、不双写重复关系。

### B1：环境 CRUD

RED 测试：

- 项目可以创建四个不同环境；同一项目不能重复绑定同一集群，不同项目可以绑定同一集群。
- 环境存在 Group 时不能删除；StorageCluster 已被环境引用时不能删除。
- 响应使用专用最小 StorageCluster 引用 schema，精确键只有 `id/name/storage_type`，不得包含密码或连接字段。
- Volume/Qtree 被 Group 引用时删除得到稳定业务错误，不把 FK 异常暴露为 `500`。
- 环境查询严格使用 G0 冻结的权限来源。

### B2：Group 严格绑定和下游接口

RED 测试：

- Group 可绑定 Volume 或 Qtree；同时提交、均未提交、Isilon 绑定 Qtree、目标集群不匹配均返回稳定 `422`。
- Group 列表可按环境过滤，响应返回统一 `storage_target`；Volume 绑定的详情、扩容、告警和邮件不访问 `group.qtree`。
- Group 请求和响应都不包含旧 `project_id/storage_cluster_id` 数字字段；保留的项目/集群筛选参数通过 JOIN `ProjectStorageEnvironment` 执行。
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

### V：总验收

- V 必须通过聚焦测试、全量现有门禁、lint、生产构建、migration 演练和外部浏览器烟测；真实设备和生产数据未验证时保持对应项“待验证”。
- 严格 Group 约束和旧列清理已直接进入 initial baseline，不存在后续 M3 或兼容窗口。
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

迁移（仅对可清空的初始开发数据库执行；旧 revision 数据库先重建为空库）：

~~~powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini heads
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini history
.\.venv\Scripts\python.exe -m alembic `
  -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic `
  -c backend\alembic.ini downgrade base
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
- [x] 单一 baseline 在空 SQLite 可 upgrade/downgrade，且与 ORM metadata 无差异。
- [x] PostgreSQL baseline offline upgrade/downgrade DDL 可编译。
- [ ] 真实 PostgreSQL 空库完成 upgrade/downgrade 验收。
- [ ] 前后端聚焦测试、全量门禁、构建和 lint 通过。
- [ ] 真实 NetApp/Isilon 环境完成至少一次只读采集验收。

## 16. 实施工作拆分

所有 Agent 都不得回退其他人的已有改动。文件所有权按阶段互斥，Main Coordinator 只负责需求收敛、调度、dirty worktree 检查、冲突复核和最终验收，不直接实现代码、测试或文档。

### Schema/Baseline Agent

独占：

~~~text
backend/models.py
backend/requirements.txt
backend/migrate/versions/000000000001_initial_schema.py
backend/test/test_project_storage_environment_migration.py
~~~

负责严格 ORM schema、单一 root baseline、空 SQLite 往返、ORM metadata 对比和 PostgreSQL offline DDL 编译。`backend/models.py` 和 baseline 是 B1 开工前的串行闸门；不实现历史审计或回填。

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

负责权限、CRUD、稳定错误、目标解析、严格环境绑定、删除保护和用量/导出接口。`projectStorageEnvironmentCrud.py` 的 API 查询与后续 collection snapshot 由同一 owner 完成，或在 B2 GREEN 后书面交接给 Celery/Aggregation Agent；禁止两人并发编辑。

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
| 已使用删除前 revision 的开发库无法升级 | 确认数据可丢弃后重建空库，只执行 `000000000001` |
| 在非空数据库误执行 initial baseline | 初始化前检查目标库为空；失败后不伪造 `alembic_version` |
| QuestDB 被误认为由 Alembic 管理 | PostgreSQL baseline 与 QuestDB 初始化、验证和清理完全分开 |
| Project 被部分成功环境覆盖 | 所有集群结束后逐 Project 检查全部启用环境；仅完整成功时刷新，否则保留上一完整成功轮次 |
| 同名项目组备份覆盖 | 新路径增加环境目录 |
| 数据库与应用 schema 不一致 | 空库 upgrade 后执行 Alembic autogenerate metadata 对比 |
| 监控器重复实现 | 只维护 `StoragePulseMonitor` 主路径，删除无入口旧实现 |
| 环境级权限遗漏 | 所有环境查询先校验 Project 上下文 |
| 真实设备行为与 Mock 不同 | 上线前执行 NetApp/Isilon 只读采集验收 |

## 19. 当前状态与未验证范围

截至 2026-07-14，当前分支已完成严格模型、单一 baseline、接口、采集、前端工作区、Dashboard 和 F4 下游适配；不存在回填、兼容窗口或后续 M3。真实 PostgreSQL、QuestDB 和外部系统仍待验收。

### 19.1 已完成

- Schema baseline：`backend/migrate/versions/` 只保留 root/head `000000000001`，静态创建当前 `14` 张表和 `31` 个索引。空 SQLite upgrade 后与 `Base.metadata` 对比无差异，downgrade 后为 `0` 张表；PostgreSQL offline upgrade/downgrade DDL 编译和逆序 drop 审计通过，核心迁移测试 `13 passed`。
- B1/B2：完成项目存储环境 CRUD、权限校验、重复环境冲突、删除保护，以及 Group 对环境和单一 Volume/Qtree 目标的严格绑定、过滤和统一目标响应；`groups.project_environment_id` 为 `NOT NULL`，不存在 `groups.project_id/storage_cluster_id`，请求与响应不暴露旧数字字段，Isilon 只允许绑定 Volume。
- C1/C2：完成环境和完整轮次 Project 汇总、环境 QuestDB 读写入口、每轮新鲜标量快照、短读取会话、分集群事务和失败隔离。PostgreSQL 先提交，QuestDB 后写入；部分集群失败时保留成功集群结果，只有全部启用环境本轮成功的项目才刷新汇总。
- Celery 主链路读取优化：任务按稳定 ID 和短会话重新读取当前数据库绑定；Group/User/Project/System 告警、项目周报、单次与批量备份、BPM 和删除流程批量预加载关联并复用当前 ORM 快照；Group TOP20 使用一次窗口查询；`enable_monitoring=false` 的 Group 不进入 Group/User 告警。该完成口径不代表整个 `celery_tasks` 目录已消除 N+1。
- F1/F2：完成环境 API wrapper、管理表单与列表，以及项目→环境→目标类型→Volume/Qtree 的项目组级联绑定；Isilon 环境固定选择 Volume。
- F3：完成项目列表环境概览、项目详情环境工作台、`RealTimePage` 环境趋势和 Dashboard 环境维度接入，包括有效环境 URL 保留、无效环境回退、仅加载当前环境、项目/环境筛选、环境独立容量展示，以及使用 `project_environment_id:group_id` 稳定 key 隔离跨环境同名 Group。
- F4：完成 Usage、Alert 和导出的环境筛选、环境内 Group 约束与环境列；监控/扩容下游统一解析 Volume/Qtree 目标，备份路径增加环境目录，项目周报按环境分组。
- V 自动化：后端全量 `146 passed`、`41 warnings`，覆盖率 `85%`（`2892` statements、`444` miss）；warning 为既有 SQLAlchemy、Pydantic、QuestDB 和 HTTP 422 弃用提示。前端 `30` 个文件、`153 passed`，覆盖率 statements `93.47%`、branches `83.56%`、functions `82.11%`、lines `93.47%`；lint 和生产构建通过。

### 19.2 待验证

- 尚未在真实 PostgreSQL 空库执行 baseline upgrade/downgrade；自动化已覆盖 SQLite 往返和 PostgreSQL offline DDL 编译。
- QuestDB 不属于 Alembic baseline，真实 QuestDB 环境趋势表初始化和读写仍待单独验收。
- 尚未执行外部浏览器烟测。
- 尚未连接真实 PostgreSQL、QuestDB、NetApp 或 Isilon 做端到端验收；外部连接、设备资源标识、目录映射、QuestDB 表结构和跨库最终一致性均待验证。
- `StoragePulseMonitor` 当前结果正确性已有测试覆盖，但真实性能仍需结合生产规模压测后确认。
- 当前 beat schedule 只启用 60 秒一次的 `storages_schedule_fetching_task`；告警、周报和定时备份条目仍为注释状态，尚未通过真实 Celery beat/worker 调度验收。
- MySQL 全 metadata 编译未通过；若后续扩大到 MySQL 部署，必须先补齐无长度 `String/VARCHAR` 并重新执行三方言编译门禁。
- 生产构建仍有既有的 `VITE_APP_TITLE` 未定义和 chunk 大于 `500 kB` warning。
