# Main 分支代码审查问题修复

- 会话：`2026-07-24-code-review-fixes`
- 状态：进行中
- 范围：修复相较 `origin/main` 的代码审查问题，并为每项修复补充回归测试、约束注释和独立提交。

## 假设与成功标准

- 保持现有 API、事件关联、AI 调用和时间选择器的公开行为兼容。
- 每项修复先验证回归测试失败，再实现最小修复并验证通过。
- 每项修复独立提交到 `main`，不混入无关重构。

## 已完成

- 恢复备份记录和大文件生产 API 路由，并增加真实 `main.app` 路由契约测试。
- 为滚动事件关联状态迁移回填每个关联键的最新历史 Incident，并覆盖同时间证据按 ID 稳定决胜。
- 为 Claude Code SDK 输出队列应用统一请求超时，超时后取消客户端并释放流式工作线程。
- 阻止窗口外迟到证据覆盖前向关联游标，保留历史事件的同时确保后续实时证据继续归入最新事件。

## 验证

- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_main_route_contract.py test/test_core_api.py test/test_project_scope_authorization.py -q`
  - 结果：36 passed。
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_forecast_incident_center.py test/test_backend_schema_contract.py -q`
  - 结果：56 passed。
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_claude_code_adapter.py test/test_ai_reasoning_effort_red.py test/test_ai_platform.py -q`
  - 结果：162 passed，存在 1 条待后续修复的取消协程未等待警告。
- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_forecast_incident_center.py -q`
  - 结果：48 passed。

## 未验证范围与风险

- 其余审查问题仍在修复中。
- 尚未运行本会话全部聚焦测试的汇总验证。
