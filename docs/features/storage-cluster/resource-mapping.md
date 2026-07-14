# NetApp 与 Isilon 存储资源术语及映射

> 状态：代码已实现，后端与前端行为验证已通过。Isilon-CR02（OneFS 9.11.0.5）已完成身份、Storage Pool 列表和 Quota 分页的只读检查；真机 Storage Pool 未返回可选 `usage` 对象，容量字段来源仍待确认，因此真机采集尚未验收完成。

## 1. 目标

- 前端使用“存储集群、容量池、存储空间、Qtree（NetApp）”作为统一页面术语，厂商原生名称只作为类型说明。
- NetApp 和 Isilon 数据进入相同的 `Aggregate`、`Volume`、`StorageUsage` 展示链路，但保留厂商原生类型。
- 不再使用 `isilon_cluster`、`null` Qtree 等占位对象伪造不存在的资源。
- 项目组始终绑定所选存储集群内的一个真实存储目标，采集、汇总、告警和页面使用同一绑定关系。

## 2. 统一术语表

| 前端统一术语 | 代码模型 | 采集流程术语 | NetApp ONTAP | Isilon OneFS | 统一含义 |
| --- | --- | --- | --- | --- | --- |
| 存储集群 | `StorageCluster` | 集群容量 | ONTAP Cluster | OneFS Cluster | 一套可独立连接和采集的存储系统实例 |
| 容量池 | `Aggregate` | 容量池 | Aggregate / Local Tier | Storage Pool / Node Pool | 厂商提供的物理容量池 |
| 存储空间 | `Volume` | 存储空间 | FlexVol / FlexGroup Volume | Directory Quota | 可分配给项目组的逻辑容量或目录配额目标 |
| Qtree（NetApp） | `Qtree` | Qtree | Volume 内的 Qtree | 不适用 | NetApp 专属的存储空间下级配额目标 |
| 用户用量 | `StorageUsage` | 用户配额 | Volume/Qtree 下的用户配额 | Directory Quota 路径下的用户配额 | 项目组内单个用户的配额和使用量 |
| 项目组 | `Group` | 项目组汇总 | 绑定一个 Volume 或 Qtree | 绑定一个 Directory Quota，对应 `volume_id` | 项目在指定存储集群上的监控和汇总单元 |

统一术语不改变公共接口。数据库模型、API 路径和请求枚举继续使用 `Aggregate`、`Volume`、`Qtree`；前端根据 `storage_cluster.storage_type` 与 `Volume.type` 派生“NetApp Aggregate”“Isilon Storage Pool”“NetApp Volume”“Isilon Directory Quota”等原生类型文案，不新增响应字段。

术语分层规则：

1. ORM、数据库表和现有 API 资源名继续使用 `Aggregate`、`Volume`、`Qtree`，避免只为改名引入迁移和兼容层。
2. 采集日志、任务步骤和内部方法说明统一使用“容量池、存储空间、用户配额、项目组汇总”，不把 Isilon 数据描述成 NetApp 资源。
3. 前端标题、筛选项、表格列和空状态统一使用“容量池、存储空间、Qtree（NetApp）”；原生名称放在“原生类型”列或详情说明中。
4. 文档首次出现统一术语时可写成“容量池（Aggregate / Storage Pool）”“存储空间（Volume / Directory Quota）”，后续只使用统一术语。

## 3. 统一资源层级

```text
StorageCluster
├── Aggregate
│   ├── NetApp Aggregate / Local Tier
│   └── Isilon Storage Pool / Node Pool
├── Volume
│   ├── NetApp FlexVol / FlexGroup
│   └── Isilon Directory Quota
├── Qtree
│   └── 仅 NetApp
└── Group
    └── StorageUsage
```

这里的 `Aggregate` 和 `Volume` 是跨厂商的展示集合，不代表 Isilon Storage Pool 与 Directory Quota 一定存在严格父子关系。OneFS Directory Quota 是基于路径的逻辑配额；只有设备接口能明确返回唯一 Storage Pool 归属时，才写入 `Volume.aggregate`，否则保持为空。

## 4. 数据字段映射

### 4.1 Aggregate

| 字段 | NetApp | Isilon |
| --- | --- | --- |
| `storage_cluster_id` | 所属 ONTAP 集群 | 所属 OneFS 集群 |
| `name` | Aggregate 名称 | Storage Pool / Node Pool 名称 |
| `limit` | Aggregate 总容量 | Storage Pool 总容量 |
| `used` | Aggregate 已用容量 | Storage Pool 已用容量 |
| `use_ratio` | Aggregate 使用率 | Storage Pool 使用率 |

