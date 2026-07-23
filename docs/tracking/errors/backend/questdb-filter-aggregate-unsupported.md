# QuestDB 不支持 PostgreSQL 聚合 `FILTER` 语法

## 错误内容

使用 PostgreSQL 风格的 `count(*) FILTER (WHERE timestamp > :now)` 审计 QuestDB 未来时间行时，QuestDB PGWire 返回语法错误：在 `FILTER` 的左括号处只接受逗号、`FROM` 或 `OVER`。该写法会使只读数据审计在第一张表即中断。

## 解决方案

不要在 QuestDB 使用 PostgreSQL 聚合 `FILTER (WHERE ...)`。把总量/时间边界与条件计数拆成独立查询，例如先执行 `SELECT count(), min(ts), max(ts) FROM table`，再执行 `SELECT count() FROM table WHERE ts > :now_utc`。新增 QuestDB SQL 必须按 QuestDB 支持的语法验证，不能仅因使用 PGWire 就假设完整 PostgreSQL 兼容。

## 备注

- 首次出现：2026-07-23，`2026-07-23-questdb-utc-time-contract`。
- 最近出现：2026-07-23，`2026-07-23-questdb-utc-time-contract`。
- 出现次数：1。
