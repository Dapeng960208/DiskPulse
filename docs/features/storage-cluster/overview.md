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

## 文档索引

| 文档 | 说明 |
| --- | --- |
| [design.md](./design.md) | 历史多集群设计背景；当前实现以本页和资源映射文档为准。 |
| [resource-mapping.md](./resource-mapping.md) | NetApp/Isilon 统一术语、采集映射、前端文案和项目组绑定实现。 |
| [migration.md](./migration.md) | PostgreSQL baseline 与 QuestDB 前向 revision 管理。 |
| [api-examples.md](./api-examples.md) | 集群 CRUD、实时查询和按集群过滤的 API 示例。 |
| [health-analytics.md](./health-analytics.md) | 容量变化、错误级别、高延迟、重复故障和报表导出。 |

## 维护边界

- 当前后端实际字段以 `backend/schemas/storageClusterSchema.py` 和 `backend/models.py` 为准。
- 新增或删除集群字段时，需要同步 `StoragePulseMonitor`、相关 CRUD、前端表单和本文档。
- `protocol` 只允许 `http` 或 `https`；`tls_verify` 仅对 HTTPS 生效。新建集群默认 `https/true`，已有集群由迁移回填为 `https/false`。
- PostgreSQL 从空库依次执行 root baseline `000000000001`、集群传输配置 `000000000002`、AI 中心 `000000000003` 和存储健康分析 `000000000004`；当前 head 为 `000000000004`，AI `000000000003` 后必须继续执行存储健康 `000000000004`。使用已删除旧 revision 链的数据库不支持伪造版本接续。
- QuestDB 使用独立前向 revision 和 checksum 账本，存储性能表由 `000000000003_storage_performance_metrics.sql` 创建，当前 head 为 `000000000003`。
