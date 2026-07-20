# 开发错误记录

将可复现、会影响后续开发或部署的错误按[开发跟踪索引](../../tracking/README.md)记录。每个会话在 `docs/tracking/sessions/<session-id>/errors.md` 保留链接；错误事实、解决方案和出现次数只保留在 `docs/tracking/errors/<category>/<error-slug>.md`。

每条错误事实文档固定包含：标题、错误内容、解决方案、备注。备注记录会话、差异、首次/最近出现和出现次数；同类错误每出现一次计数加一，并更新[错误总表](../../tracking/errors/error-index.md)。瞬时拼写误输入、预期 TDD 红灯或没有复用价值的单次失败不需要保留。
