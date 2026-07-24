# AI 后端实现细节

## 1. 模块职责

| 模块 | 职责 |
| --- | --- |
| `models.py` 与当前数据库迁移 | 模型配置、平台设置、会话、消息、审计和会话名称别名持久化对象。 |
| `schemas/aiSchema.py` | 用户会话、管理配置和审计查询的输入输出约束。 |
| `crud/aiCrud.py` | AI 表的最小查询与写入封装。 |
| `crud/aiNameObfuscationCrud.py` | 在当前用户可见的项目与资源范围内收集可保护名称。 |
| `services/ai_security.py` | API Key 加密、解密和掩码。 |
| `services/ai_name_obfuscation_service.py` | 会话/保护代次别名生成、加密持久化、递归转换和跨流式分片还原。 |
| `services/ai_rate_limit.py` | Redis DB 7 固定分钟窗口限流。 |
| `services/ai_reasoning_service.py` | Provider 能力发现、官方能力目录、统一 `reasoning_control` 和请求参数映射。 |
| `services/ai_client.py` | OpenAI 兼容接口、Provider 原生接口与 Claude 接口的请求、流式响应和工具调用归一化。 |
| `services/ai_tool_service.py` | 从 FastAPI 路由生成常规只读工具和受角色保护的系统管理工具，并以当前用户身份执行。 |
| `services/ai_chat_service.py` | 会话隔离、消息持久化、Provider 调用、工具循环和审计状态机。 |
| `routers/ai.py`、`routers/ai_admin.py` | 登录用户对话 API、SSE 输出和超级管理员 API。 |
| `routers/audit_events.py` | 统一审计的两个只读 AI 工具；原有项目权限和序列化脱敏保持唯一事实来源。 |

## 2. 流式对话主链路

`POST /storage-pulse/api/ai/conversations/{id}/messages/stream` 按以下顺序执行：

1. JWT 依赖解析当前用户，Redis 以 `user_id` 执行固定窗口限流。
2. 使用 `conversation_id + user_id` 查询会话。查不到一律返回 `404`，不向调用方暴露其他用户是否拥有该会话。
3. 校验会话绑定模型仍处于启用且允许对话状态。
4. 按会话模型当前 `reasoning_control` 校验本条消息的 `reasoning`，保存用户消息、首条消息标题和 `running` 审计，再开始输出 SSE。这样即使 Provider 失败或客户端断开，用户输入、所选推理值和审计仍可恢复。
5. 读取全局名称混淆开关。启用时以当前用户的授权范围收集项目、用户、集群、项目组、标签、容量池、存储空间、Qtree 与主机名称，加载同一会话/保护代次的加密映射；首次启用或重新启用时把当前用户消息设为历史下限，未保护的旧消息不发送给 Provider。映射初始化、解密、资源加载或保存失败会在 Provider 调用前终止。
6. 按消息 ID 倒序取最近 20 条，再反转为时间正序发送给 Provider。启用保护时递归混淆系统提示、消息和后续工具结果；`children` 等嵌套对象中的名称会转换，数值指标不变。系统提示要求先拆分多事项请求；资源范围、时间范围、期望操作或完成标准不明确时，助手先提出简短澄清问题且不得调用工具或猜测补齐。目标明确后，助手先给出简短可验证的执行范围，再按必要步骤查询或执行。
7. 从当前 FastAPI 应用路由构建工具注册表，并转换为当前 Provider 的工具格式。审计工具在定义中携带范围检索、事件下钻和事实/数据缺口的专用说明；仅注册它们不会改变普通对话的系统提示。只有本回合实际调用 `list_audit_events` 或 `get_audit_event` 后，才在后续 Provider 轮次追加不可覆盖的审计研判约束：`operation_id`/Trace/Request 配对与四个固定回答标题。
8. 流式读取模型输出；普通文本产生 `delta`，工具请求进入由 `ai.chat_tool_max_iterations` 控制（默认 4）的执行循环。普通和降级总结流均缓冲可能跨分片的别名，确认可还原后再输出；无流式回退文本也会还原。工具参数若不是 JSON 对象，则在服务端保留工具名和错误类别，不保留原始参数。
9. 工具调用前还原模型参数，以当前用户身份通过内部 ASGI 请求调用原业务 API；原值工具结果用于 SSE、持久化与审计轨迹，递归混淆后的结果才按 Provider 协议追加到上下文。同一回合内同名同参数的成功结果由服务端复用，不再请求业务接口，轨迹状态为 `reused`，下一次 Provider 调用的工具列表会被置空以强制总结已有结果。系统管理写请求仅对超级管理员可用。审计工具同样通过当前用户 Bearer Token 执行，因此模型注册或旧会话不能扩大审计可见范围。
10. 工具参数格式错误会最多反馈给模型两次后重试；工具请求失败时会反馈经脱敏的原因：参数错误可据此修正，服务端 5xx 会明确标识为已通过参数校验、不能通过改参修复。连续三次工具请求失败、达到工具轮次上限或参数修复耗尽时，额外发起一次禁用工具的总结调用；总结只能使用当前已获得的工具结果。
11. 正常完成保存 `succeeded`；工具上限、参数修复耗尽、连续工具请求失败或无工具总结失败保存 `degraded` 并发送 `completed`。真实 Provider/传输失败才保存 `failed`；生成器关闭或任务取消保存 `cancelled`。

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

