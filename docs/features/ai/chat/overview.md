# AI 对话与管理中心

实现细节：

- [后端实现](./backend.md)：对话主链路、Provider 适配、动态工具、事务、安全和审计。
- [前端实现](./frontend.md)：SSE 分块、会话状态、失败恢复、Markdown 安全和路由权限。

## 1. 功能边界

- “AI 助手”面向所有已登录用户，不提供匿名访问。
- 侧边栏“AI 助手”固定显示在“项目组”之后、“告警”之前。
- 会话只按 `user_id` 隔离，不绑定项目；跨用户读取、删除或发送消息统一返回 `404`。
- “系统管理 > AI 中心”只允许 `backend/config.yml` 中 `super_admin_usernames` 配置的超级管理员访问，其他用户返回 `403`。
- 不包含项目级 AI 设置、上传总结、项目绑定和审计自动清理；仅有显式标记并经超级管理员双层校验的系统管理写工具属于例外。

## 2. 数据与安全

AI 持久化包含：

- `ai_configs`：Provider、模型、温度、Token 上限、启用状态和加密后的 API Key。
- `ai_conversations`：用户、模型、标题和时间戳。
- `ai_messages`：会话内用户与助手消息。
- `ai_audit_logs`：请求状态、工具调用计数、脱敏摘要、Trace ID 和错误摘要。

API Key 使用 `cryptography` 的 Fernet 加密，密钥由独立的 `ai.config_secret_key` 派生。管理接口只返回掩码和是否已配置，不返回明文或密文。审计只保存消息长度、响应长度和工具名称/状态，不保存原始提问、工具参数或工具结果。

## 3. 运行配置

真实配置写入被忽略的 `backend/config.yml`，结构参考 `backend/config.example.yml`：

- `config_secret_key` 必须是至少 16 字符的独立非占位密钥；更换后既有 API Key 密文无法解密。
- 限流固定使用 Redis DB 7，键命名空间为 `diskpulse:ai:rate:*`，每用户每分钟默认 10 次消息请求。
- Redis 不可用时聊天接口返回 `503`；超限返回 `429` 并携带 `Retry-After`。
- Provider 请求默认超时 60 秒，工具循环最多 4 轮。

## 4. Provider 与连接测试

支持 `openai`、`openrouter`、`ollama`、`claude`。OpenAI 兼容 Provider 使用 `/chat/completions`，Claude 使用 `/v1/messages`；未配置 Base URL 时使用各 Provider 默认地址。AI 中心的“连接测试”会向 Provider 真实发送最小消息，不以配置格式校验代替网络调用。

## 5. 对话与 SSE

用户 API 均挂载在 `/storage-pulse/api`：

- `GET /ai/models`
- `GET|POST /ai/conversations`
- `GET|DELETE /ai/conversations/{id}`
- `POST /ai/conversations/{id}/messages`
- `POST /ai/conversations/{id}/messages/stream`

流式接口事件顺序由下列固定事件组成：`accepted`、`user_message`、`status`、`tool_call_started`、`tool_call_finished`、`delta`、`completed`、`error`、`cancelled`。客户端必须先收到 `accepted`，终态必须是最后一个已知事件；违反该顺序或截断时保留部分输出并进入可重试失败态。服务端保存最近 20 条历史；首条用户消息会自动生成最多 32 字的会话标题。

工具轮次达到 `max_tool_iterations` 后不会直接把已有数据丢弃为服务故障：当前回合禁止再调用工具并总结已获得信息，助手消息标记为 `degraded`，附带“继续查询”操作。工具参数不是 JSON 对象时，系统最多两次要求模型按工具契约修复；原始非法参数不会展示或持久化。只有用户点击恢复操作才会开始新的受限查询回合。

## 6. 动态工具与系统管理工具

常规 AI 工具必须是 FastAPI `GET` 路由且显式声明 `openapi_extra.ai_exposed=true`；它们对所有登录用户保持只读。

系统管理工具必须额外声明 `openapi_extra.ai_system_management=true`，并且当前用户命中 `backend/config.yml` 的 `super_admin_usernames`。只有超级管理员可见这组 `GET`、`POST`、`PUT`、`PATCH`、`DELETE` 工具；普通用户不会从工具定义中获知它们。

当前系统管理范围包括存储集群、容量池、存储空间、项目组标签、用户和 AI 模型配置的非删除已授权操作，以及存储设置和离职备份记录的只读查询。项目组和用户目录各有一条“调整限额”工具，只向超级管理员开放；它们复用既有配额调整 API。所有删除工具、创建用户、创建容量池、创建/更新存储空间、全部 Qtree（NetApp）工具、存储设置更新和 AI 审计查询保持关闭。

工具参数由路由 Path/Query 参数和写请求的 Pydantic `body` 信封动态校验。执行阶段再次校验超级管理员身份，再携带当前用户 Bearer Token 通过内部 ASGI 调用原业务 API；因此旧注册表不能绕过权限。转发请求体时不包含 Pydantic 计算字段；删除接口的 `204 No Content` 视为成功空结果。

新增工具必须显式补充唯一的 `ai_name` 和清晰的 `ai_description`；不得按路由路径猜测权限，也不得开放文件或图片响应。

## 7. 管理 API

- `GET|POST /admin/ai-models`
- `PATCH|DELETE /admin/ai-models/{id}`
- `POST /admin/ai-models/{id}/test`
- `GET /admin/ai-audits`
- `GET /admin/ai-audits/{id}`
- `GET /admin/ai-audits/conversations/{conversation_id}`

前端入口为 `/admin/ai-center?tab=models|audit`，隐藏审计详情路由为 `/admin/ai-center/audits/:id`。

## 8. 部署边界

部署必须提供独立 AI 加密密钥、可用 Redis 和当前数据库迁移。超级管理员通过 AI 中心配置模型并执行真实连接测试；普通用户的流式对话需在部署环境冒烟。不得提交真实 API Key、AI 加密密钥或生产 Provider 地址。
