# UTC 时间契约整改错误记录

## 已记录问题

- [横切 API 与迁移契约变化后测试预期未同步](../../errors/backend/cross-cutting-contract-test-drift.md)
  - 本会话首次运行全量后端测试时，旧测试夹具向 `UTCDateTime` 写入 naive datetime，或 monkeypatch 已移除的裸 `datetime.now()`，触发同类测试契约漂移。
  - 已更新受影响的持久化夹具、Dashboard UTC 查询边界和任务时钟 mock；合并后的后端全量测试恢复通过。
