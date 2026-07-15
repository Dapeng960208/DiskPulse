# AI 对话与管理中心

实现细节：

- [后端实现](./backend.md)：对话主链路、Provider 适配、动态工具、事务、安全和审计。
- [前端实现](./frontend.md)：SSE 分块、会话状态、失败恢复、Markdown 安全和路由权限。

## 1. 功能边界

- “AI 助手”面向所有已登录用户，不提供匿名访问。
- 侧边栏“AI 助手”固定显示在“项目组”之后、“告警”之前。
- 会话只按 `user_id` 隔离，不绑定项目；跨用户读取、删除或发送消息统一返回 `404`。
- “系统管理 > AI 中心”只允许 `backend/config.yml` 中 `super_admin_usernames` 配置的超级管理员访问，其他用户返回 `403`。
- 首版不包含项目级 AI 设置、上传总结、项目绑定、写工具和审计自动清理。

## 2. 数据与安全

Alembic `000000000003` 新增：

- `ai_configs`：Provider、模型、温度、Token 上限、启用状态和加密后的 API Key。
- `ai_conversations`：用户、模型、标题和时间戳。
- `ai_messages`：会话内用户与助手消息。
- `ai_audit_logs`：请求状态、工具调用计数、脱敏摘要、Trace ID 和错误摘要。

API Key 使用 `cryptography` 的 Fernet 加密，密钥由独立的 `ai.config_secret_key` 派生。管理接口只返回掩码和是否已配置，不返回明文或密文。审计只保存消息长度、响应长度和工具名称/状态，不保存原始提问、工具参数或工具结果。

## 3. 运行配置

真实配置写入被忽略的 `backend/config.yml`，结构参考 `backend/config.example.yml`：

```yaml
redis:
  host: localhost
  port: 6379

ai:
  config_secret_key: replace-with-an-independent-random-secret
  request_timeout_seconds: 60
  max_tool_iterations: 4
  chat_rate_limit_per_minute: 10
```

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

流式接口事件顺序由下列固定事件组成：`accepted`、`user_message`、`status`、`tool_call_started`、`tool_call_finished`、`delta`、`completed`、`error`、`cancelled`。服务端保存最近 20 条历史；首条用户消息会自动生成最多 32 字的会话标题。前端可中止当前流、恢复失败输入，并忽略已切换旧会话的迟到事件。

## 6. 动态只读工具

只有同时满足以下条件的路由会注册为 AI 工具：

1. FastAPI `GET` 路由；
2. 显式声明 `openapi_extra.ai_exposed=true`；
3. 返回 JSON。

工具参数由路由 Path/Query 参数动态生成 Pydantic 校验模型。执行时使用当前用户的 Bearer Token 通过内部 ASGI 请求调用原业务 API，因此继承原接口权限和数据范围。首批覆盖项目、项目组、项目组标签、存储集群、容量池、存储空间、Qtree（NetApp）、用户目录、告警、大文件和实时趋势；配置、用户管理、离职备份、导出和图片接口不开放。

新增工具时必须显式补充唯一的 `ai_name` 和清晰的 `ai_description`，不得开放写路由或返回文件/图片的路由。

## 7. 管理 API

- `GET|POST /admin/ai-models`
- `PATCH|DELETE /admin/ai-models/{id}`
- `POST /admin/ai-models/{id}/test`
- `GET /admin/ai-audits`
- `GET /admin/ai-audits/{id}`
- `GET /admin/ai-audits/conversations/{conversation_id}`

前端入口为 `/admin/ai-center?tab=models|audit`，隐藏审计详情路由为 `/admin/ai-center/audits/:id`。

## 8. 部署步骤

1. 在真实 `backend/config.yml` 设置独立 AI 加密密钥和 Redis 地址。
2. 执行 `alembic upgrade head` 创建 AI 表。
3. 启动后由超级管理员进入 AI 中心创建模型并执行真实连接测试。
4. 确认 Redis DB 7 可访问，再由普通登录用户完成流式对话冒烟。

部署前不要提交真实 API Key、AI 加密密钥或生产 Provider 地址。
