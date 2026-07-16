# 项目组与用户目录配额调整设计

> 状态：已实现并通过自动化聚焦验证；真实 NetApp/Isilon 写入待测试设备人工验收。

## 1. 目标

在项目组列表和用户目录列表提供“调整配额”入口。管理员填写调整后的目标配额，后端根据资源所属存储集群调用 NetApp ONTAP 或 Dell PowerScale OneFS 接口，并在设备成功后同步本地数据、调整记录和结果邮件。

“调整配额”同时允许扩容和缩容，不再把输入值解释为新增容量。

## 2. 范围

- 项目组：调整其独占存储目标的配额或容量。
- 用户目录：调整当前系统用户名对应的用户配额；当前系统用户名与研发用户名一致。
- 空间硬限额：必填，可大于或小于当前值。
- 空间软限额：可选；填写时必须大于 `0` 且小于硬限额。
- 软限额宽限期：仅 Isilon 显示和提交；设置软限额时必填。
- 单位：空间限额支持 `GiB`、`TiB`；宽限期支持分钟、小时、天。
- 权限：仅超级管理员可执行。

本期不支持文件限额和 NetApp 用户映射。NetApp 用户映射是跨 Windows/UNIX 身份映射能力，不用于选择本系统用户。

## 3. API 契约

新增资源化接口：

```http
PATCH /groups/{group_id}/quota
PATCH /storage-usages/{storage_usage_id}/quota
```

两个接口复用同一请求 schema：

```json
{
  "hard_limit": 100,
  "soft_limit": 80,
  "unit": "GiB",
  "soft_grace": 60,
  "soft_grace_unit": "minutes"
}
```

字段规则：

| 字段 | 规则 |
| --- | --- |
| `hard_limit` | 必填，有限正数。 |
| `soft_limit` | 可为 `null`；非空时为有限正数且严格小于 `hard_limit`。 |
| `unit` | `GiB` 或 `TiB`，同时作用于硬限额和软限额。 |
| `soft_grace` | Isilon 且设置软限额时必填正整数；其他情况必须为 `null`。 |
| `soft_grace_unit` | `minutes`、`hours` 或 `days`；与 `soft_grace` 同时出现。 |

后端把空间限额统一换算为字节、把宽限期统一换算为秒后调用设备客户端；数据库现有 `limit`、`soft_limit` 字段继续保存 GiB，不新增容量字段。

成功响应返回资源 ID、存储类型以及换算为 GiB 的最终硬限额、软限额和宽限期。请求 schema 禁止额外字段。

## 4. 资源与设备映射

| 操作对象 | 存储目标 | 设备操作 | 可配置字段 |
| --- | --- | --- | --- |
| 项目组 | NetApp Qtree | Tree quota rule | 硬限额、软限额 |
| 项目组 | NetApp Volume | Volume 容量 | 仅硬限额 |
| 项目组 | Isilon Directory Quota | Directory quota | 硬限额、软限额、宽限期 |
| 用户目录 | NetApp Volume/Qtree | User quota rule，以当前系统用户名定位 | 硬限额、软限额 |
| 用户目录 | Isilon Directory | User quota，以路径和当前系统用户名定位 | 硬限额、软限额、宽限期 |

NetApp Volume 没有与 quota rule 等价的软限额语义，因此项目组直接绑定 NetApp Volume 时，前端隐藏软限额，后端拒绝携带软限额的请求。

## 5. 后端设计

Router 只负责路径参数、请求 schema、超级管理员依赖和响应组装。新增配额 service 负责：

