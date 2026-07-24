# AI 用户目录工具混用用户名与整数 ID

## 错误内容

`list_storage_usages.user_id` 同时声明为整数和字符串，AI 因无法读取内部用户数字 ID 而把研发用户名传入该字段。FastAPI 接受字符串后，SQLAlchemy 将 PostgreSQL 整数列 `storage_usages.user_id` 与用户名比较，触发 `InvalidTextRepresentation: invalid input syntax for type integer`，接口返回 HTTP 500。AI 工具层又把 5xx 描述为“参数已通过接口校验”，既掩盖了参数契约缺陷，也会诱导模型继续尝试其他参数。

## 解决方案

将 `user_id` 收紧为 `integer | null`，仅兼容历史空字符串到 `null` 的边界转换；新增独立的 `rd_username: string | null` 精确查询参数，并拒绝两者同时出现。数据库查询继续使用 SQLAlchemy 参数化表达式，通过 `StorageUsage.user.has(User.rd_username == rd_username)` 查询用户名。所有 AI 暴露路由增加全量 Schema 契约测试，拒绝混合不兼容标量类型和虚假的可空默认值。5xx 工具结果改为 `error_type=server_error`、`retryable=false`，当前回合阻止同一工具再次执行并关闭下一轮工具列表。

## 备注

- 首次出现：2026-07-24，`2026-07-24-ai-tool-parameter-contracts` 会话。
- 最近出现：2026-07-24，用户目录查询把研发用户名 `guojianpeng` 作为 `user_id` 传入 PostgreSQL 整数条件。
- 出现次数：1。
