# AI 后端实现细节

## 1. 模块职责

| 模块 | 职责 |
| --- | --- |
| `models.py` 与当前数据库迁移 | 模型配置、会话、消息和审计四类持久化对象。 |
| `schemas/aiSchema.py` | 用户会话、管理配置和审计查询的输入输出约束。 |
| `crud/aiCrud.py` | AI 表的最小查询与写入封装。 |
| `services/ai_security.py` | API Key 加密、解密和掩码。 |
| `services/ai_rate_limit.py` | Redis DB 7 固定分钟窗口限流。 |
| `services/ai_client.py` | OpenAI 兼容接口与 Claude 接口的请求、流式响应和工具调用归一化。 |
| `services/ai_tool_service.py` | 从 FastAPI 路由生成常规只读工具和受角色保护的系统管理工具，并以当前用户身份执行。 |
| `services/ai_chat_service.py` | 会话隔离、消息持久化、Provider 调用、工具循环和审计状态机。 |
| `routers/ai.py`、`routers/ai_admin.py` | 登录用户对话 API、SSE 输出和超级管理员 API。 |

## 2. 流式对话主链路

`POST /storage-pulse/api/ai/conversations/{id}/messages/stream` 按以下顺序执行：

1. JWT 依赖解析当前用户，Redis 以 `user_id` 执行固定窗口限流。
2. 使用 `conversation_id + user_id` 查询会话。查不到一律返回 `404`，不向调用方暴露其他用户是否拥有该会话。
3. 校验会话绑定模型仍处于启用且允许对话状态。
4. 保存用户消息、首条消息标题和 `running` 审计，再开始输出 SSE。这样即使 Provider 失败或客户端断开，用户输入和审计仍可恢复。
5. 按消息 ID 倒序取最近 20 条，再反转为时间正序发送给 Provider。
6. 从当前 FastAPI 应用路由构建工具注册表，并转换为当前 Provider 的工具格式。
7. 流式读取模型输出；普通文本产生 `delta`，工具请求进入最多 4 轮的执行循环。工具参数若不是 JSON 对象，则在服务端保留工具名和错误类别，不保留原始参数。
8. 工具通过内部 ASGI 请求调用原业务 API，并把结果按 Provider 协议追加到上下文；同一回合内同名同参数的成功结果由服务端复用，不再请求业务接口，轨迹状态为 `reused`，下一次 Provider 调用的工具列表会被置空以强制总结已有结果。系统管理写请求仅对超级管理员可用。
9. 工具参数格式错误会最多反馈给模型两次后重试；工具请求失败时会要求模型保留已成功结果、修改参数后重试。连续三次工具请求失败、达到工具轮次上限或参数修复耗尽时，额外发起一次禁用工具的总结调用；总结只能使用当前已获得的工具结果。
10. 正常完成保存 `succeeded`；工具上限、参数修复耗尽、连续工具请求失败或无工具总结失败保存 `degraded` 并发送 `completed`。真实 Provider/传输失败才保存 `failed`；生成器关闭或任务取消保存 `cancelled`。

同步接口复用同一生成器，只消费到 `completed`；因此同步与 SSE 的模型、工具和审计行为一致。

## 3. SSE 事件与持久化边界

| 事件 | 关键数据 | 服务端状态 |
| --- | --- | --- |
| `accepted` | `conversation_id`、`audit_id`、`trace_id` | 用户消息和运行中审计已提交。 |
| `user_message` | 完整用户消息、更新后的会话 | 前端可安全加入消息列表并更新自动标题。 |
| `status` | `thinking` | 仅表示当前生成状态，不落库。 |
| `tool_call_started` | 工具名、轮次、序号 | 审计中的工具调用计数已增加。 |
| `tool_call_finished` | 工具名、轮次、成功、复用或失败、脱敏限长的展示结果 | 工具轨迹已提交；`reused` 表示未重复请求业务接口；非法参数只返回安全错误类别和空参数对象。 |
| `delta` | 文本分片 | 分片不逐条落库，避免高频写入。 |
| `completed` | 完整助手消息、会话、审计 ID、可选 `recovery` | `succeeded` 或 `degraded` 已提交；`recovery` 表示需由用户授权继续/重新查询。 |
| `error` | 可展示错误 | 仅真实不可恢复故障使用；审计已标记 `failed`，不回显内部异常或原始工具参数。 |
| `cancelled` | 会话 ID、审计 ID | 异步取消时审计已标记取消。客户端断开时连接可能无法再接收该事件。 |

