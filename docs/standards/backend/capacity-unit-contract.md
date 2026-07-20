# 容量单位 API 契约

本规范适用于 DiskPulse 所有存储容量 API、容量树、实时趋势、健康分析、预测和 Mock 响应。它是容量数值单位、转换和前端展示的唯一规范来源。

## 1. 原始值与显示值

- 数据库、采集、计算和兼容数值字段以 GB 为原始口径；不得为了页面展示而改变原始字段的数值或名称。
- 任一非空容量字段必须同时在响应的 `capacity` 映射中提供 `{ "value": number, "unit": "MB"|"GB"|"TB"|"PB" }`。字段名与原始字段一致，例如 `limit`、`soft_limit`、`used`、`allocated`、`storage_used`、`limit_gb`、`used_gb`、`available_gb`、`quota_limit_gb` 和 `capacity_delta`。
- `null`、非有限值或响应中不存在的容量字段不得伪造为零；其 `capacity` 项省略。消费者必须显示空态，而不是自行推断单位。
- 新增包含容量字段的 Pydantic 响应模型必须继承 `CapacityResponseBase`，或以等价方式复用 `format_capacity_fields` 并明确声明字段映射。

## 2. 二进制转换规则

转换以原始 GB 值的绝对值判断，保留原数值正负号，并最多保留两位小数：

| 原始 GB 值的绝对值 | 返回单位 | 返回值 |
| --- | --- | --- |
| 小于 `1` | `MB` | `GB × 1024` |
| `1` 至 `1024`（含） | `GB` | 原始 GB 值 |
| 大于 `1024` 至 `1024 × 1024`（含） | `TB` | `GB ÷ 1024` |
| 大于 `1024 × 1024` | `PB` | `GB ÷ (1024 × 1024)` |

因此恰好 `1024 GB` 返回 `1024 GB`，恰好 `1024 TB` 返回 `1024 TB`；只有超过边界才提升到下一单位。容量变化量也使用同一规则，例如负扩容值保留负号。

## 3. 曲线、树和专用响应

- 容量时间序列必须以顶层 `data_unit` 标明曲线 `data` 的数值单位；服务端必须在返回前将曲线数值及同口径容量限额提供为该单位的数值。百分比阈值保持 `%` 口径，不参与容量换算。
- 容量池、存储空间、Qtree（NetApp）、项目、项目组和存储集群的实时容量曲线使用 `data_unit="TB"`；用户目录容量曲线使用 `data_unit="GB"`。
- 利用率曲线使用 `data_unit="%"`，用户目录文件数曲线使用 `data_unit="count"`；它们不是容量，不能套用容量单位转换。
- 存储空间监控和存储集群健康容量变化使用 TB。容量树节点必须分别返回 `capacity_unit` 与 `value_unit`，使容量、利用率和其他数值可独立解释。
- 预测曲线原始序列使用 `data_unit="GB"`；预测总量、容量计划变化量和 P10/P50/P90 点仍各自返回字段级 `capacity` 映射。

## 4. 消费与演进要求

- 前端必须优先使用接口返回的 `capacity.{field}`，通过 `formatCapacity` 直接拼接 `value` 和 `unit`；不得硬编码 `GB`、`TB` 等后缀或重复换算。
- `formatCapacityFromGb` 仅可用于旧接口兼容和没有字段级单位的受控回退，不能成为新增 API 或 Mock 的常规展示路径。
- 新增容量字段、曲线或树节点时，后端必须补齐单位契约和边界测试；前端和 Mock 必须同步覆盖接口返回 MB、GB、TB、PB 的展示。

实现入口为 `backend/schemas/capacitySchema.py`；存储趋势的目标单位和数值换算由 `backend/services/storageTrendService.py` 统一处理。
