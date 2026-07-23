# PostgreSQL 对含 JSON 的整行执行 DISTINCT 失败

## 错误内容

为 `storage_alerts` 建立定向备份时使用 `SELECT DISTINCT alert.*`，PostgreSQL 因表中包含 `json` 列而报 `could not identify an equality operator for type json`，整个备份事务回滚。

## 解决方案

需要按关联表筛选且源表主键唯一时，使用 `WHERE EXISTS` 代替连接后的整行 `DISTINCT`；既避免 JSON 相等比较，也不会因一对多连接复制源行。备份表创建和计数继续放在同一事务中。

## 备注

- 首次出现：2026-07-23，`2026-07-23-questdb-utc-time-contract`。
- 最近出现：2026-07-23，`2026-07-23-questdb-utc-time-contract`。
- 出现次数：1。