| Provider | 能力来源与原生请求语义 |
| --- | --- |
| `openai` | 保持 Chat Completions，按官方模型目录解析档位并发送 `reasoning_effort`；未知模型只允许 `auto`。 |
| `openrouter` | 从模型接口读取 `supported_efforts`、`default_effort` 和 `mandatory`，通过 `reasoning.effort` 发送。 |
| `ollama` | 使用原生 `/api/chat` 的 `think`；GPT-OSS 模型使用 `low/medium/high`，其他思考模型使用布尔开关。 |
| `claude` | 从 `/v1/models` 能力字段读取档位，通过 `output_config.effort` 发送；adaptive thinking 模型按要求省略不兼容的采样参数。 |
| `claude_code` | 使用 `claude-agent-sdk==0.2.123` 和模型专用 API Key，通过 SDK `effort` 发送。只挂载 DiskPulse 进程内 MCP 工具并设置 `tools=[]`，不提供文件、Shell、插件或其他外部 MCP 工具。 |
| `deepseek` | 按具体模型使用 `thinking` 开关或 `reasoning_effort`；工具回合保留 Provider 要求回传的当前请求状态。 |
| `dashscope` | 使用 DashScope OpenAI 兼容入口和原生 `enable_thinking` 开关，不把 `thinking_budget` 近似为强度。 |
| `volcengine` | 使用火山方舟 OpenAI 兼容入口和 `thinking.type` 开关。 |
| `zhipu` | 较早模型使用原生思考开关，官方声明支持档位的模型使用 `reasoning_effort`。 |
| `moonshot` | 按模型使用原生 `reasoning_effort` 或 `thinking`，并保留工具回合要求的当前请求状态。 |
| `minimax` | 支持其 OpenAI/Anthropic 兼容入口；官方未声明可调档位的模型返回 `none`。 |
| `qianfan` | 按官方模型目录选择 `thinking`、`enable_thinking` 或 `reasoning_effort`，单次请求不同时发送多种控制参数。 |
| `hunyuan` | 默认使用 TokenHub 入口；支持档位的模型使用 `low/medium/high`，其他思考模型使用原生开关。 |

所有适配器只发送模型声明支持的控制参数；开关或预算能力不映射为虚假强度。
- Provider 客户端把文本和工具调用统一为 `AICompletionStreamEvent`，对话服务不解析厂商原始响应。
- DeepSeek、Kimi 等要求在工具调用后回传推理状态的 Provider，只在当前 Provider 请求上下文中保留必要状态；返回的思维链不会进入 `ai_messages`、SSE 或审计。
- OpenAI 兼容 Provider 可能发送 `choices: []` 的用量或状态帧；该帧不含增量或工具调用，客户端会忽略并继续读取后续有效帧。
- OpenAI 工具名称和 JSON 参数可能分多个 delta 到达，按工具索引拼接后再校验 JSON。
- Claude 的 `tool_use` 和 `input_json_delta` 分开到达；缺失的 `input` 才兼容为空对象，显式空字符串、数组、`null` 或其他非对象均保留为参数错误，避免误执行为 `{}`。
- 非 JSON 或非对象参数抛出带工具 ID、工具名和错误类别的内部异常；编排层只将安全的格式提示回送给模型，最多重试两次，不将原始参数写入 SSE 或审计。
- 工具结果按厂商要求回填：OpenAI 使用 `assistant.tool_calls + tool`，Claude 使用 `assistant.tool_use + user.tool_result`。
- 管理端连接测试真实发送最小消息，不把 URL、密钥格式校验当作连接成功。

