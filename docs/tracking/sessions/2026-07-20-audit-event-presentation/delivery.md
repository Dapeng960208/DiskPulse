# 统一审计展示交付记录

## 范围

修复统一操作审计的 ISO 时间显示，明确人工接口请求人或系统任务触发方，并将已有执行上下文和采集摘要以可读字段展示。

## 已完成

- 审计列表和详情统一使用本地可读的秒级时间。
- 人工接口触发的审计显示关联用户；没有人工用户的定时采集明确显示为“系统定时任务”。
- 审计详情显示操作、记录阶段、执行来源、请求/Trace 关联与已记录原因码；存储采集摘要显示更新的用户目录和项目组数量。
- 不再固定渲染未采集字段，避免把空 IP、请求地址或资源路径展示为无意义的 `-`。

## 验证

- 前端 Vitest：`pnpm exec vitest run test/unit/audit-event-presentation.test.js test/unit/audit-event-table-associations.test.js test/unit/incident-and-audit-list-layout.test.js test/unit/mock-runtime.test.js --coverage.enabled=false`（4 个文件、32 项通过）。
- 前端 ESLint：审计展示工具、列表、详情页、抽屉和 Mock 运行时均通过。
- 前端测试构建：`pnpm run build:test` 通过；仅保留仓库既有的标题环境变量与大包体积警告。
- 隔离 Mock 浏览器验收：在 `/admin/audit-events` 打开“系统定时任务”的存储采集记录，确认列表、详情抽屉、关联项目、请求/追踪 ID 与采集结果均正常渲染。

## 未验证范围与风险

- 未连接真实后端或生产审计数据验证；历史记录缺少请求人和来源类型时会如实显示“未记录”。
- 时间使用浏览器本地时区格式化，跨时区用户会按其本地时间看到事件。
