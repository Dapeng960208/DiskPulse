# AI 对话与管理中心

实现细节：

- [后端实现](./backend.md)：对话主链路、Provider 适配、动态工具、事务、安全和审计。
- [前端实现](./frontend.md)：SSE 分块、会话状态、失败恢复、Markdown 安全和路由权限。

## 1. 功能边界

- “AI 助手”面向所有已登录用户，不提供匿名访问。
- 侧边栏“AI 助手”固定显示在“项目组”之后、“告警”之前。
- 会话只按 `user_id` 隔离，不绑定项目；跨用户读取、删除或发送消息统一返回 `404`。
- “系统管理”的“智能治理”分区中，“AI 中心”只允许 `backend/config.yml` 中 `super_admin_usernames` 配置的超级管理员访问，其他用户返回 `403`。
- 不包含项目级 AI 设置、上传总结、项目绑定和审计自动清理；仅有显式标记并经超级管理员双层校验的系统管理写工具属于例外。

## 2. 数据与安全

AI 持久化包含：

- `ai_configs`：Provider、模型、温度、Token 上限、启用状态、加密后的 API Key，以及模型推理能力缓存、获取状态、脱敏错误和刷新时间。
- `ai_platform_settings`：全局默认聊天模型。初始值可以为空；默认模型必须保持启用且允许聊天。
- `ai_conversations`：用户、模型、标题和时间戳。
- `ai_messages`：会话内用户与助手消息；用户消息同时保存本次选择的 `reasoning`，用于恢复会话内的推理设置。
- `ai_audit_logs`：请求状态、工具调用计数、脱敏摘要、Trace ID 和错误摘要。

API Key 使用 `cryptography` 的 Fernet 加密，密钥由独立的 `ai.config_secret_key` 派生。管理接口只返回掩码和是否已配置，不返回明文或密文。审计只保存消息长度、所选推理值、实际发送值、响应长度和工具名称/状态，不保存原始提问、工具参数、工具结果或 Provider 返回的思维链；聊天历史和页面也不展示思维链。配额确认例外仅在所属审计中保留白名单预览字段、最终决定和 `ok`/限长可读错误，以便会话重载恢复卡片，不保留 Redis 中的执行参数或设备完整返回。

## 3. 运行配置

真实配置写入被忽略的 `backend/config.yml`，结构参考 `backend/config.example.yml`：

- `config_secret_key` 必须是至少 16 字符的独立非占位密钥；更换后既有 API Key 密文无法解密。
- 限流固定使用 Redis DB 7，键命名空间为 `diskpulse:ai:rate:*`，每用户每分钟默认 10 次消息请求。
- Redis 不可用时聊天接口返回 `503`；超限返回 `429` 并携带 `Retry-After`。
- Provider 请求默认超时 60 秒，工具循环最多 4 轮。

## 4. Provider 与连接测试

支持 `openai`、`openrouter`、`ollama`、`claude`、`claude_code`、`deepseek`、`dashscope`、`volcengine`、`zhipu`、`moonshot`、`minimax`、`qianfan` 和 `hunyuan`。管理页面为这些 Provider 提供默认且可编辑的 Base URL；AI 中心的“连接测试”会向 Provider 真实发送最小消息，不以配置格式校验代替网络调用。

模型推理能力按“Provider 动态元数据、内置官方能力目录、`unknown`”顺序解析。`GET /ai/models` 对每个模型返回 `is_default` 和统一的 `reasoning_control`：

- `kind` 为 `effort`、`toggle` 或 `none`，分别表示原生多档强度、原生思考开关或不可调节。
- `options` 只包含模型原生支持的值；`provider_default` 表示 Provider 默认值，`mandatory` 表示该模型是否强制推理。
- `source` 为 `provider`、`official_catalog` 或 `unknown`，并返回 `status` 和 `updated_at` 供页面展示能力状态。
- `auto` 是所有模型都允许的客户端值，表示不发送推理控制参数并遵循 Provider 默认行为。能力获取失败或模型未知时只能选择 `auto`，不得猜测或静默降级为其他档位。

不同 Provider 保留原生语义：OpenAI、OpenRouter、部分 Ollama GPT-OSS、部分 GLM、Kimi 和混元模型使用原生强度档位；Ollama 其他思考模型、DeepSeek、通义千问、豆包及部分国内模型使用原生开关；官方未声明可调能力的模型返回 `none`。系统不把思考预算或开关近似成虚假的强度档位。