1. 查询项目组或用户目录，并解析存储集群和存储目标。
2. 校验字段组合、资源归属、存储类型和共享目标。
3. 把输入单位换算为字节。
4. 根据 `storage_type` 创建现有 `NetAppClient` 或 `IsilonClient`，调用对应写方法。
5. 对设备结果执行读回校验。
6. 设备确认成功后，在同一数据库事务中更新本地记录并写调整记录。
7. 数据库提交成功后发送结果邮件；邮件失败只记录通知错误，不回滚已生效的设备配额和本地事务。
8. 始终关闭设备客户端；数据库异常时回滚本地事务，并记录设备已成功但本地同步失败的高优先级错误，交由下一次采集按设备真实值恢复一致。

不新增抽象基类。统一由一个 service 分派，厂商差异保留在两个现有客户端中。

### 5.1 共享目标

项目组调整前按实际 `volume_id` 或 `qtree_id` 查询关联项目组数量。存在多个项目组时返回 `409 Conflict`，不依赖可能过期的页面状态或 `associate_multiple_groups` 标记，也不调用设备。

### 5.2 NetApp

- Qtree 和用户配额先通过 quota rule 查询定位 UUID。
- 规则存在时调用 `PATCH /api/storage/quota/rules/{uuid}`。
- 规则不存在时调用 `POST /api/storage/quota/rules` 创建明确规则。
- 写入 `space.hard_limit` 和 `space.soft_limit`；清空软限额时使用 ONTAP 规定的无限制值。
- 项目组直接绑定 Volume 时，通过 Volume API 调整目标容量，只接受硬限额。
- 异步任务使用 `return_timeout` 等待；超时仍返回 job 时轮询到成功或失败，不能把 `202 Accepted` 直接当成调整完成。
- 写入后读取 quota report 或 Volume，核对最终值。

### 5.3 Isilon

- 通过 quota 列表定位 Directory quota 或以路径、当前系统用户名定位 User quota ID。
- 配额存在时调用 `PUT /platform/{version}/quota/quotas/{quota-id}`。
- 配额不存在时调用 quota collection `POST` 创建明确配额。
- 只构造 OneFS 支持写入的字段，设置 `thresholds.hard`、`thresholds.soft`、`thresholds.soft_grace`，不回传只读统计字段。
- 清空软限额时同时清空宽限期。
- 用户当前继承 `default-user` 配额时，不修改共享默认值；为该用户创建独立 User quota。
- 写入后读取具体 quota，核对最终阈值。

### 5.4 本地同步

- 项目组调整成功后同步其独占 `Volume` 或 `Qtree`，以及项目组的 `limit`、`soft_limit`、利用率和更新时间。
- 用户目录调整成功后同步该 `StorageUsage` 的 `limit`、`soft_limit`、利用率和更新时间。
- 后续采集继续以设备真实值覆盖本地记录，作为最终一致性保障。
- 设备失败或读回不一致时不提交本地限额变化。

## 6. 前端设计

项目组列表和用户目录列表的行操作增加“调整配额”，复用一个 `QuotaDialog`：

- 展示对象名称、存储类型、当前硬限额、当前软限额和已用容量。
- 硬限额、软限额共用一个 `GiB/TiB` 单位选择，打开时按当前值初始化。
- Isilon 设置软限额后显示并必填宽限期；NetApp 不显示宽限期。
- NetApp Volume 项目组只显示硬限额。
- 共享存储目标的项目组禁用入口并显示原因；后端仍执行独立校验。
- 前端和后端都校验软限额严格小于硬限额。
- 新硬限额小于当前已用容量时允许提交，但必须二次确认“可能立即阻止写入”。
- 提交成功后关闭弹窗并刷新当前列表；失败时保留输入值并展示友好错误。

## 7. 错误与安全

| 状态码 | 场景 |
| --- | --- |
| `403` | 当前用户不是超级管理员。 |
| `404` | 项目组、用户目录或关联存储资源不存在。 |
| `409` | 存储目标被多个项目组共享，或设备配额状态冲突。 |
| `422` | 限额关系、单位、宽限期或存储类型字段组合无效。 |
| 设备原始状态码 | NetApp/Isilon 返回 HTTP 错误时，接口原样保留设备状态码、响应体和 `Content-Type`，JSON 和纯文本均不包装，例如 OneFS `403 AEC_FORBIDDEN` 或 ONTAP `409`。 |
| `502` | 连接失败、超时、DNS/TLS 错误等设备未返回 HTTP 响应的情况，以及读回缺失或不一致。 |

