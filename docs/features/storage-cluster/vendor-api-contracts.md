# NetApp 与 PowerScale 性能、事件接口契约

## 1. 适用范围

本文记录 DiskPulse 当前实际调用的设备只读接口、字段映射和对外分析接口。示例中的主机、token、账号和密码均为占位符，不能复制为生产凭据。

## 2. NetApp ONTAP

### 2.1 设备接口

| 用途 | DiskPulse 调用 | 关键字段 | 处理方式 |
| --- | --- | --- | --- |
| Volume 性能 | `GET /api/storage/volumes?fields=uuid,name,metric` | `metric.latency`、`metric.iops`、`metric.throughput` | 延迟微秒除以 1000；嵌套 `total` 写入标准字段。 |
| EMS 事件 | `GET /api/support/ems/events?time=>={UTC_Z}&fields=time,index,message,node,log_message` | `time`、`index`、`message.name`、`message.severity`、`node` | 转为统一事件、按 `index` 去重。 |

ONTAP `metric` 是单数。历史排障已验证，错误请求 `metrics` 会被设备以 `400/262197` 拒绝；客户端和测试均锁定单数字段。NetApp 官方将存储对象性能分为 IOPS、Latency、Throughput，并区分读、写、其他和总值；DiskPulse 当前使用总值作为跨厂商的展示口径。[ONTAP REST API reference](https://docs.netapp.com/us-en/ontap-restapi/pdfs/sidebar/Cluster.pdf)

### 2.2 性能映射

| ONTAP 响应 | DiskPulse 字段 | 单位 |
| --- | --- | --- |
| `metric.latency.total` | `latency_total` | `µs → ms` |
| `metric.latency.read` | `latency_read` | `µs → ms` |
| `metric.latency.write` | `latency_write` | `µs → ms` |
| `metric.iops.total` | `iops_total` | IOPS |
| `metric.throughput.total` | `throughput_total` | B/s |
| `metric.timestamp` | `collected_at` | 设备时间 |

## 3. PowerScale / Isilon OneFS

### 3.1 Session 与版本发现

| 用途 | 调用 | 说明 |
| --- | --- | --- |
| 建立 PAPI Session | `POST /session/1/session` | 以 `services=["platform"]` 建立 Platform API 会话。 |
| 检查缓存 Session | `GET /session/1/session` | 仅在集群选择 Session 缓存时调用。 |
| 发现 API 版本 | `GET /platform/latest` | 不把 OneFS release 硬编码为 API 版本。 |
| 探测集群 | `GET /platform/1/cluster/config` | 验证连通性并读取 OneFS release。 |

OneFS API 的 `/platform/latest` 用于发现最新 API 版本；使用具体资源版本可避免把设备 release 号直接当作 API URI 版本。OneFS 官方文档同时明确说明 Session cookie 与 CSRF 认证流程。[OneFS API overview](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference_9.5.0.0/introduction-to-this-guide?guid=guid-ec43cac3-3ea7-4e46-9fd2-749e26881b5d)

### 3.2 路径性能接口

| 步骤 | 调用 | 目的 |
| --- | --- | --- |
| 发现 dataset | `GET /platform/{version}/performance/datasets` | 选择 `metrics` 包含 `path` 的 dataset，取得 `id` 与 `statkey`。 |
| 读取固定 workload | `GET /platform/{version}/performance/datasets/{id}/workloads` | 将内部 workload ID 映射为 `metric_values.path`。 |
| 读取当前统计 | `GET /platform/{version}/statistics/current?keys={statkey}` | 读取 workload `record` 的计数器。 |

OneFS 将 dataset 定义为一组被采集的性能指标，workload 接口用于列出/维护 dataset 下的 workload；`statistics/current` 返回请求时刻的当前统计。[Performance datasets](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference/performance-datasets-resource?guid=guid-f036e2e1-edff-43a6-b422-c27b6fe9d938&lang=en-us) · [Dataset workloads](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference/performance-datasets-workloads-resource?guid=guid-50a8d00b-6800-485f-8b6d-1deb002f700e&lang=en-us) · [Current statistics](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference/statistics-current-resource?guid=guid-fb7c7796-3e27-45f1-8e0f-1f448555fb77&lang=en-us)

| OneFS workload record | DiskPulse 字段 | 规则 |
| --- | --- | --- |
| `latency_read.sum/count` | `latency_read` | `µs → ms` |
| `latency_write.sum/count` | `latency_write` | `µs → ms` |
| `latency_read/write/other` 合并 | `latency_total` | 用合并 `sum/count` 得到加权平均。 |
| `protocol_ops.sum` 或 `ops.sum` | `iops_total` | 保留设备提供的总操作值。 |
| `bytes_in.sum + bytes_out.sum` | `throughput_total` | 两者均缺失时保持 `null`。 |
| `stat.time` | `collected_at` | Unix 时间戳转本地 naive 时间。 |

只有 `workload` 路径已存在于 PostgreSQL `Volume.name` 时，采集器才把它作为 `object_type=volume` 写入。未固定的 Directory Quota、父路径和节点统计不会被“补算”进来。

### 3.3 OneFS 事件接口

| 用途 | 调用 | DiskPulse 处理 |
| --- | --- | --- |
| Event Group | `GET /platform/{version}/event/eventgroup-occurrences` | 使用 `last_event`，缺失时回退 `time_noticed`；从 `causes` 取事件代码与描述。 |
| Event List | `GET /platform/{version}/event/eventlists` | 展开外层 `events[]` 后逐条标准化。 |

OneFS 官方将 eventgroup occurrences 和 eventlists 分别作为可枚举的事件分组资源及按分组列出事件的资源。[Event group occurrences](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference/event-eventgroups-occurrences-resource?guid=guid-ea315fee-dcaf-46dc-abef-5a55bbdc6f57&lang=en-us) · [Event lists](https://www.dell.com/support/manuals/en-us/isilon-onefs/ifs_pub_onefs_api_reference/event-eventlists-resource?guid=guid-9d81434b-a947-4017-b266-88e6fc8af051&lang=en-us)

## 4. DiskPulse 分析 API

所有接口均以 `/storage-pulse/api` 为前缀，并要求 `Authorization: Bearer <token>`。

### 4.1 性能 Top 对象

```text
GET /storage-clusters/{storage_cluster_id}/analytics/top-latency
```

查询参数：

| 参数 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- |
| `start_time` | 是 | ISO 8601；范围最长 180 天 | 查询起点。 |
| `end_time` | 是 | 晚于 `start_time` | 查询终点。 |
| `limit` | 否 | `1..100`，默认 `10` | 返回对象数。 |
| `object_type` | 否 | `volume`、`workload`、`node` | 页面固定传 `volume`。 |

示例：

```bash
curl -G 'https://diskpulse.example/storage-pulse/api/storage-clusters/7/analytics/top-latency' \
  -H 'Authorization: Bearer <token>' \
  --data-urlencode 'start_time=2026-07-16T00:00:00+08:00' \
  --data-urlencode 'end_time=2026-07-16T23:59:59+08:00' \
  --data-urlencode 'limit=20' \
  --data-urlencode 'object_type=volume'
```

响应摘录：

```json
{
  "supported": true,
  "data": [{
    "object_id": "volume-uuid-or-path",
    "object_name": "/ifs/data/project-a",
    "object_type": "volume",
    "p95_latency": 8.47,
    "avg_latency": 2.71,
    "max_latency": 8.02,
    "avg_read_latency": 1.50,
    "avg_write_latency": 3.00,
    "avg_iops": 125.0,
    "avg_throughput": 4096.0,
    "sample_count": 5
  }]
}
```

`supported=false` 表示该集群从未成功写入性能样本；`supported=true` 且 `data=[]` 表示当前时间范围没有数据。

### 4.2 系统事件

```text
GET /storage-clusters/{storage_cluster_id}/analytics/system-events
```

| 参数 | 默认值 | 约束 | 说明 |
| --- | --- | --- | --- |
| `start_time`、`end_time` | 无 | 范围最长 180 天 | 时间窗口。 |
| `keyword` | 无 | 最大 100 字符 | 匹配事件代码、对象或正文。 |
| `severity` | 无 | `critical`、`error`、`warning`、`info` | 统一后的严重级别。 |
| `page` | `1` | ≥1 | 页码。 |
| `page_size` | `20` | `1..100` | 每页数量。 |

响应为 `{data, total, page, page_size}`。另外可使用 `error-severity` 获取按严重级别汇总，使用 `repeated-faults` 获取相同 fingerprint 至少出现两次的设备故障。

### 4.3 导出

```text
GET /storage-clusters/{storage_cluster_id}/analytics/export
```

参数：`format=csv|excel|pdf`，`section=capacity|severity|latency|faults|all`。导出沿用默认性能排行口径；页面的多指标选择只影响当前可视化和表格列，不改变已归档的导出契约。

## 5. 最小权限与前置条件

PowerScale 采集账号至少需要 `ISI_PRIV_LOGIN_PAPI`、`ISI_PRIV_CLUSTER`、`ISI_PRIV_SMARTPOOLS`、`ISI_PRIV_QUOTA`、`ISI_PRIV_STATISTICS`、`ISI_PRIV_PERFORMANCE`、`ISI_PRIV_EVENT`、`ISI_PRIV_SYS_TIME` 的只读权限。权限满足后仍需创建 `path` dataset 并固定每一个需展示的 Directory Quota workload；权限本身不会产生 workload 数据。

详细部署和验证命令见[排障手册](../../guides/storage-performance-event-troubleshooting.md)。
