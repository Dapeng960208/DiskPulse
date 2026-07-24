# 横切 API 与迁移契约变化后测试预期未同步

## 错误内容

近三日提交同时改变了容量曲线序列化、字段级容量对象、嵌套项目组容量和 Alembic 当前 head，但部分核心测试仍断言旧字典、旧字段形态或旧 head 数量。除已单独归类的实时 TB 与配额角色问题外，后端全量测试仍出现多项契约漂移失败。2026-07-24 的 UTC 时间契约又使仍构造 naive 持久化时间、或 mock 已删除裸 `datetime.now()` 的旧测试暴露为同类漂移；这些夹具必须显式使用 aware UTC 或 mock `utc_now()`。

## 解决方案

以当前 schema、容量单位规范、嵌套资源事实文档和 `alembic heads` 为权威，统一更新横切契约断言；把容量序列化、嵌套响应、迁移 head 和权限角色矩阵纳入同一次影响面核对。

## 备注

- 分类：`backend`
- 出现次数：3
- 首次出现：2026-07-20 近三日代码审查修复会话
- 出现记录：`sessions/2026-07-20-recent-code-review-remediation/errors.md`
- 最近出现：2026-07-24，`2026-07-24-router-transactions-startup-security`：四个迁移契约测试仍把 `000000000016` 或 `000000000022` 写死为当前 head；改为验证单一 head 与受保护修订的可达性。
- 出现记录：`sessions/2026-07-24-utc-time-contract/errors.md`