设备凭据继续从 `StorageCluster` 读取，不写入日志、响应或调整记录。服务端日志记录集群 ID、资源类型、资源 ID、设备操作阶段、设备状态码和设备错误消息，不记录密码、认证头、Cookie 或请求凭据。配额接口仅超级管理员可调用，设备错误正文按厂商接口原样返回。所有厂商调用还必须遵守[NetApp 与 PowerScale 厂商接口契约](../storage-cluster/vendor-api-contracts.md#11-设备-http-错误契约)。

HTTPS 集群显式配置 `tls_verify=false` 时，配额调用关闭 urllib3 重复输出的 `InsecureRequestWarning`；该行为不改变实际证书校验配置，生产环境仍应配置受信任 CA 并启用校验。

## 8. 调整记录与邮件

复用 `StorageAlerts`，不新增审计表：

- `alert_type` 使用 `quota_adjustment`。
- `related_id`、`related_type` 指向项目组或用户目录。
- `related_info` 保存原硬/软限额、新硬/软限额、宽限期、存储类型和操作对象，不保存凭据。
- 描述统一使用“配额调整”，同时覆盖扩容和缩容。
- 复用现有邮件发送链路，将模板标题和正文改为“配额调整结果”。
- 只有设备调整成功后才在本地事务中写成功记录；事务提交成功后发送成功邮件。
- 邮件失败不改变接口的配额调整成功结果，只记录通知错误。
- 设备失败不写成功记录；设备成功但本地事务失败时记录高优先级服务端错误，后续采集以设备真实值恢复本地数据。

## 9. TDD 与验证

### 9.1 RED

- Schema：硬限额、软限额关系、额外字段、单位、Isilon 宽限期组合。
- Service：五种资源映射、共享目标拒绝、NetApp Volume 字段限制、Isilon linked 用户转独立配额。
- Client：NetApp GET/POST/PATCH 和异步任务；Isilon GET/POST/PUT；清空软限额。
- API：成功、权限拒绝、资源不存在、冲突、设备失败和读回不一致。
- 前端：条件字段、表单校验、缩容确认、共享目标禁用、成功刷新、失败保留。

先执行聚焦测试，确认失败来自缺少配额调整实现，再提交 RED 检查点。

### 9.2 GREEN

- 以最小实现通过同一组聚焦测试并提交 GREEN 检查点。
- 执行后端相关 pytest、前端相关 Vitest、lint、生产构建和 `git diff --check`。
- 达到仓库现行覆盖率门槛；无法运行的全量检查必须在发布跟踪中注明。

### 9.3 手工集成

更新 NetApp 和 Isilon 手工检查脚本，分别验证读取、调整、读回和恢复原值。脚本不得使用生产凭据或默认执行写操作。真实设备验证需要管理员显式提供测试目标，因此在完成前标记为“待人工验证”。

## 10. 文档与兼容边界

实现时同步更新：

- `docs/features/storage-quota/overview.md`
- `docs/overview/latest-features.md`
- `docs/tracking/current-release.md`
- 相关 API、权限和手工验证说明

旧 `POST /storage-usages/expand` 将输入解释为扩容量，语义与本功能的最终目标配额冲突，已由两个资源化 `PATCH .../quota` 接口替代，不再保留旧页面入口和后端路由。

## 11. 非目标

- 文件硬限额、文件软限额。
- NetApp 用户映射开关。
- 批量配额调整。
- 普通管理员或项目管理员执行配额调整。
- 共享存储目标的单项目组配额调整。
- 新增后台任务队列或新的设备客户端抽象层。