### 4.1 推理能力契约

对外模型能力统一为 `reasoning_control`：

| 字段 | 约束 |
| --- | --- |
| `kind` | `effort`、`toggle`、`none`。 |
| `options` | `auto` 加上模型原生支持的可选值；`auto` 表示不发送 Provider 推理控制参数。 |
| `provider_default` | Provider 声明的默认推理设置；未知时为 `null`。 |
| `mandatory` | Provider 是否要求模型始终推理。 |
| `source` | `provider`、`official_catalog`、`unknown`。 |
| `status` | 能力获取状态；失败状态只允许消息使用 `auto`。 |
| `updated_at` | 最近一次能力解析或刷新时间。 |

解析顺序固定为动态 Provider 元数据优先、内置官方能力目录其次、未知能力最后。管理员创建配置、修改 Provider/Base URL/API Key/模型标识、连接测试成功或主动刷新时更新缓存；刷新失败只保存脱敏错误，不阻止模型配置写入。

消息请求的 `reasoning` 默认为 `auto`，表示完全省略 Provider 推理参数。其他值必须属于当前 `options`；开关模型只接受 `on/off`，强度模型只接受 `none/minimal/low/medium/high/xhigh/max` 中模型声明的子集。无效值返回 `422`，不得静默降级。标题、摘要和连接测试等后台调用固定使用 `auto`。

### 4.2 默认聊天模型

`ai_platform_settings` 是平台级单例设置，`default_chat_model_id` 可以为空。`POST /ai/conversations` 的 `model_id` 可选：显式值仍按既有启用和聊天权限校验，省略时读取默认聊天模型；未配置可用默认模型时返回明确配置错误。

`GET|PATCH /admin/ai-settings` 仅允许超级管理员读取和修改默认模型。默认模型必须同时满足 `enabled=true` 和 `enable_chat=true`；停用、取消聊天权限或删除当前默认模型返回 `409`，要求管理员先切换默认值。

### 4.3 自动发现模型列表

`AIModelCreate.model` 与 `AIModelPatch.model` 允许空字符串。手工提供非空标识时不会请求 Provider；空值仅在模型配置的创建或更新流程中触发自动发现，并采用 Provider 返回的第一个可用标识，数据库中不会持久化空模型标识。

`POST /admin/ai-models/discover` 只允许超级管理员调用，接收 Provider、Base URL 与临时 API Key，返回 `{models, default_model}`。API Key 只用于当前服务端请求：先在内存中加密以复用统一认证头构造，不写入数据库、响应或审计；客户端错误只返回通用中文提示。模型目录最多保留 200 个非空、长度不超过 200 的去重标识。

OpenAI 兼容 Provider 使用 `GET /models` 的 `data[].id`，Ollama 使用 `GET /api/tags` 的 `models[].name`，Anthropic 协议使用 `GET /v1/models`。Claude Code 没有可安全调用的模型目录接口，会返回受控的“不支持自动获取”错误。目录请求使用至多 10 秒超时；HTTP、超时和无效响应均不得回显上游地址、响应正文或密钥。

## 5. 动态工具与系统管理权限

常规工具仍以业务路由为唯一参数契约：只有 `GET` 且显式设置 `openapi_extra.ai_exposed=true` 的路由才对登录用户注册。路由自身及其 `Depends` 依赖链中的 Path、Query 参数都会生成 Pydantic 模型，并使用 `extra="forbid"` 拒绝模型擅自增加的参数；可选 Query 参数保留路由的默认行为。存储集群健康分析的 `start_time`、`end_time` 会明确暴露给模型，任一缺省时在服务端按请求时刻补足最近 24 小时范围。

系统管理工具必须同时声明 `ai_exposed=true` 和 `ai_system_management=true`。只有 `is_super_admin(current_user)` 为真时才会注册，允许的方法限定为 `GET`、`POST`、`PUT`、`PATCH`、`DELETE`；不会按 `/admin` 或其他路径名称自动推断权限。

