# StorageCluster 多存储支持功能文档

## 文档索引

本目录包含 StorageCluster 多存储支持功能的完整文档：

1. **[storage_cluster_design.md](./storage_cluster_design.md)** - 架构设计文档
   - 需求背景和整体架构
   - 数据库表结构设计（PostgreSQL + QuestDB）
   - ER 关系图
   - API 接口设计
   - 监控任务设计
   - 数据流程说明

2. **[storage_cluster_migration.md](./storage_cluster_migration.md)** - 数据库迁移文档
   - PostgreSQL 迁移 SQL
   - QuestDB 迁移 SQL
   - 现有数据迁移方案
   - 回滚方案
   - 验证步骤

3. **[storage_cluster_api_examples.md](./storage_cluster_api_examples.md)** - API 使用示例
   - CRUD 操作示例
   - 实时数据查询示例
   - 按集群过滤资源示例
   - Python 代码示例

## 快速开始

### 1. 执行数据库迁移

参考 [storage_cluster_migration.md](./storage_cluster_migration.md) 执行数据库迁移。

### 2. 创建存储集群

```bash
curl -X POST "http://localhost:8000/api/storage/storage-clusters" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NetApp-Cluster-01",
    "ip_address": "192.168.1.100",
    "storage_type": "netapp",
    "limit": 100000
  }'
```

### 3. 查看集群列表

```bash
curl "http://localhost:8000/api/storage/storage-clusters"
```

## 核心功能

- ✅ 支持多个存储集群的配置管理（NetApp、Isilon）
- ✅ Volume、Qtree、Aggregate、StorageUsage 关联到存储集群
- ✅ 记录每个集群的总存储使用情况
- ✅ 实时监控集群使用趋势（QuestDB 时序数据）
- ✅ 按集群过滤存储资源
- ✅ RESTful API 接口

## 技术栈

- FastAPI - Web 框架
- SQLAlchemy - PostgreSQL ORM
- QuestDB - 时序数据库
- Celery - 异步任务调度

## 代码变更

### 新增文件
- `models.py` - 新增 StorageCluster 模型
- `questdb/models.py` - 新增 StorageClusterUsage 模型
- `schemas/storageClusterSchema.py` - StorageCluster Schema
- `crud/storageClusterCrud.py` - StorageCluster CRUD
- `routers/storage_cluster.py` - StorageCluster API 路由

### 修改文件
- `models.py` - Aggregate、Volume、Qtree、StorageUsage 添加 storage_cluster_id
- `questdb/models.py` - AggregateStorageUsage 添加 storage_cluster_id
- `crud/questDbCrud.py` - 添加 get_storage_cluster_real_time 函数
- `main.py` - 注册 storage_cluster 路由

## 后续工作

如需实现监控任务的多集群支持，还需要修改：
- `celery_tasks/manager/storagePulseMonitor.py` - 支持按集群初始化
- `celery_worker.py` - 为每个集群启动独立监控任务

详细设计参考 [storage_cluster_design.md](./storage_cluster_design.md) 第 6 节。