Isilon 不再创建 `name='isilon_cluster'` 的占位 Aggregate。集群总容量继续写入 `StorageCluster`，Storage Pool 只保存真实池数据。

### 4.2 Volume

| 字段 | NetApp | Isilon |
| --- | --- | --- |
| `storage_cluster_id` | 所属 ONTAP 集群 | 所属 OneFS 集群 |
| `name` | Volume 名称 | Directory Quota 完整路径 |
| `vserver` | SVM 名称 | Access Zone 名称；接口未返回时为空 |
| `aggregate` | 所属 Aggregate 名称 | 可确认的 Storage Pool 名称；无法确认时为空 |
| `type` | `flexvol`、`flexgroup` 等 | `directory_quota` |
| `limit` | Volume 容量或硬限额 | Directory Quota 硬限额 |
| `soft_limit` | Volume 软限额 | Directory Quota 软限额 |
| `used` | Volume 已用容量 | Directory Quota 逻辑已用容量 |

### 4.3 Qtree 和 StorageUsage

- Qtree 只采集 NetApp 真实 Qtree；没有 Qtree 的 NetApp Volume 由项目组直接绑定 `volume_id`，不再创建 `name='null'` 的占位 Qtree。
- Isilon 不创建 Qtree 记录，也不允许项目组绑定 `qtree_id`。
- NetApp 用户配额和 Isilon 用户配额都写入 `StorageUsage`，并通过 `group_id`、`storage_cluster_id` 进入同一用户用量链路。

## 5. 统一数据采集流程

### 5.1 采集阶段术语

| 阶段 | 当前方法名 | 统一日志文案 | 输出模型 |
| --- | --- | --- | --- |
| 整轮采集 | `execute_data_collection` | 开始/完成存储资源采集 | 当前集群全部资源 |
| 采集集群容量 | `aggregate_cluster_usage` | 汇总集群容量 | `StorageCluster` |
| 采集容量池 | `fetch_capacity_pools` | 获取容量池 | `Aggregate` |
| 采集存储空间 | `fetch_storage_spaces` | 获取存储空间 | `Volume` |
| 采集 Qtree | `fetch_qtrees` | 获取 Qtree | `Qtree` |
| 采集用户配额 | `fetch_user_quotas` | 获取用户配额 | `StorageUsage` |
| 同步业务库 | `sync_data_to_postgres` | 同步存储资源 | PostgreSQL 当前态 |
| 汇总项目组 | `aggregate_group_usage` | 汇总项目组用量 | `Group` |
| 汇总集群 | `aggregate_cluster_usage` | 汇总集群用量 | `StorageCluster` |
| 写入趋势 | `write_questdb` | 写入存储趋势 | QuestDB 时序数据 |

采集入口先读取设备数据，再调用同步和汇总方法。Isilon 的 Directory Quota 与用户配额复用同一次 `get_quotas()` 响应，避免同一轮重复请求设备。

### 5.2 采集流程

```text
读取启用的 StorageCluster
        |
        v
按 storage_type 创建 NetAppClient / IsilonClient
        |
        +-- NetApp
        |   +-- Aggregate API       -> 容量池（Aggregate）
        |   +-- Volume API          -> 存储空间（Volume）
        |   +-- Qtree API           -> Qtree
        |   `-- Quota Report API    -> 用户配额（StorageUsage）
        |
        `-- Isilon
            +-- /platform/16/storagepool/storagepools?toplevels=true
            |                         -> 容量池（Aggregate）
            +-- Quota API 单次响应    -> 存储空间（Volume）+ 用户配额（StorageUsage）
            `-- 不采集 Qtree
        |
        v
同一集群事务内同步 PostgreSQL
        |
        v
按项目组真实绑定汇总 Group
        |
        v
更新 StorageCluster 总容量
        |
        v
