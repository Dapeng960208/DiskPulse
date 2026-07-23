# PostgreSQL 显式 ID 种子后序列未同步

## 错误内容

`vendor_event_definitions` 的早期迁移使用显式 `id` 写入种子数据，但 PostgreSQL 自增序列没有同步到表中最大 ID。后续迁移省略 `id` 插入新事件定义时，序列返回已存在的 `id=2`，触发 `vendor_event_definitions_pkey` 唯一约束错误并回滚整个 Alembic 事务。

## 解决方案

最终方案将事件目录数据移出 Alembic revision，统一由独立初始化脚本插入且不提供显式 `id`、`created_at`、`updated_at`。迁移只管理结构，因此不再需要 revision 内的 PostgreSQL 序列同步；初始化测试覆盖空库写入、部分已有数据、重复执行和事务回滚，防止再次出现显式主键与序列脱节。

## 备注

- 会话：`2026-07-22-event-time-association`
- 首次与最近出现：2026-07-22
- 出现次数：1
- 触发环境：PostgreSQL `10.0.91.37:5432/diskpulse`，执行 `000000000017 -> 000000000018`
