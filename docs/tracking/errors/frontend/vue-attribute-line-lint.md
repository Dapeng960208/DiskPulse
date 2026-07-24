# Vue 模板属性未按仓库 ESLint 换行规则书写

## 错误内容

`vue/max-attributes-per-line` 或 `vue/first-attribute-linebreak` 拒绝事件中心 AI 设置模板中未按仓库规则换行的组件属性。

## 解决方案

将每个额外属性换到独立行，保留组件现有的模板格式；提交前执行 `pnpm lint`。

## 备注

- 出现次数：3
- 2026-07-23，`2026-07-23-incident-ai-agent`：新增 AI 设置对话框时出现；已按属性换行修复，`pnpm lint` 通过。
- 2026-07-24，`2026-07-24-unified-time-range-picker`：`IncidentAiSettingsDialog.vue:28` 仍触发 `vue/first-attribute-linebreak`；该文件不属于本次范围选择器改动，未跨范围修改。
- 2026-07-24，`2026-07-24-merge-duplicate-routes`：全量 `pnpm run lint` 仍在 `IncidentAiSettingsDialog.vue:28` 触发 `vue/first-attribute-linebreak`；该文件不属于本次路由合并范围，未跨范围修改。
