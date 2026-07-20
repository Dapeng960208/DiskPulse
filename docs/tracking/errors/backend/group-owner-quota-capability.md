# 项目负责人配额能力测试混淆资源授权边界

## 错误内容

`backend/test/test_project_scope_authorization.py` 曾把“项目负责人可调整项目内用户目录配额”误写成“项目负责人可调整项目组配额”，因此断言 `GET /groups/{id}` 的 `capabilities.adjust_quota` 为 `true`。当前权威边界是：项目组配额仅超级管理员可调整；项目负责人和超级管理员可调整项目内用户目录配额。

## 解决方案

按资源类型拆分权限矩阵：项目组配额覆盖超级管理员允许、其他角色拒绝；用户目录配额覆盖项目负责人和超级管理员允许、其他角色拒绝。Router 不得复制比 Service 更严格的角色预检。

## 备注

- 首次出现：2026-07-20，`2026-07-20-storage-utilization-range-query` 会话。
- 最近出现：2026-07-20；出现次数：3。
- 差异：首次修改 `GET /groups/` 的列表筛选参数和 CRUD 条件；本次扩展到容量集合筛选。两次均未修改 `GET /groups/{group_id}` 或能力计算路径。
- 出现记录：`sessions/2026-07-20-recent-code-review-remediation/errors.md`；本次复核功能事实文档后纠正了历史错误前提，并补全两类资源的角色矩阵。