`claude_code` 通过 Claude Agent SDK 调用，只注册 DiskPulse 动态 MCP 工具，并禁用文件、Shell 等 Claude Code 内置工具；工具执行继续使用当前登录用户的认证、权限、项目隔离、配额确认和审计边界。

## 5. 对话与 SSE

用户 API 均挂载在 `/storage-pulse/api`：

- `GET /ai/models`
- `GET|POST /ai/conversations`
- `GET|DELETE /ai/conversations/{id}`
- `POST /ai/conversations/{id}/messages`
- `POST /ai/conversations/{id}/messages/stream`

创建会话时 `model_id` 可以省略；服务端使用管理员配置的默认聊天模型。没有默认模型且调用方未显式传入模型时返回明确配置错误。已有会话继续绑定创建时的模型，不随默认模型变化。

同步和流式消息请求都接受每条消息的 `reasoning`。默认值 `auto`；其他值只能是能力契约声明的 `on`、`off` 或 `none`、`minimal`、`low`、`medium`、`high`、`xhigh`、`max`。服务端在发送前按当前能力再次校验，能力已过期或值不受支持时返回 `422`，不向 Provider 发送近似值。

流式接口事件顺序由下列固定事件组成：`accepted`、`user_message`、`status`、`tool_call_started`、`tool_call_finished`、`delta`、`completed`、`error`、`cancelled`。客户端必须先收到 `accepted`，终态必须是最后一个已知事件；违反该顺序或截断时保留部分输出并进入可重试失败态。服务端保存最近 20 条历史；首条用户消息会自动生成最多 32 字的会话标题。

配额调整工具会先返回待确认卡片；用户确认后，卡片必须基于确认接口的实际结果显示“配额调整成功”或可读失败原因，不得只结束等待状态。确认、失败或取消后的安全终态会随所属会话历史恢复，因此刷新页面不会丢失扩容结果。配额值的默认规则见[配额](../../storage/quota/overview.md)。

工具轮次达到 `ai.chat_tool_max_iterations` 后不会直接把已有数据丢弃为服务故障：当前回合禁止再调用工具并总结已获得信息，助手消息标记为 `degraded`，附带“继续查询”操作。工具参数不是 JSON 对象时，系统最多两次要求模型按工具契约修复；工具请求失败时会把经脱敏的可行动原因反馈给模型：参数错误可据此调整，服务端 5xx 会明确提示参数已通过校验、不能靠调整参数修复。连续三次失败则降级为基于已有结果的回答并附带“重新查询”操作。原始非法参数不会展示或持久化。相同工具与相同参数在同一回合已成功时，服务端复用该结果而不再次请求业务接口，工具轨迹标为“复用已获取结果”，并在下一次 Provider 调用禁用工具以强制基于已有结果作答。只有用户点击恢复操作才会开始新的受限查询回合。`request_timeout_seconds`、`chat_tool_max_iterations` 和 `chat_rate_limit_per_minute` 都属于 AI 对话配置，不与事件审计配置共用。

## 6. 动态工具与系统管理工具

常规 AI 工具必须是 FastAPI `GET` 路由且显式声明 `openapi_extra.ai_exposed=true`；它们对所有登录用户保持只读。

统一审计的 `GET /v1/audit-events` 与 `GET /v1/audit-events/{event_id}` 分别以 `list_audit_events`、`get_audit_event` 注册为常规只读工具，不标记为系统管理工具。它们继续走原 API 的项目隔离：超级管理员可查全局，项目管理员只能读取已授权项目范围。审计工具的描述自身要求范围检索、事件下钻和事实/数据缺口区分；只有本回合实际调用任一审计工具后，后续 Provider 轮次才会追加不可覆盖的审计研判约束：优先使用 `operation_id`/Trace/Request 标识配对尝试与结果，并以“研判依据、排查建议、解决方案、限制与数据缺口”四个标题回答。仅注册审计工具不会改变普通对话的系统提示或输出限制；自定义模型系统提示不能移除已激活的审计约束。

