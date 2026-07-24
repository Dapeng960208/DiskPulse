# 存储趋势与实时详情

## 统一趋势

`StorageTrendChart` 统一服务于容量池、存储空间、Qtree（NetApp）、项目、项目组、用户目录、存储集群和 Dashboard。组件复用现有 ECharts 与主题 token，不新增图表依赖。

- 单对象趋势按有效三级阈值分段显示；多对象比较保留对象身份颜色，不把不同限额混为同一容量阈值。
- `used`、`use_ratio`、`alert_ratio` 和用户目录的 `file_used` 是受支持指标。非法指标由后端拒绝，QuestDB 查询只使用服务端白名单列。
- `alert_ratio` 由后端明确返回实际读取的历史口径；软限额缺失时不以当前值反推历史阈值。
- 组件响应主题和容器尺寸变化，并在卸载时释放图表实例。

## 数据契约

趋势响应可携带 `trend_meta`：

| 字段 | 含义 |
| --- | --- |
| `quota_basis` | 当前告警口径：`hard` 或 `soft`。 |
| `rule_source` | 有效规则来源：`system`、`project` 或 `group`。 |
| `thresholds` | 重要、严重、紧急三级百分比阈值。 |
| `quota_limit_gb` | 当前口径的限额；不适用时为 `null`。 |
| `quota_limit_tb` | 当实时容量曲线使用 TB 时，与 `quota_limit_gb` 等价的 TB 限额；不适用时为 `null`。 |
| `ratio_indicator` | `alert_ratio` 对应的历史字段。 |

有效规则优先级为项目组、项目、系统；物理容量视图使用硬容量和系统规则。

## 容量单位契约

容量字段、`data_unit`、二进制换算边界和前端消费方式统一遵守[容量单位 API 契约](../../../standards/backend/capacity-unit-contract.md)。本专题只定义趋势元数据和指标选择，不重复容量显示规则。

项目容量趋势读取 QuestDB 的 `project_storage_usages`。每轮存储采集先在 PostgreSQL 内完成项目组更新和项目去重汇总，事务提交成功后才写入项目趋势；只有该项目所有启用项目组所在的存储集群均采集成功时才写入，避免混入跨集群的部分结果。

所有容量趋势表的 `updated_at` 都表示 UTC 瞬时。写入边界把 DiskPulse `Asia/Shanghai` naive 墙上时间转换为 UTC naive 值，查询边界绑定 UTC `Z` 字符串，API 返回图表时间前再转换为 `Asia/Shanghai`；不得依赖 worker、API 或浏览器宿主机时区。

## 详情展示

- 资源详情使用动态面包屑，不额外复制资源名称或时间摘要。
- 实时监控、存储集群健康分析和存储空间监控的时间范围筛选复用[统一日期时间范围选择器](../../experience/time-range-picker/frontend.md)，保证快捷范围和时间格式一致。
- 实时告警表显示面向用户的紧急程度、触发值和时间；兼容历史等级并保留未知值。表格复用共享 `DataTable` 的紧凑密度、加载状态和容器内滚动，不在页面内重复定义 Element Plus 表格样式。
- 用户目录详情以懒加载页签展示“容量趋势、配额历史、耗尽风险、关联事件”；容量趋势页已提供关联告警表，因此不再提供重复的“告警”页签。容量趋势只展示稳定的目录、限额、已用量和利用率摘要，暂未稳定的扩展字段不作为当前页面契约。
- 配额历史、[耗尽风险](../../ai/capacity-prediction/frontend.md)和事件分别遵守配额、预测发布和项目 RBAC 边界；关联告警在容量趋势页遵守资源过滤边界，不重复取数。

真实历史数据、设备权限和登录态交互仍需在部署环境核对。
