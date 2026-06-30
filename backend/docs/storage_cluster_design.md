# StorageCluster 多存储支持设计文档

## 1. 需求背景

当前系统仅支持单一存储集群的管理和监控。随着业务发展，需要支持多个存储集群（NetApp、Isilon等）的统一管理和监控。

### 核心需求
- 支持多个存储集群的配置管理（IP、类型、命名等）
- Volume、Qtree、Aggregate、StorageUsage 需要关联到具体的存储集群
- 记录每个集群的总存储使用情况和实时趋势
- 监控任务支持多集群并行采集

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ StorageCluster   │  │ Aggregate/Volume/Qtree/Usage     │ │
│  │ CRUD API         │  │ CRUD API (支持集群过滤)            │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ StorageCluster   │  │ Aggregate/Volume/Qtree/Usage     │ │
│  │ CRUD             │  │ CRUD (按集群过滤)                  │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ PostgreSQL       │  │ QuestDB (时序数据)                 │ │
│  │ - StorageCluster │  │ - StorageClusterUsage            │ │
│  │ - Aggregate      │  │ - AggregateStorageUsage          │ │
│  │ - Volume         │  │ - VolumeStorageUsage             │ │
│  │ - Qtree          │  │ - QtreeStorageUsage              │ │
│  │ - StorageUsage   │  │ - StorageUsage                   │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│                  Monitoring Layer (Celery)                   │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ StoragePulseMonitor (多实例，每个集群一个)                ││
│  │ - 从 StorageCluster 读取配置                              ││
│  │ - 采集 Aggregate/Volume/Qtree 数据                        ││
│  │ - 计算集群总使用量                                         ││
│  │ - 写入 PostgreSQL + QuestDB                               ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 3. 数据库设计

### 3.1 PostgreSQL 表结构

#### StorageCluster (新增)
```sql
CREATE TABLE storage_clusters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(255) NOT NULL,
    storage_type VARCHAR(50) NOT NULL,  -- 'netapp' or 'isilon'
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    limit BIGINT,                       -- 总容量 (GB)
    used BIGINT,                        -- 已使用 (GB)
    use_ratio FLOAT,                    -- 使用率 (%)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Aggregate (修改)
```sql
ALTER TABLE aggregates ADD COLUMN storage_cluster_id INTEGER REFERENCES storage_clusters(id);
CREATE INDEX idx_aggregates_cluster ON aggregates(storage_cluster_id);
```

#### Volume (修改)
```sql
ALTER TABLE volumes ADD COLUMN storage_cluster_id INTEGER REFERENCES storage_clusters(id);
CREATE INDEX idx_volumes_cluster ON volumes(storage_cluster_id);
```

#### Qtree (修改)
```sql
ALTER TABLE qtrees ADD COLUMN storage_cluster_id INTEGER REFERENCES storage_clusters(id);
CREATE INDEX idx_qtrees_cluster ON qtrees(storage_cluster_id);
```

#### StorageUsage (修改)
```sql
ALTER TABLE storage_usage ADD COLUMN storage_cluster_id INTEGER REFERENCES storage_clusters(id);
CREATE INDEX idx_storage_usage_cluster ON storage_usage(storage_cluster_id);
```

### 3.2 QuestDB 表结构

#### storage_cluster_storage_usages (新增)
```sql
CREATE TABLE storage_cluster_storage_usages (
    storage_cluster_id SYMBOL,
    used DOUBLE,
    use_ratio DOUBLE,
    updated_at TIMESTAMP
) TIMESTAMP(updated_at) PARTITION BY DAY;
```

#### 现有表修改
所有存储相关的时序表都需要添加 `storage_cluster_id SYMBOL` 字段：
- aggregate_storage_usages
- volume_storage_usages
- qtree_storage_usages
- storage_usages

## 4. ER 关系图

```
┌─────────────────────┐
│  StorageCluster     │
│  ─────────────────  │
│  id (PK)            │
│  name               │
│  ip_address         │
│  storage_type       │
│  limit              │
│  used               │
│  use_ratio          │
└─────────────────────┘
          │
          │ 1:N
          ├──────────────────────────────────────┐
          │                                      │
          ↓                                      ↓
