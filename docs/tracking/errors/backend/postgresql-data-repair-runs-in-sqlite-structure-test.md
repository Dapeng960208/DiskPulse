# PostgreSQL 历史数据修复在 SQLite 结构验证中执行

## 错误内容

SQLite 的结构迁移测试从兼容基线升级时，先后执行 `000000000019` 和 `000000000020` 中仅适用于 PostgreSQL 的历史数据修复 SQL。SQL 包含 `interval`、`AT TIME ZONE`、`regexp_replace` 与 `UPDATE ... FROM`，SQLite 因语法不支持而失败。

## 解决方案

历史数据修复迁移在 `upgrade()` 开始处检查连接方言，仅在 PostgreSQL 执行，并以注释说明修复的数据前提。SQLite 测试继续覆盖结构迁移；不要以跳过方式绕过通用 DDL 或跨方言结构变更。

## 备注

- 分类：`backend`
- 首次出现：2026-07-24，`2026-07-24-router-transactions-startup-security`。
- 最近出现：2026-07-24，`2026-07-24-router-transactions-startup-security`。
- 出现次数：2。
- 出现记录：`000000000019` 的 QuestDB 性能派生记录修复、`000000000020` 的 DiskPulse 告警证据修复。
