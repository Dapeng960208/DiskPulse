# AI 工具展示式参数名触发严格校验失败

## 标题

AI Provider 使用展示式或缩写式参数名时，动态工具的严格输入模型在调用业务 API 前拒绝请求。

## 错误内容

`list_storage_usages` 的路由契约要求 `use_ratio_min` 与 `use_ratio_max`，但 Provider 本次调用传入 `use ratio min` 和 `use_max`。动态工具输入模型启用 `extra="forbid"`，将这两个键视为额外字段并返回“工具参数无效”，内部 ASGI 请求未到达存储查询接口。

## 解决方案

执行前仅将可唯一映射的展示式键归一为路由字段别名，并支持省略 `_ratio_` 的同名变体；无法匹配的 `null` 占位参数忽略。所有非空未知参数仍保留给 Pydantic 严格拒绝，值类型、范围、权限和原业务接口校验保持不变。

## 备注

- 首次与最近出现：2026-07-24，`2026-07-24-ai-tool-argument-normalization` 会话。
- 出现次数：1。