系统管理工具必须额外声明 `openapi_extra.ai_system_management=true`，并且当前用户命中 `backend/config.yml` 的 `super_admin_usernames`。只有超级管理员可见这组 `GET`、`POST`、`PUT`、`PATCH`、`DELETE` 工具；普通用户不会从工具定义中获知它们。

当前系统管理范围包括存储集群、容量池、存储空间、项目组标签、用户和 AI 模型配置的非删除已授权操作，以及存储设置的只读查询。项目组和用户目录各有一条“调整限额”工具，只向超级管理员开放；它们复用既有配额调整 API。大文件、离职备份记录、所有删除工具、创建用户、创建容量池、创建/更新存储空间、Qtree（NetApp）写工具、存储设置更新和 AI 审计查询保持关闭。

AI 工具返回在写入 Provider 上下文前按路由黑名单递归过滤。用户目录工具不返回用户对象、用户 ID、目录路径或嵌套项目组负责人与通知关联信息；审计工具不返回操作者、资源展示对象或可包含用户字段的变更摘要；告警、Incident、存储配置、存储集群和 AI 模型配置分别移除其用户关联、目录、联系方式、内部连接信息、掩码密钥和系统提示字段。大文件和离职备份记录仍保留其原业务 API，但不设置 `ai_exposed`，因此不会注册到 AI 对话。

集群详情相关的 JSON 查询工具仅向超级管理员注册：实时容量趋势、容量池与存储分布、存储空间与 Qtree（NetApp）读查询、容量变化、严重级别、Top 延迟、重复故障、厂商系统事件及详情、容量耗尽风险、容量预测、性能异常、故障分析事件和确定性 Incident 诊断。普通登录用户不会获得这些工具定义；即使复用先前为超级管理员生成的注册表，执行期仍拒绝。原有页面和业务 API 的查询范围保持不变。存储空间性能监控继续使用仅超级管理员的 `GET /volumes/{volume_id}/monitoring/ai`，且只返回性能指标、容量趋势和项目绑定摘要，不返回目录路径。集群健康分析导出为二进制下载，不向 AI 注册。

工具参数由路由 Path/Query 参数和写请求的 Pydantic `body` 信封动态校验。执行阶段再次校验超级管理员身份，再携带当前用户 Bearer Token 通过内部 ASGI 调用原业务 API；因此旧注册表不能绕过权限。转发请求体时不包含 Pydantic 计算字段；删除接口的 `204 No Content` 视为成功空结果。

新增工具必须显式补充唯一的 `ai_name` 和清晰的 `ai_description`；不得按路由路径猜测权限，也不得开放文件或图片响应。

## 7. 管理 API

- `GET|POST /admin/ai-models`
- `POST /admin/ai-models/discover`
- `PATCH|DELETE /admin/ai-models/{id}`
- `POST /admin/ai-models/{id}/test`
- `POST /admin/ai-models/{id}/capabilities/refresh`
- `GET|PATCH /admin/ai-settings`
- `GET /admin/ai-audits`
- `GET /admin/ai-audits/{id}`
- `GET /admin/ai-audits/conversations/{conversation_id}`

超级管理员通过 `PATCH /admin/ai-settings` 设置全局默认聊天模型。默认模型必须启用且允许聊天；停用或删除当前默认模型会返回 `409`，必须先更换默认模型。创建模型、修改 Provider/Base URL/API Key/模型标识或连接测试成功时会刷新能力，也可以手动调用刷新接口。刷新失败不阻止保存配置，但该模型只能使用 `auto`。

模型标识可以留空。手工填写时直接作为该配置的默认模型标识；留空时服务端通过 `POST /admin/ai-models/discover` 获取 Provider 模型列表，并使用返回的第一个可用标识创建或更新配置。发现接口只向超级管理员开放，返回去重、限量后的 `models` 和 `default_model`，不回显 API Key 或 Provider 原始元数据。

前端入口为 `/admin/ai-center?tab=models|audit`，隐藏审计详情路由为 `/admin/ai-center/audits/:id`。

## 8. 部署边界

部署必须提供独立 AI 加密密钥、可用 Redis 和当前数据库迁移。超级管理员通过 AI 中心配置模型并执行真实连接测试；普通用户的流式对话需在部署环境冒烟。不得提交真实 API Key、AI 加密密钥或生产 Provider 地址。

本期不提供截图中的独立“速度”控制，也不提供管理员默认推理档位；默认推理行为固定为 `auto`。