┌─────────────────────┐              ┌─────────────────────┐
│  Aggregate          │              │  Volume             │
│  ─────────────────  │              │  ─────────────────  │
│  id (PK)            │              │  id (PK)            │
│  storage_cluster_id │              │  storage_cluster_id │
│  name               │              │  aggregate_id (FK)  │
│  used               │              │  name               │
└─────────────────────┘              │  used               │
                                     └─────────────────────┘
                                               │
                                               │ 1:N
                                               ↓
                                     ┌─────────────────────┐
                                     │  Qtree              │
                                     │  ─────────────────  │
                                     │  id (PK)            │
                                     │  storage_cluster_id │
                                     │  volume_id (FK)     │
                                     │  name               │
                                     │  used               │
                                     └─────────────────────┘

┌─────────────────────┐
│  StorageUsage       │
│  ─────────────────  │
│  id (PK)            │
│  storage_cluster_id │
│  ...                │
└─────────────────────┘
```

## 5. API 接口设计

### 5.1 StorageCluster API

#### 获取所有存储集群
```
GET /api/storage-clusters
Response: List[StorageClusterResponse]
```

#### 创建存储集群
```
POST /api/storage-clusters
Body: StorageClusterCreate
Response: StorageClusterResponse
```

#### 获取集群详情
```
GET /api/storage-clusters/{id}
Response: StorageClusterResponse
```

#### 更新集群
```
PUT /api/storage-clusters/{id}
Body: StorageClusterUpdate
Response: StorageClusterResponse
```

#### 删除集群
```
DELETE /api/storage-clusters/{id}
Response: {"message": "success"}
```

#### 获取集群实时使用趋势
```
GET /api/storage-clusters/{storage_cluster_id}/realtime
Query Parameters:
  - start_time: datetime (可选)
  - end_time: datetime (可选)
  - indicator: str = 'used' (可选: 'used' | 'use_ratio')
Response: List[{timestamp, value}]
```

### 5.2 现有 API 增强

所有存储相关的 API 都添加 `storage_cluster_id` 查询参数：

```
GET /api/aggregates?storage_cluster_id=1
GET /api/volumes?storage_cluster_id=1
GET /api/qtrees?storage_cluster_id=1
GET /api/storage-usage?storage_cluster_id=1
```

## 6. 监控任务设计

### 6.1 StoragePulseMonitor 改造

**核心改动：**

1. **构造函数改造**
```python
def __init__(self, db: Session, logger, storage_cluster_id: int):
    # 从 StorageCluster 表读取配置
    cluster = db.query(StorageCluster).filter(
        StorageCluster.id == storage_cluster_id
    ).first()
    
    self.storage_cluster_id = storage_cluster_id
    self.storage_type = cluster.storage_type
    self.ip_address = cluster.ip_address
    
    # 根据类型初始化客户端
    if self.storage_type == 'netapp':
        self.client = NetAppClient(cluster.ip_address, ...)
    else:
        self.client = IsilonClient(cluster.ip_address, ...)
```

2. **数据采集时设置 storage_cluster_id**
```python
def sync_aggregates(self):
    for agg_data in self.client.get_aggregates():
        aggregate = Aggregate(
            storage_cluster_id=self.storage_cluster_id,
            name=agg_data['name'],
            ...
        )
```

3. **计算集群总使用量**
```python
def aggregate_cluster_usage(self):
    if self.storage_type == 'netapp':
        # NetApp: 对所有 Aggregate 求和
        total_used = self.db.query(func.sum(Aggregate.used)).filter(
            Aggregate.storage_cluster_id == self.storage_cluster_id
        ).scalar() or 0
    else:
        # Isilon: 直接使用 cluster stats
        total_used = self.cluster_stats['used']
    
    # 更新 StorageCluster 表
    cluster = self.db.query(StorageCluster).get(self.storage_cluster_id)
    cluster.used = total_used
    cluster.use_ratio = (total_used / cluster.limit * 100) if cluster.limit else 0
    cluster.updated_at = datetime.now()
    self.db.commit()
    
    # 写入 QuestDB
    write_storage_cluster_usage_to_questdb(
        storage_cluster_id=self.storage_cluster_id,
        used=total_used,
        use_ratio=cluster.use_ratio
    )
