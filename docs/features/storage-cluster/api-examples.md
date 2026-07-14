# StorageCluster API 使用示例

## 基础 CRUD 操作

### 1. 创建存储集群

```bash
# 创建 NetApp 集群
curl -X POST "http://localhost:8000/storage-pulse/api/storage-clusters" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NetApp-Cluster-01",
    "storage_host": "192.168.1.100",
    "storage_type": "netapp",
    "protocol": "https",
    "tls_verify": true,
    "description": "生产环境 NetApp 存储",
    "limit": 100000,
    "is_active": true
  }'

# 创建 Isilon 集群
curl -X POST "http://localhost:8000/storage-pulse/api/storage-clusters" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Isilon-Cluster-01",
    "storage_host": "192.168.1.200",
    "storage_type": "isilon",
    "protocol": "https",
    "tls_verify": true,
    "description": "备份环境 Isilon 存储",
    "limit": 200000,
    "is_active": true
  }'
```

上述 `http://localhost:8000` 是 DiskPulse API 地址，不代表存储设备协议；设备协议由请求体中的 `protocol` 决定。`tls_verify` 仅对 HTTPS 生效，HTTP 下设备凭据会以明文传输。

### 2. 获取所有集群

```bash
# 获取所有集群
curl "http://localhost:8000/storage-pulse/api/storage-clusters"

# 仅获取活跃集群
curl "http://localhost:8000/storage-pulse/api/storage-clusters?is_active=true"
```

### 3. 获取集群详情

```bash
curl "http://localhost:8000/storage-pulse/api/storage-clusters/1"
```

### 4. 更新集群

```bash
curl -X PUT "http://localhost:8000/storage-pulse/api/storage-clusters/1" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "更新后的描述",
    "is_active": false
  }'
```

### 5. 删除集群

```bash
curl -X DELETE "http://localhost:8000/storage-pulse/api/storage-clusters/1"
```

## 实时数据查询

### 获取集群使用趋势

```bash
# 最近24小时的使用量
curl "http://localhost:8000/storage-pulse/api/storage-clusters/1/realtime?indicator=used"

# 最近24小时的使用率
curl "http://localhost:8000/storage-pulse/api/storage-clusters/1/realtime?indicator=use_ratio"

# 指定时间范围
curl "http://localhost:8000/storage-pulse/api/storage-clusters/1/realtime?start_time=2026-03-01T00:00:00&end_time=2026-04-01T00:00:00&indicator=used"
```

## 按集群过滤存储资源

### 获取指定集群的容量池（Aggregate / Storage Pool）

```bash
curl "http://localhost:8000/storage-pulse/api/aggregates?storage_cluster_id=1"
```

### 获取指定集群的存储空间（Volume / Directory Quota）

```bash
curl "http://localhost:8000/storage-pulse/api/volumes?storage_cluster_id=1"
```

### 获取指定集群的 Qtree（NetApp）

```bash
curl "http://localhost:8000/storage-pulse/api/qtrees?storage_cluster_id=1"
```

### 获取指定集群的存储一览容量树

```bash
curl "http://localhost:8000/storage-pulse/api/aggregates/storage-trees/?storage_cluster_id=1"
```

### 获取指定集群的 StorageUsage

```bash
curl "http://localhost:8000/storage-pulse/api/storage-usages?storage_cluster_id=1"
```

### 按存储目标过滤项目组

```bash
# 绑定指定存储空间的项目组
curl "http://localhost:8000/storage-pulse/api/groups?volume_id=10"

# 绑定指定 Qtree（NetApp）的项目组
curl "http://localhost:8000/storage-pulse/api/groups?qtree_id=20"
```

`volume_id` 与 `qtree_id` 不能同时提交；同时提交时返回 `422`。模型名、字段名和 `/aggregates`、`/volumes`、`/qtrees` 路径保持不变。

## Python 示例

```python
import requests

BASE_URL = "http://localhost:8000/storage-pulse/api"

# 创建集群
def create_cluster():
    response = requests.post(f"{BASE_URL}/storage-clusters", json={
        "name": "NetApp-Cluster-01",
        "storage_host": "192.168.1.100",
        "storage_type": "netapp",
        "protocol": "https",
        "tls_verify": True,
        "limit": 100000
    })
    return response.json()

# 获取集群列表
def get_clusters():
    response = requests.get(f"{BASE_URL}/storage-clusters")
    return response.json()

# 获取集群实时数据
def get_cluster_realtime(cluster_id):
    response = requests.get(
        f"{BASE_URL}/storage-clusters/{cluster_id}/realtime",
        params={"indicator": "used"}
    )
    return response.json()

# 获取集群下的所有容量池
def get_cluster_aggregates(cluster_id):
    response = requests.get(
        f"{BASE_URL}/aggregates",
        params={"storage_cluster_id": cluster_id}
    )
    return response.json()
```
