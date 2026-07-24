# UTC 迁移安全契约尚未落地

## 错误内容

在主线 `efd8504` 的 `test_utc_time_contract.py` 中，PostgreSQL 非空数据库应在任何 DDL 前拒绝 UTC 迁移，且离线编译结果应包含锁超时设置；当前 `000000000025_utc_time_contract.py` 未实现这两项保护，聚焦测试出现 2 个失败。

## 解决方案

为 PostgreSQL 在线迁移补充 DDL 前的数据存在性检查与明确的锁等待上限，并让离线 SQL 编译输出同样反映该锁策略；实现后运行 `test/test_utc_time_contract.py`。

## 备注

- 分类：`backend`
- 出现次数：1
- 首次出现：2026-07-24 `2026-07-24-router-transactions-startup-security` 主线同步
- 最近出现：2026-07-24 `2026-07-24-router-transactions-startup-security` 主线同步
- 出现记录：`sessions/2026-07-24-router-transactions-startup-security/errors.md`
- 本会话按用户指示不扩展处理该主线基线问题。
