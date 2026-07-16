# 存储集群专题

## 目标

`StorageCluster` 用于把 NetApp、Isilon 等存储系统纳入统一监控。后端以 `storage_clusters` 作为集群配置入口，并把 `aggregates`、`volumes`、`qtrees`、`groups`、`storage_usages` 关联到具体集群。

## 当前入口

API 统一挂载在：

```text
/storage-pulse/api
```

核心接口：

| 能力 | 路径 |
| --- | --- |
| 集群列表 | `GET /storage-pulse/api/storage-clusters` |
| 新增集群 | `POST /storage-pulse/api/storage-clusters` |
| 集群详情 | `GET /storage-pulse/api/storage-clusters/{storage_cluster_id}` |
| 修改集群 | `PUT /storage-pulse/api/storage-clusters/{storage_cluster_id}` |
| 删除集群 | `DELETE /storage-pulse/api/storage-clusters/{storage_cluster_id}` |
| 实时趋势 | `GET /storage-pulse/api/storage-clusters/{storage_cluster_id}/realtime` |

## 创建示例

```bash
curl -X POST "http://localhost:8000/storage-pulse/api/storage-clusters" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NetApp-Cluster-01",
    "storage_type": "netapp",
    "storage_host": "192.168.1.100",
    "storage_port": 443,
    "protocol": "https",
    "tls_verify": true,
    "storage_user": "monitor",
    "storage_password": "******",
    "limit": 100000,
    "is_active": true
  }'
```

示例中的 `http://localhost:8000` 是 DiskPulse API 地址，不代表存储设备协议；设备协议由请求体中的 `protocol` 决定。HTTP 下 TLS 校验不适用，设备凭据会以明文传输。

## Isilon Session 缓存

Isilon 集群在新增/编辑表单中按集群选择 Session 缓存模式：

| 模式 | 数据库值 | 行为 |
| --- | --- | --- |
| 不缓存 | `none` | 每轮采集重新登录，并在结束时调用 OneFS logout 安全释放 Session。 |
| 本地文件 | `file` | Cookie 与 CSRF Token 保存到 `isilon_session_cache_path`；相对路径以 `backend` 为基准，默认 `.isilon_cache/cache.json`。 |
| Redis | `redis` | 使用全局 `redis.host`、`redis.port` 和独立的 `redis.session_db`，按 OneFS Session 绝对超时时间设置 TTL。 |

数据库只保存 `isilon_session_cache_mode` 和 `isilon_session_cache_path`，不保存 Cookie。缓存读取或写入失败时退回安全注销，避免遗留未管理的设备 Session。本地缓存文件和 Redis 都包含有效认证材料，部署时必须限制文件 ACL 和 Redis 网络访问。

Isilon 配额采集使用 `resolve_names=true`，通过 `persona.name` 关联已经由 LDAP 同步到 DiskPulse 的用户；`persona.name` 缺失时仍可回退读取 `UID:<数字>`。采集账号必须使用加入专用最小权限角色的 OneFS 本地服务账号，不能使用 NIS 人员账号：目标 OneFS 9.11 在 NIS 人员账号触发身份解析后会使其下一次 PAPI 登录返回 `403`，本地服务账号不受该身份映射影响。

## Isilon 采集账号要求

Isilon 类型必须使用 System Zone 的 OneFS 本地服务账号。不要使用个人 NIS、LDAP 或 AD 账号作为长期采集账号。推荐账号名为 `diskpulse_monitor`，并加入专用的 `DiskPulseMonitor` 最小权限角色。监控权限保持只读；项目组和用户扩容要求 Quota 父权限及 Quota Management 子权限均为写权限。

角色需要以下最小权限：

| 权限 | 用途 |
| --- | --- |
| `ISI_PRIV_LOGIN_PAPI` | 登录 Platform API。 |
| `ISI_PRIV_CLUSTER` | 读取集群配置和总容量。 |
| `ISI_PRIV_SMARTPOOLS` | 读取 Storage Pool。 |
| `ISI_PRIV_QUOTA`（写） | 读取、调整目录和用户配额；OneFS 要求父权限不能低于 Quota Management 子权限。 |
| `ISI_PRIV_QUOTA_QUOTAMANAGEMENT`（写） | 创建和修改 Directory/User quota。 |
| `ISI_PRIV_STATISTICS` | 读取性能统计。 |
| `ISI_PRIV_PERFORMANCE` | 读取 performance dataset 和已固定 workload 配置。 |
| `ISI_PRIV_EVENT` | 读取系统事件。 |
| `ISI_PRIV_SYS_TIME` | 读取集群时间及 Dashboard 状态。 |

使用 root 在任一 Isilon 节点执行以下命令；创建用户时根据提示输入密码：