## 4. Provider 适配

- `openai`、`openrouter`、`ollama` 共用 OpenAI Chat Completions 协议；`claude` 使用 Messages API。
- Provider 客户端把文本和工具调用统一为 `AICompletionStreamEvent`，对话服务不解析厂商原始响应。
- OpenAI 兼容 Provider 可能发送 `choices: []` 的用量或状态帧；该帧不含增量或工具调用，客户端会忽略并继续读取后续有效帧。
- OpenAI 工具名称和 JSON 参数可能分多个 delta 到达，按工具索引拼接后再校验 JSON。
- Claude 的 `tool_use` 和 `input_json_delta` 分开到达；缺失的 `input` 才兼容为空对象，显式空字符串、数组、`null` 或其他非对象均保留为参数错误，避免误执行为 `{}`。
- 非 JSON 或非对象参数抛出带工具 ID、工具名和错误类别的内部异常；编排层只将安全的格式提示回送给模型，最多重试两次，不将原始参数写入 SSE 或审计。
- 工具结果按厂商要求回填：OpenAI 使用 `assistant.tool_calls + tool`，Claude 使用 `assistant.tool_use + user.tool_result`。
- 管理端连接测试真实发送最小消息，不把 URL、密钥格式校验当作连接成功。

## 5. 动态工具与系统管理权限

常规工具仍以业务路由为唯一参数契约：只有 `GET` 且显式设置 `openapi_extra.ai_exposed=true` 的路由才对登录用户注册。Path 和 Query 参数直接生成 Pydantic 模型，并使用 `extra="forbid"` 拒绝模型擅自增加的参数。

系统管理工具必须同时声明 `ai_exposed=true` 和 `ai_system_management=true`。只有 `is_super_admin(current_user)` 为真时才会注册，允许的方法限定为 `GET`、`POST`、`PUT`、`PATCH`、`DELETE`；不会按 `/admin` 或其他路径名称自动推断权限。

当前系统管理工具包括存储集群、容量池、存储空间、项目组标签、用户和 AI 模型配置的非删除已授权操作，以及存储设置和离职备份记录的只读查询。项目组与用户目录的限额调整工具仅对超级管理员注册，继续复用原有配额 PATCH 路由、请求校验、设备写入和通知逻辑。全部删除工具、创建用户、创建容量池、创建/更新存储空间、全部 Qtree（NetApp）工具、存储设置更新及 AI 审计查询均不注册。

`GET /v1/anomalies` 和 `GET /v1/incidents` 分别以 `list_performance_anomalies`、`list_incidents` 注册给所有登录用户，原路由继续按当前用户可见项目过滤；`get_incident_diagnosis` 用于读取已定位事件的确定性诊断。`GET /volumes/{volume_id}/monitoring/ai` 仅作为超级管理员工具 `get_volume_performance_monitoring` 注册，并将原监控结果投影为性能指标、容量趋势、存储空间标识和项目绑定摘要，排除 `linux_path`。

执行阶段再次以当前认证用户调用 `is_super_admin`，即使旧注册表被复用也会拒绝普通用户。内部 ASGI 请求使用当前用户 ID 签发的 Bearer Token，继续经过原 API 的认证、权限和数据范围逻辑。写请求的 JSON 内容必须放在受 Pydantic 校验的 `body` 信封内；转发时排除 Pydantic 计算字段，避免其被原路由的 `extra="forbid"` 校验拒绝。

业务响应会做有限归一化：

