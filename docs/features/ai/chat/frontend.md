# AI 前端实现细节

## 1. 模块职责

| 模块 | 职责 |
| --- | --- |
| `src/api/ai-api.js` | AI CRUD 请求、原生 Fetch SSE 请求和分块解析。 |
| `src/pages/ai/AiChatPage.vue` | 会话列表、模型选择、流式消息、停止、失败恢复和工具状态。 |
| `src/services/ai-markdown.js` | Markdown 渲染、链接协议限制和 HTML 净化。 |
| `src/pages/admin/ai/AiCenterPage.vue` | 超级管理员模型配置、连接测试和审计分页筛选。 |
| `src/pages/admin/ai/AiAuditDetailPage.vue` | 隐藏路由中的单次审计详情。 |
| `src/router/routes.js` | 根菜单“AI 助手”、AI 中心权限和隐藏详情路由。 |

## 2. SSE 请求与分块解析

普通 CRUD 继续复用项目 Axios 请求封装；流式消息使用原生 `fetch`，因为浏览器端需要直接读取 `ReadableStream`。请求显式携带当前 Bearer Token、JSON 请求体和 `Accept: text/event-stream`。

网络分块不保证与 SSE 事件边界对齐，因此解析器维护跨分块 `buffer`：

1. `TextDecoder` 以流模式解码当前字节块。
2. 按空行切分完整 SSE block，最后一个不完整 block 留到下一次读取。
3. 每个 block 提取 `event:` 和允许多行的 `data:`。
4. 已知事件的 `data` 必须为符合事件最小契约的 JSON 对象；非法载荷立即作为协议错误处理，不把字符串传给页面状态。
5. 流结束后再处理 buffer 中剩余的最后一个事件，并确认先收到 `accepted`、再收到 `completed`、`error`、`cancelled` 之一；终态前缺失确认、终态后出现任一已知事件或缺失终态时，均抛出可重试的协议错误。

非 `2xx` 响应优先读取后端 `detail` 或 `message`；非 JSON 响应回退为包含 HTTP 状态码的错误。

## 3. 会话与消息状态

发送前会固定本次 `requestConversationId`。所有 SSE 事件进入页面状态前都验证它仍等于当前会话 ID，因此用户切换会话后，旧请求的迟到分片不会污染新会话。

| 事件 | 页面行为 |
| --- | --- |
| `user_message` | 加入服务端已保存的用户消息，并同步自动生成的会话标题。 |
| `delta` | 创建或复用带 `streaming` 标记的临时助手消息，追加文本。 |
| `status` | 更新“正在连接/正在分析”提示。 |
| `tool_call_started` | 增加运行中的工具状态项。 |
| `tool_call_finished` | 按 `call_id` 更新对应工具项；`reused` 显示为“复用已获取结果”，表示本次没有再次请求业务接口。 |
| `completed` | 用服务端正式消息替换临时消息，并同步会话时间和标题；`status=degraded` 时保留工具轨迹和恢复元数据。 |
| `error` | 抛给发送流程，保留原输入并标记临时消息失败。 |

停止生成由当前请求的 `AbortController` 完成。`AbortError` 不弹出失败提示；其他错误（包括 SSE 截断、终态顺序和已知事件载荷错误）保留已有文本/工具轨迹、把原输入写入 `failedContent` 并清理 `streaming` 状态，用户点击“重试”后重新发送。降级消息下方显示“继续查询”或“重新查询”：工具轮次上限使用前者，参数或连续工具请求失败使用后者；点击后会先产生可见的用户授权消息，再开启一个遵循既有限流和工具上限的新回合。

额度调整确认卡在“确认执行”完成后保留可见反馈：确认接口返回 `ok=true` 显示成功，返回失败结果则显示后端的可读错误；取消显示已取消，不得把用户主动取消标记为生成失败。重新打开或刷新会话时，页面将历史中的终态确认记录标准化为同一反馈并禁用操作按钮。

## 4. 聊天工作区布局

- 对话历史栏和右侧聊天面板共享受限工作区高度；会话列表与消息列表各自滚动，长历史不得撑开应用壳的内容滚动区。
- 右侧聊天面板按“标题、可滚动消息、输入区”纵向排列。输入区不参与消息滚动，始终位于该工作区底部。
- 应用壳传递给路由页面的 flex 容器必须允许收缩（`min-height: 0`），否则长消息会使外层滚动并带走输入区。
- 输入框使用明确可见的边框；模型选择器置于输入框右下角的发送操作旁，快捷键提示位于左下角。

## 5. Markdown 与 XSS 边界

助手消息允许 Markdown，用户消息始终使用 Vue 文本插值。助手渲染采用三层约束：

1. `markdown-it` 关闭原始 HTML。
2. 渲染前移除 `javascript:`、`vbscript:`、`data:` 等危险协议，链接渲染器只允许 HTTP、HTTPS、邮件和站内绝对路径。
3. 最终 HTML 再经 DOMPurify 净化；新窗口链接强制添加 `noopener noreferrer`。

不要在页面中绕过 `renderAiMarkdown` 直接把模型输出传给 `v-html`。若以后允许更多标签或协议，必须同步增加 XSS 回归测试。

## 6. 路由与权限

- `/ai/chat` 是登录后的根菜单，对所有登录用户可见。
- `/admin/ai-center?tab=models|audit` 复用现有超级管理员路由元数据和后端 `403` 校验。
- `/admin/ai-center/audits/:id` 作为隐藏详情路由，不出现在菜单中，但执行相同超级管理员校验。
- 前端菜单隐藏只改善交互，不能替代后端授权。

## 7. 管理页面交互

- 模型表单支持 `openai`、`openrouter`、`ollama`、`claude`；编辑时 API Key 留空表示保留原密钥。
- “连接测试”调用真实后端测试接口，并展示 Provider 返回结果，不在浏览器中直接访问模型服务。
- 模型和审计列表统一使用共享 `DataTable`；审计状态筛选复用 `QueryForm`，查询、重置或切换每页数量后按服务端分页重新加载。
- 审计详情通过列表右侧固定的“查看”操作进入隐藏详情路由，不依赖整行点击。
- 审计页按状态、Provider、用户和时间分页筛选；列表不展示原始消息或工具参数。
- 审计详情按审计 ID 独立加载，页面刷新后仍可恢复。

## 8. 扩展边界

新增 SSE 事件时，应同时更新 `parseSseBlock` 的契约测试、事件最小载荷校验、`applyEvent` 状态映射和本专题文档。新增 Markdown 能力时先确认 DOMPurify 允许范围，不直接开启 `markdown-it` 的原始 HTML。

- 前端验证入口见[前端测试指南](../../../guides/frontend/testing.md)。部署环境仍需在登录浏览器验证断流、会话切换、超级管理员菜单和真实长响应滚动体验。
