# 存储配额

## 数据与展示

NetApp 和 PowerScale 配额同时支持硬限额与软限额。软限额为空、零或负值时视为未设置，接口和页面以空值表达，不能显示为 `0%`。

| 资源 | 硬限额来源 | 软限额来源 |
| --- | --- | --- |
| NetApp 用户、Qtree 和 Volume 配额 | `space.hard_limit` | `space.soft_limit` |
| PowerScale 用户与目录配额 | `thresholds.hard` | `thresholds.soft` |

用户目录、项目组、存储空间和 Qtree（NetApp）展示硬/软限额与对应利用率；物理容量层不使用软限额。告警口径由有效告警规则决定，软限额不可用时不得回退为硬限额。

## 集群采集

启用的存储集群在创建、启用或连接配置更新后异步触发采集；保存请求不等待设备响应。协议和 TLS 校验按集群配置，HTTP 不适用于 TLS 校验且仅应在可信隔离网络使用。

## 直接配额调整

超级管理员可以调整项目组和用户目录的最终目标配额：

- `PATCH /groups/{group_id}/quota` 仅适用于独占存储目标；共享 Volume/Qtree 返回 `409`。
- `PATCH /storage-usages/{storage_usage_id}/quota` 按当前研发用户名调整用户配额。
- 硬限额必填；软限额必须小于硬限额。PowerScale 设置软限额时还需要宽限期。
- 新硬限额低于已用容量时，必须由超级管理员显式传入 `force_below_usage=true` 和 1--256 字符理由。
- 同一设备规则由 Redis 非阻塞锁串行化；锁冲突返回 `409 quota_adjustment_in_progress`，Redis 不可用时拒绝写入。
- 设备写入后读取目标配额验证结果。超时或连接中断不重发，只读回匹配时标记 `post_timeout_readback`，否则返回 `502 quota_outcome_unknown` 和 `operation_id`。
- `POST .../quota/reconcile` 只读设备并修复本地数据；`GET .../quota/history` 返回最近十条脱敏结果。

设备写入继续受原路由授权、Pydantic 校验和审计保护。真实设备写入与回读需在隔离环境验证。