PostgreSQL 提交成功后写入 QuestDB
```

采集约束：

1. 每类数据只有在对应设备请求成功且返回非空记录后才允许清理本集群的旧记录；请求失败或响应无法解析时必须回滚，合法空结果保留旧数据。
2. NetApp 集群总容量按真实 Aggregate 汇总；Isilon 集群总容量直接使用 cluster stats，不依赖 Storage Pool 求和。
3. Isilon Directory Quota 使用完整路径作为 Volume 的设备侧稳定键；同一集群内按 `(storage_cluster_id, name)` 唯一同步。
4. Qtree 按 `(storage_cluster_id, volume_id, name)` 唯一同步。
5. QuestDB 继续按统一模型写入 `aggregate_storage_usages`、`volume_storage_usages`、`qtree_storage_usages` 和 `storage_usages`；Isilon 不写 Qtree 指标。
6. 被项目组或下级 Qtree 引用的存储空间、被项目组引用的 Qtree 不自动删除，采集日志记录保留原因。

## 6. 项目组绑定关系

每个项目组必须同时确定：

- 一个 `project_id`。
- 一个 `storage_cluster_id`。
- 一个 `group_tag_id`。
- 恰好一个存储目标：`volume_id` 或 `qtree_id`。

| 存储类型 | 项目组目标 | 字段规则 | 项目组直接用量来源 |
| --- | --- | --- | --- |
| NetApp | Volume | `volume_id` 非空，`qtree_id` 为空 | 对应 Volume |
| NetApp | Qtree | `qtree_id` 非空，`volume_id` 为空 | 对应 Qtree |
| Isilon | Directory Quota（统一显示为 Volume） | `volume_id` 非空，`qtree_id` 为空 | 对应 Directory Quota Volume |

必须执行以下校验：

1. Volume/Qtree 必须属于项目组选择的 `storage_cluster_id`。
2. Isilon 项目组禁止提交 `qtree_id`。
3. 切换存储集群或目标类型时，必须清空原 `volume_id` 和 `qtree_id`，再选择新目标。
4. 被项目组引用的 Volume/Qtree 不允许删除，应返回稳定的 `409`。
5. `associate_multiple_groups=false` 时，Group 直接继承目标的容量、已用量和使用率。
6. `associate_multiple_groups=true` 时，目标仍然必选，但 Group 用量改为汇总该 Group 下的 `StorageUsage`，不能直接复制整个目标用量。
7. 多个 Group 可以在业务明确时绑定同一个目标；项目级和集群级汇总必须按目标 ID 去重，避免重复计算容量。

`GET /groups` 支持按 `volume_id` 或 `qtree_id` 过滤；两个参数同时提交时返回 `422`。

## 7. 前端页面术语

| 页面/位置 | 统一文案 | NetApp 展示 | Isilon 展示 |
| --- | --- | --- | --- |
| 左侧菜单 | 容量池 | 原生类型为“NetApp Aggregate” | 原生类型为“Isilon Storage Pool” |
| 列表/详情标题 | 容量池 / 容量池详情 | 显示 Aggregate 数据 | 显示 Storage Pool 数据 |
| 容量池搜索字段 | 容量池名称 | Aggregate 名称 | Storage Pool 名称 |
| 容量池类型列 | 原生类型 | NetApp Aggregate | Isilon Storage Pool |
| 左侧菜单 | 存储空间 | 原生类型为“NetApp Volume” | 原生类型为“Isilon Directory Quota” |
| 列表/详情标题 | 存储空间 / 存储空间详情 | 显示 Volume 数据 | 显示 Directory Quota 数据 |
| 存储空间搜索字段 | 名称/路径 | Volume 名称 | Directory Quota 路径 |
| 存储空间类型列 | 原生类型 | NetApp Volume | Isilon Directory Quota |
| 所属容量池列 | 所属容量池 | Aggregate 名称 | 能确认时显示 Storage Pool，否则显示 `-` |
| 左侧菜单 | Qtree（NetApp） | 正常展示 | 页面提示“Isilon 不支持 Qtree”，不请求 Qtree 数据 |
| 项目组表单 | 存储目标类型 | 可选“存储空间”“Qtree（NetApp）” | 固定为“存储空间（Directory Quota）” |
| 项目组表单 | 存储目标 | 按所选类型选择 Volume/Qtree | 选择 Directory Quota 路径 |
| 项目组开关 | 单个存储目标关联多个项目组 | 同一文案 | 同一文案 |
| 项目组列表 | 存储目标 | `存储空间 / 名称` 或 `Qtree（NetApp） / 名称` | `存储空间 / Directory Quota 路径` |

路由和 API 暂不重命名，继续使用 `/aggregates`、`/volumes`、`/qtrees`，减少无业务收益的兼容改造。页面通过 `storage_cluster_id` 筛选，并根据集群类型展示原生类型和适用字段。按钮、面包屑、空状态、趋势图标题、导出列名和错误提示必须与上述统一文案一致，不能只修改菜单标题。

## 8. 实现结果与数据兼容

- Isilon Storage Pool 写入 `Aggregate`，cluster stats 只更新 `StorageCluster`；成功同步真实池数据时清理历史 `isilon_cluster` Aggregate。
- Isilon Directory Quota 写入 `Volume`，名称为完整路径，`type=directory_quota`，无法确认唯一 Storage Pool 时 `aggregate` 为空。
- NetApp 只保存真实 Qtree。成功同步 Volume/Qtree 后，历史 `null` Qtree 项目组绑定迁移为对应 `volume_id`，再删除占位 Qtree。
- 项目组汇总同时支持 NetApp Volume、NetApp Qtree 和 Isilon Directory Quota；项目汇总按 `(storage_cluster_id, target_type, target_id)` 去重直接目标。
- 本次不修改 PostgreSQL 或 QuestDB schema，不新增 Alembic/QuestDB revision；历史 QuestDB 占位指标保留，新采集不再写入占位资源。
- 前端路由标题、列表、详情、选择器、项目组、用量和告警文案已统一；`/aggregates`、`/volumes`、`/qtrees` 路径不变。

## 9. 实施验收标准

- Isilon 容量池列表只出现真实 Storage Pool，不出现 `isilon_cluster`。
- Isilon 存储空间列表只出现真实 Directory Quota，名称使用完整路径且原生类型明确。
- Isilon 不创建、不请求、不展示 Qtree。
- NetApp Volume 和 Qtree 两种项目组绑定都能正确更新 Group 指标。
- 项目组 API 拒绝双目标、无目标、跨集群目标和 Isilon Qtree。
- 同一目标绑定多个 Group 时，项目和集群容量汇总不重复计数。
- 自动化测试覆盖两类存储的采集映射、项目组绑定校验、Group 汇总，以及菜单、标题、筛选、表格、详情和空状态术语。

手工只读检查可从仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe backend\scripts\manual_isilon_check.py "<存储集群名称>"
```