当前系统管理工具包括存储集群、容量池、存储空间、项目组标签、用户和 AI 模型配置的非删除已授权操作，以及存储设置和离职备份记录的只读查询。项目组与用户目录的限额调整工具仅对超级管理员注册，继续复用原有配额 PATCH 路由、请求校验、设备写入和通知逻辑。全部删除工具、创建用户、创建容量池、创建/更新存储空间、Qtree（NetApp）写工具、存储设置更新及 AI 审计查询均不注册。

集群详情的 JSON 读工具一律标记 `ai_system_management=true`：`/storage-clusters/{storage_cluster_id}` 的实时趋势和健康分析（容量变化、严重级别、Top 延迟、重复故障、系统事件及详情）、容量池与存储树、存储空间实时趋势、Qtree（NetApp）列表/详情/实时趋势、`/v1/capacity-predictions/{asset_type}/{asset_id}/risk`、`/v1/forecasts`、`/v1/anomalies`、`/v1/incidents` 和确定性 Incident 诊断。它们只对超级管理员注册，并在执行期再次校验当前用户；底层路由继续执行既有认证、数据范围和参数校验。集群健康分析 `export` 保持未注册，因为工具执行只接受 JSON 响应。`GET /volumes/{volume_id}/monitoring/ai` 继续作为超级管理员工具 `get_volume_performance_monitoring`，并将原监控结果投影为性能指标、容量趋势、存储空间标识和项目绑定摘要，排除 `linux_path`。

执行阶段再次以当前认证用户调用 `is_super_admin`，即使旧注册表被复用也会拒绝普通用户。内部 ASGI 请求使用当前用户 ID 签发的 Bearer Token，继续经过原 API 的认证、权限和数据范围逻辑。写请求的 JSON 内容必须放在受 Pydantic 校验的 `body` 信封内；转发时排除 Pydantic 计算字段，避免其被原路由的 `extra="forbid"` 校验拒绝。

业务响应会做有限归一化：

- `{content, total, ...}` 转为 `{items, total, ...}`；
- `{data: [...], meta: {...}}` 转为 `{items, ...meta}`；
- 其他 `{data: value}` 返回 `value`，普通 JSON 原样返回；
- `204 No Content` 的成功删除返回 `{ok: true, data: null}`，不误报为非 JSON 错误。

## 6. 安全、限流与审计

- API Key 使用 `ai.config_secret_key` 经 SHA-256 派生 Fernet 密钥后加密；`fernet::` 前缀用于识别当前密文格式。配置密钥必须独立且不得使用占位值。
- 名称别名使用同一密钥加密原值，唯一范围是会话、保护代次和别名。别名使用“类别-随机大写字母数字”形式，不含真实名称或内部 ID；同名跨类别时回退为“资源”类别。映射跨进程重启、资源改名或删除后仍可用于还原。
- `name_obfuscation_enabled` 默认开启。关闭只让后续消息按既有行为发送；从关闭改为开启递增保护代次，新代次从当前用户消息开始，旧的未保护历史被排除。Provider 绝不接收原始受管名称；保护链路无法安全完成时不调用 Provider。
- 管理响应只包含密钥掩码和是否已配置；空更新不会覆盖已有密钥。
- 审计请求只保存 `[REDACTED]`、长度、用户选择的 `reasoning`、解析后的控制类型和实际发送值；响应保存消息 ID、长度、最终状态及可选恢复操作。Provider 返回的思维链不保存、不展示。工具展示明细和管理写请求的 `body` 按敏感字段脱敏并限长，非法原始参数不保存；工具失败仅展示白名单中的可读原因（如缺少开始/结束时间，以及提示参数无法修复的服务端 5xx），不展示异常文本、堆栈或凭据。
- 限流键为 `diskpulse:ai:rate:{user_id}:{UTC分钟}`。首次计数设置 60 秒过期；超限返回 `429 + Retry-After`。
- Redis 是聊天入口的安全依赖，连接或命令失败时采用关闭式失败并返回 `503`，不绕过限流。
- 工具循环受 `ai.chat_tool_max_iterations` 限制，避免模型递归调用工具造成不可控资源消耗；该配置仅用于 AI 对话，和事件审计无关。
- 每个对话回合按“工具名 + 规范化参数”缓存成功结果；失败结果不缓存，允许模型在安全提示下修改参数后重试，连续三次失败才进入受控降级。
- 到达上限后不会自动开启新查询回合：当前回合先禁用工具总结，助手消息以 `degraded` 保存 `recovery`；只有用户在页面点击恢复操作才会发送新的受限回合。

