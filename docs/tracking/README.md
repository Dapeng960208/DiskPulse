# 开发跟踪索引

跟踪记录按“会话记录 + 错误分类事实库”管理，不再使用平铺的 `current-release.md` 或 `error-log.md`。

```text
docs/tracking/
├── sessions/<session-id>/
│   ├── delivery.md                 # 本次交付、阻塞、验证和风险
│   └── errors.md                   # 本会话出现的错误及分类事实文档链接
└── errors/
    ├── error-index.md              # 自动维护的错误标题、链接、出现次数总表
    └── <category>/<error-slug>.md  # 同类错误的唯一事实来源
```

## 会话记录

每次开发任务开始时，创建 `docs/tracking/sessions/<YYYY-MM-DD>-<task-slug>/`。目录必须包含：

- `delivery.md`：会话范围、进度或阻塞、已完成项、验证、未验证范围和风险。
- `errors.md`：本会话实际出现且具有复用价值的错误。没有符合条件的错误时，明确写“无”。

交付状态只能写当前会话；历史状态保留在各自会话目录，不复制到新会话。

## 错误分类与自动统计

出现可复现错误时，AI 必须按以下顺序处理：

1. 在[错误总表](./errors/error-index.md)和对应分类目录中查找相同根因或相同处理方式的错误。
2. 同类错误存在时，在该错误事实文档的“备注”中追加本次会话、差异和出现记录；将出现次数加一。
3. 同类错误不存在时，在 `errors/<category>/<error-slug>.md` 新建事实文档，字段固定为“标题、错误内容、解决方案、备注”，首次出现次数为一。
4. 更新本会话 `errors.md`，只链接分类事实文档，不复制错误内容。
5. 更新错误总表。表格按出现次数降序；次数相同时，最近一次出现的错误排在前面。

错误消息、环境或触发步骤可以不同；只要确认根因和处理方式属于同一类，就写入同一事实文档并计数。根因尚未确认时不得强行合并；先创建独立记录，确认后再合并并修正统计。

瞬时拼写误输入、预期的 TDD 红灯或没有复用价值的单次失败不进入错误分类库。

## 入口

| 内容 | 入口 |
| --- | --- |
| 错误分类与出现次数 | [错误总表](./errors/error-index.md) |
| 已迁移的文档分类会话 | [交付记录](./sessions/2026-07-19-documentation-taxonomy/delivery.md) |
| 本次跟踪机制建设 | [交付记录](./sessions/2026-07-20-tracking-record-management/delivery.md) |
| 导航信息架构调整 | [交付记录](./sessions/2026-07-20-navigation-information-architecture/delivery.md) |