脚本按名称读取 `storage_clusters` 中的 Isilon 连接配置，只调用 Quota 查询并输出总数和类型统计；不会更新 PostgreSQL 或 QuestDB，也不会输出密码。

## 10. 风险与待验证项

- Isilon-CR02（OneFS 9.11.0.5）已验证 `/platform/latest`、Storage Pool 实际列表和 Quota 分页；部署数据库中的原连接入口可成功读取全部 `2264` 条 Quota，无需为 Quota 采集切换入口。
- 真机返回的 Storage Pool 条目包含名称和类型，但未包含 SDK 中定义为可选的 `usage` 对象；在确认容量字段的官方来源、所需权限和单位前，不添加猜测式回退，采集失败时保持整集群回滚。
- 未缓存的 OneFS API 会话会在客户端关闭时通过 `DELETE /session/1/session` 注销，避免服务端会话持续占用并发名额。
- Directory Quota 与 Storage Pool 不一定是一对一关系，当前不会为了填充“所属容量池”而人工指定默认池。
- 运行时兼容清理已由自动化测试覆盖，但仍需在持有历史占位数据的集成库观察一次完整采集事务。

## 11. 参考资料

- [NetApp：Disks and ONTAP local tiers](https://docs.netapp.com/us-en/ontap/disks-aggregates/)
- [NetApp：Volumes, qtrees, files, and LUNs](https://docs.netapp.com/us-en/ontap/concepts/volumes-qtrees-files-luns-concept.html)
- [Dell：PowerScale OneFS quota types](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs-pub-91300-administration-guide-gui/quota-types?guid=guid-8d7d96db-d24f-4edb-9789-f7ce88ca7d70&lang=en-us)
- [Dell OneFS 9.11 SDK：Storagepool API](https://github.com/Isilon/isilon_sdk_python/blob/Isilon_SDK_v0.7.0/isilon_sdk/isilon_sdk/v9_11_0/docs/StoragepoolApi.md)
- [Dell OneFS API：注销会话](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference/log-out-of-a-session?guid=guid-6e944631-bc6b-435c-983a-fe01a7e0d6c2&lang=en-us)
