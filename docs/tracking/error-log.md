# 错误记录

### 2026-06-30：规范引用文件与当前仓库结构不一致
- 触发：按 `AGENTS.md` 和项目标准读取必读文档、前端样式入口。
- 现象：`docs/standards/domain-terminology.md` 不存在；`frontend/src/style.css` 不存在。
- 根因：规范引用仍指向旧文件，当前仓库实际样式入口为 `frontend/src/styles/style.scss`。
- 修复：本次认证交付先按现有实际文件执行，并在认证文档与交付记录中避免引用不存在入口。
- 验证：已确认 `docs/standards/` 下无 `domain-terminology.md`，前端实际入口由 `frontend/src/main.js` 引入 `frontend/src/styles/style.scss`。
- 风险：后续任务仍可能按旧规范路径寻找文件，需要补齐或修订标准文档。