```sh
ROLE='DiskPulseMonitor'
SVC_USER='diskpulse_monitor'

isi auth roles view "$ROLE" --zone System >/dev/null 2>&1 ||
isi auth roles create "$ROLE" --zone System --description "DiskPulse monitoring and quota management"

isi auth users create "$SVC_USER" --zone System --enabled yes --password-expires no --set-password
isi auth roles modify "$ROLE" --zone System --add-user "$SVC_USER"

isi auth roles modify "$ROLE" --zone System \
  --add-priv-read ISI_PRIV_LOGIN_PAPI \
  --add-priv-read ISI_PRIV_CLUSTER \
  --add-priv-read ISI_PRIV_SMARTPOOLS \
  --add-priv-read ISI_PRIV_STATISTICS \
  --add-priv-read ISI_PRIV_PERFORMANCE \
  --add-priv-read ISI_PRIV_EVENT \
  --add-priv-read ISI_PRIV_SYS_TIME

# 兼容既有角色从只读升级：先删除 ISI_PRIV_QUOTA:r，再按父子顺序添加写权限。
isi auth roles modify "$ROLE" --zone System --remove-priv ISI_PRIV_QUOTA 2>/dev/null || true
isi auth roles modify "$ROLE" --zone System --add-priv-write ISI_PRIV_QUOTA
isi auth roles modify "$ROLE" --zone System --add-priv-write ISI_PRIV_QUOTA_QUOTAMANAGEMENT

isi auth users view "$SVC_USER" --zone System
isi auth roles view "$ROLE" --zone System
```

在 DiskPulse 存储集群表单中填写该服务账号和密码，API 协议选择 HTTPS，端口通常为 `8080`。Session 缓存推荐选择“不缓存（每次安全注销）”；保存账号后需重启 Celery Worker。

逐 Directory Quota 的延迟还要求 OneFS 配置以 `path` 为识别维度的 performance dataset，并把需要长期展示的路径固定为 workload。只增加 `ISI_PRIV_PERFORMANCE` 不会自动生成逐路径 workload。使用 root 检查和配置：

```sh
isi performance datasets list
isi performance datasets create path --name path   # 仅在没有 path dataset 时执行
isi performance workloads list path
isi performance workloads pin path "path:/ifs/data/example"
isi statistics workload --dataset path
```

每个 DiskPulse “Isilon Directory Quota”路径都需要执行一次 `workloads pin`；固定后至少等待 30 秒再检查统计。`path` 维度只覆盖 SMB/NFS 访问，不能把未固定路径的节点总延迟推算成目录延迟。

## 文档索引

| 文档 | 说明 |
| --- | --- |
| [design.md](./design.md) | 历史多集群设计背景；当前实现以本页和资源映射文档为准。 |
| [resource-mapping.md](./resource-mapping.md) | NetApp/Isilon 统一术语、采集映射、前端文案和项目组绑定实现。 |
| [migration.md](./migration.md) | PostgreSQL baseline 与 QuestDB 前向 revision 管理。 |
| [api-examples.md](./api-examples.md) | 集群 CRUD、实时查询和按集群过滤的 API 示例。 |
| [health-analytics.md](./health-analytics.md) | 容量变化、错误级别、高延迟、重复故障和报表导出。 |
| [performance-event-collection.md](./performance-event-collection.md) | NetApp/PowerScale 性能与事件采集整体设计、标准化和数据流。 |
| [vendor-api-contracts.md](./vendor-api-contracts.md) | 厂商设备接口、字段映射和 DiskPulse 分析 API 契约。 |
| [../../guides/storage-performance-event-troubleshooting.md](../../guides/storage-performance-event-troubleshooting.md) | 性能与事件采集的部署前检查、排障路径和真机验收清单。 |

## 维护边界

- 当前后端实际字段以 `backend/schemas/storageClusterSchema.py` 和 `backend/models.py` 为准。
- 新增或删除集群字段时，需要同步 `StoragePulseMonitor`、相关 CRUD、前端表单和本文档。
- `protocol` 只允许 `http` 或 `https`；`tls_verify` 仅对 HTTPS 生效。新建集群默认 `https/true`，已有集群由迁移回填为 `https/false`。
- PostgreSQL 从空库依次执行 root baseline `000000000001`、集群传输配置 `000000000002`、AI 中心 `000000000003`、存储健康分析 `000000000004` 和 Isilon Session 缓存配置 `000000000005`；当前 head 为 `000000000005`。已有集群升级后默认使用 `none`，需要在管理表单中明确选择文件或 Redis。使用已删除旧 revision 链的数据库不支持伪造版本接续。
- QuestDB 使用独立前向 revision 和 checksum 账本，存储性能表由 `000000000003_storage_performance_metrics.sql` 创建，当前 head 为 `000000000003`。
