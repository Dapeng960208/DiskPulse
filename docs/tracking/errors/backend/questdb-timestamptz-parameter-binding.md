# QuestDB 遥测质量快照使用 `timestamptz` 绑定参数

## 错误内容

执行 `telemetry_quality_snapshot_task` 时，`_raw_point_count` 将带时区的 Python `datetime` 直接作为 QuestDB PGWire 查询参数传递。SQLAlchemy/psycopg2 将其适配为 `timestamptz`，QuestDB 因不支持该常量而报出 `psycopg2.DatabaseError: invalid constant: timestamptz`，导致派生遥测质量任务失败。

## 解决方案

将窗口下限先规范化为 UTC，再以 RFC 3339 `Z` 字符串绑定到 QuestDB 查询参数；不要把带时区的 `datetime` 直接传给 QuestDB PGWire。为性能和容量使用两条原始点查询保留同一回归测试。

## 备注

- 首次出现：2026-07-20，`2026-07-20-questdb-telemetry-quality-timestamp`。
- 最近出现：2026-07-20，`2026-07-20-questdb-telemetry-quality-timestamp`。
- 出现次数：1。
