# Vue 模板属性未按仓库 ESLint 换行规则书写

## 错误内容

`vue/max-attributes-per-line` 拒绝同一行中含多个 `ElOption` 或 `TableActionButton` 属性的事件中心 AI 设置模板。

## 解决方案

将每个额外属性换到独立行，保留组件现有的模板格式；提交前执行 `pnpm lint`。

## 备注

- 出现次数：1
- 2026-07-23，`2026-07-23-incident-ai-agent`：新增 AI 设置对话框时出现；已按属性换行修复，`pnpm lint` 通过。