## 7. 事务与失败恢复

- SSE 开始前提交用户消息和运行中审计，后续失败不会丢失用户提问。
- `failed` 审计和 SSE `error` 只保留安全的用户提示；服务端同时以 `trace_id`、审计 ID、会话 ID、用户 ID 和异常类型记录完整异常栈，便于排障且不向客户端或审计载荷回显内部错误、提问或凭据。
- 最终文本只在完整生成后一次性保存；半截 `delta` 不进入历史上下文。
- 流式别名还原只释放已确认不会构成别名的前缀；因此跨 `delta` 分片不会向用户短暂暴露别名或半截别名。
- 历史助手消息按审计中的可见性范围重新校验：普通用户缺少可验证范围的旧记录保持隐藏。会话已经按 `user_id` 隔离，因此配置的超级管理员可以读取自己会话中缺少范围标记的旧记录，不能据此读取其他用户的会话。
- 异常处理中先 `rollback` 清理 SQLAlchemy 会话，再重新加载审计记录并提交失败状态。
- `degraded` 的恢复信息写在既有审计 `response_payload` 中；会话重载时由助手消息序列化恢复，因而不需要数据库迁移。
- 配额确认的确认、失败或取消结果追加到所属审计的工具轨迹中，并复用该轨迹的可见性标记；只保存白名单预览字段、决定、`ok` 和限长可读错误，历史序列化据此恢复终态卡片，不保存 Redis 绑定参数或设备完整返回。
- 客户端主动关闭同步生成器触发 `GeneratorExit`；异步任务取消触发 `CancelledError`。两者均记录取消审计。
- 前端重试会作为一条新用户消息再次发送，不修改或覆盖原消息。

## 8. 验证边界

AI 回归应覆盖各 Provider 的推理参数映射与采样参数剔除、动态能力与目录回退、能力刷新失败后仅允许 `auto`、默认模型设置和停用/删除保护、每消息推理校验、Claude Code 工具白名单及取消清理、DeepSeek/Kimi 工具回合状态、数据库迁移，以及既有轮次上限降级、无工具总结、参数校验修复、失败调用改参重试、同参成功结果复用、依赖链 Query 参数注册、健康分析最近 24 小时默认范围、安全失败原因、澄清后再调用工具、动态工具权限和空响应处理。部署环境仍需验证真实 Provider、Redis、数据库迁移和不同权限用户的完整 SSE 对话。

## 9. Incident 诊断工具约束

`GET /storage-pulse/api/v1/incidents/{id}/diagnosis` 是显式注册的只读工具。内部 ASGI 调用继续携带当前用户 Bearer Token，因此诊断、候选、证据 ID、数据缺口详情和厂商事件安全摘要仍受项目作用域校验。`data_gap_details` 把 `asset_mapping_missing` 转为“资产映射不完整”，明确它只表示节点/卷/Qtree/项目的稳定映射链路不完整；已有稳定节点身份的厂商事件不产生该缺口。该列表同时收录候选级缺口代码（如 `conflicting_evidence` 转为“证据相互冲突”），因此客户端可用同一份详情列表解释诊断级与候选级的全部缺口代码。`evidence_summaries` 只包含来源引用、事件代码、实例严重级别，以及已启用且已审核目录的关联类型、中文标签和标题。目录缺失、停用或待审核时只返回未分类回退，不向 AI 暴露候选语义。工具不会返回原始厂商载荷、路径、作业环境、完整日志、故障指纹或设备凭据。

模型在调用该工具后只能回传确定性 JSON 字段 `incident_id`、`confidence`、`candidates`、`evidence_ids`、`data_gaps`、`data_gap_details` 和 `evidence_summaries`。服务端逐项比较候选、分数、证据 ID、数据缺口、厂商事件语义和置信度，并从确定性结果重新生成用户可见文本。任何未知引用、字段缺失、分数/置信度变化、额外事实或非 JSON 文本都会被拒绝并回退至确定性模板；模型不能增加证据、猜测未分类代码或提高置信度。
