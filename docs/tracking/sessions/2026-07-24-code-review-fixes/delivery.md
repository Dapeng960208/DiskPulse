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

## 验证

- `cd backend; ..\.venv\Scripts\python.exe -m pytest test/test_main_route_contract.py test/test_core_api.py test/test_project_scope_authorization.py -q`
  - 结果：36 passed。

## 未验证范围与风险

- 其余审查问题仍在修复中。
- 尚未运行本会话全部聚焦测试的汇总验证。
