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
    "storage_user": "monitor",
    "storage_password": "******",
    "limit": 100000,
    "is_active": true
  }'
```

## 文档索引

| 文档 | 说明 |
| --- | --- |
| [design.md](./design.md) | 多集群设计背景、数据关系、监控任务设计。 |
| [migration.md](./migration.md) | 当前空库 baseline 和 QuestDB 独立初始化边界。 |
| [api-examples.md](./api-examples.md) | 集群 CRUD、实时查询和按集群过滤的 API 示例。 |

## 维护边界

- 当前后端实际字段以 `backend/schemas/storageClusterSchema.py` 和 `backend/models.py` 为准。
- 新增或删除集群字段时，需要同步 `StoragePulseMonitor`、相关 CRUD、前端表单和本文档。
- PostgreSQL 从空库执行单一 baseline `000000000001`；不支持从已删除 revision 原地升级。QuestDB 不属于 Alembic。