- `{content, total, ...}` 转为 `{items, total, ...}`；
- `{data: [...], meta: {...}}` 转为 `{items, ...meta}`；
- 其他 `{data: value}` 返回 `value`，普通 JSON 原样返回；
- `204 No Content` 的成功删除返回 `{ok: true, data: null}`，不误报为非 JSON 错误。

## 6. 安全、限流与审计

- API Key 使用 `ai.config_secret_key` 经 SHA-256 派生 Fernet 密钥后加密；`fernet::` 前缀用于识别当前密文格式。配置密钥必须独立且不得使用占位值。
- 管理响应只包含密钥掩码和是否已配置；空更新不会覆盖已有密钥。
- 审计请求只保存 `[REDACTED]` 和长度；响应保存消息 ID、长度、最终状态及可选恢复操作。工具展示明细和管理写请求的 `body` 按敏感字段脱敏并限长，非法原始参数不保存。
- 限流键为 `diskpulse:ai:rate:{user_id}:{UTC分钟}`。首次计数设置 60 秒过期；超限返回 `429 + Retry-After`。
- Redis 是聊天入口的安全依赖，连接或命令失败时采用关闭式失败并返回 `503`，不绕过限流。
- 工具循环受 `ai.max_tool_iterations` 限制，避免模型递归调用工具造成不可控资源消耗。
- 每个对话回合按“工具名 + 规范化参数”缓存成功结果；失败结果不缓存，允许模型在安全提示下修改参数后重试，连续三次失败才进入受控降级。
- 到达上限后不会自动开启新查询回合：当前回合先禁用工具总结，助手消息以 `degraded` 保存 `recovery`；只有用户在页面点击恢复操作才会发送新的受限回合。

## 7. 事务与失败恢复

- SSE 开始前提交用户消息和运行中审计，后续失败不会丢失用户提问。
- `failed` 审计和 SSE `error` 只保留安全的用户提示；服务端同时以 `trace_id`、审计 ID、会话 ID、用户 ID 和异常类型记录完整异常栈，便于排障且不向客户端或审计载荷回显内部错误、提问或凭据。
- 最终文本只在完整生成后一次性保存；半截 `delta` 不进入历史上下文。
- 历史助手消息按审计中的可见性范围重新校验：普通用户缺少可验证范围的旧记录保持隐藏。会话已经按 `user_id` 隔离，因此配置的超级管理员可以读取自己会话中缺少范围标记的旧记录，不能据此读取其他用户的会话。
- 异常处理中先 `rollback` 清理 SQLAlchemy 会话，再重新加载审计记录并提交失败状态。
- `degraded` 的恢复信息写在既有审计 `response_payload` 中；会话重载时由助手消息序列化恢复，因而不需要数据库迁移。
- 客户端主动关闭同步生成器触发 `GeneratorExit`；异步任务取消触发 `CancelledError`。两者均记录取消审计。
- 前端重试会作为一条新用户消息再次发送，不修改或覆盖原消息。

## 8. 验证边界

AI 回归应覆盖轮次上限降级、无工具总结、参数校验修复、失败调用改参重试、同参成功结果复用、性能/事件工具的注册权限、系统管理工具的双层鉴权、写请求 `body` 转发与空响应处理。部署环境仍需验证真实 Provider、Redis、数据库迁移和不同权限用户的完整 SSE 对话。

## 9. Incident 诊断工具约束

`GET /storage-pulse/api/v1/incidents/{id}/diagnosis` 是显式注册的只读工具。内部 ASGI 调用继续携带当前用户 Bearer Token，因此诊断、候选、证据 ID 和数据缺口仍受项目作用域校验；工具不会返回原始厂商载荷、路径、作业环境、日志或设备凭据。

模型在调用该工具后只能回传确定性 JSON 字段 `incident_id`、`confidence`、`candidates`、`evidence_ids`、`data_gaps`。服务端逐项比较候选、分数、证据 ID、数据缺口和置信度，并从确定性结果重新生成用户可见文本。任何未知引用、字段缺失、分数/置信度变化、额外事实或非 JSON 文本都会被拒绝并回退至确定性模板；模型不能增加证据或提高置信度。
