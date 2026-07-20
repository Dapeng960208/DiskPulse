# QuestDB 派生监控任务使用 `timestamptz` 绑定参数

## 错误内容

派生监控任务将带时区的 Python `datetime` 直接作为 QuestDB PGWire 查询参数传递。SQLAlchemy/psycopg2 将其适配为 `timestamptz`，QuestDB 因不支持该常量而报出 `psycopg2.DatabaseError: invalid constant: timestamptz`。已出现于 `telemetry_quality_snapshot_task` 的 `_raw_point_count` 和 `performance_anomaly_scan_task` 的 `_performance_rows`，会导致相应派生任务失败，但不会回滚原始采集。

## 解决方案

将窗口下限先规范化为 UTC，再以 RFC 3339 `Z` 字符串绑定到 QuestDB 查询参数；不要把带时区的 `datetime` 直接传给 QuestDB PGWire。每个新增或修改的 QuestDB 查询都要覆盖参数绑定回归，至少包括质量统计和性能异常扫描路径。

## 备注

- 首次出现：2026-07-20，`2026-07-20-questdb-telemetry-quality-timestamp`。
- 最近出现：2026-07-20，`2026-07-20-questdb-performance-cutoff`。
- 出现次数：2。
- 2026-07-20，`2026-07-20-questdb-telemetry-quality-timestamp`：质量统计原始点查询直接绑定带时区时间。
- 2026-07-20，`2026-07-20-questdb-performance-cutoff`：性能异常扫描直接绑定带时区截止时间。
