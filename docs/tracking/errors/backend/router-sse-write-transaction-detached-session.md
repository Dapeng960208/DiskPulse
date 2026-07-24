# Router 通用写事务提前结束 SSE 会话

## 错误内容

函数级 `get_write_db` 在 SSE 路由返回 `StreamingResponse` 后立即提交，SQLAlchemy 默认使 `current_user` 过期；流生成器随后访问 `current_user.id` 时因 session 已关闭而抛出 `DetachedInstanceError`。

## 解决方案

对需要跨响应生命周期的流式写路由使用 `@skip_write_transaction` 排除通用事务依赖。流服务在首事件、成功结束、取消和异常处使用短检查点持久化状态，且不跨模型调用持有事务。

## 备注

- 分类：`backend`
- 首次出现：2026-07-24，`2026-07-24-router-transactions-startup-security`。
- 最近出现：2026-07-24，`2026-07-24-router-transactions-startup-security`。
- 出现次数：1。
