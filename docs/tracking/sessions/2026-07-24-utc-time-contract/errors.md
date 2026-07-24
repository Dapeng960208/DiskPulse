# UTC 时间契约整改错误记录

## 已记录问题

- [横切 API 与迁移契约变化后测试预期未同步](../../errors/backend/cross-cutting-contract-test-drift.md)
  - 本会话首次运行全量后端测试时，旧测试夹具向 `UTCDateTime` 写入 naive datetime，或 monkeypatch 已移除的裸 `datetime.now()`，触发同类测试契约漂移。
  - 已更新本整改覆盖的存储健康与软配额测试；其余历史测试需要按同一 aware UTC 夹具规则分批治理。