```

### 6.2 Celery Worker 改造

```python
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # 获取所有 active 的存储集群
    db = SessionLocal()
    clusters = db.query(StorageCluster).filter(
        StorageCluster.is_active == True
    ).all()
    
    # 为每个集群启动监控任务
    for cluster in clusters:
        sender.add_periodic_task(
            300.0,  # 5分钟
            monitor_storage_cluster.s(cluster.id),
            name=f'monitor-cluster-{cluster.id}'
        )

@app.task
def monitor_storage_cluster(storage_cluster_id: int):
    db = SessionLocal()
    monitor = StoragePulseMonitor(db, logger, storage_cluster_id)
    monitor.execute_data_collection()
```

## 7. 数据流程

### 7.1 数据采集流程

```
1. Celery 定时任务启动
   ↓
2. 遍历所有 active 的 StorageCluster
   ↓
3. 为每个集群创建 StoragePulseMonitor 实例
   ↓
4. 从 StorageCluster 读取配置（ip、type）
   ↓
5. 初始化对应的客户端（NetAppClient/IsilonClient）
   ↓
6. 采集数据并设置 storage_cluster_id
   - Aggregate
   - Volume
   - Qtree
   - StorageUsage
   ↓
7. 计算集群总使用量
   - NetApp: sum(Aggregate.used)
   - Isilon: cluster_stats.used
   ↓
8. 更新 StorageCluster 表
   ↓
9. 写入 QuestDB 时序表
```

### 7.2 查询流程

```
1. 前端请求集群列表
   ↓
2. GET /api/storage-clusters
   ↓
3. 返回所有集群及其使用情况
   ↓
4. 前端选择某个集群
   ↓
5. GET /api/aggregates?storage_cluster_id=1
   ↓
6. 返回该集群下的所有 Aggregate
   ↓
7. GET /api/storage-clusters/1/realtime
   ↓
8. 从 QuestDB 查询该集群的使用趋势
```

## 8. 使用示例

### 8.1 创建存储集群

```python
import requests

# 创建 NetApp 集群
response = requests.post('http://api/storage-clusters', json={
    'name': 'NetApp-Cluster-01',
    'ip_address': '192.168.1.100',
    'storage_type': 'netapp',
    'description': '生产环境 NetApp 存储',
    'limit': 100000  # 100TB
})

# 创建 Isilon 集群
response = requests.post('http://api/storage-clusters', json={
    'name': 'Isilon-Cluster-01',
    'ip_address': '192.168.1.200',
    'storage_type': 'isilon',
    'description': '备份环境 Isilon 存储',
    'limit': 200000  # 200TB
})
```

### 8.2 查询集群数据

```python
# 获取所有集群
clusters = requests.get('http://api/storage-clusters').json()

# 获取某个集群的详情
cluster = requests.get('http://api/storage-clusters/1').json()

# 获取集群的实时使用趋势
realtime = requests.get(
    'http://api/storage-clusters/1/realtime',
    params={
        'start_time': '2026-03-01T00:00:00',
        'end_time': '2026-04-01T00:00:00',
        'indicator': 'used'
    }
).json()

# 获取某个集群下的所有 Aggregate
aggregates = requests.get(
    'http://api/aggregates',
    params={'storage_cluster_id': 1}
).json()
```

## 9. 注意事项

### 9.1 数据迁移
- 现有数据需要关联到默认集群（id=1）
- PostgreSQL 和 QuestDB 都需要迁移
- 建议在低峰期执行迁移

### 9.2 性能考虑
- 为 storage_cluster_id 字段添加索引
- QuestDB 使用 SYMBOL 类型存储 storage_cluster_id
- 监控任务并行执行，避免阻塞

### 9.3 兼容性
- 保持现有 API 向后兼容
- storage_cluster_id 参数为可选
- 不传参数时返回所有集群的数据

## 10. 后续扩展

- 支持集群间数据迁移
- 集群健康度监控
- 集群容量预警
- 集群性能对比分析
