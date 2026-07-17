# 项目级 RBAC 与统一审计验收

## 本地验收结果

| 检查项 | 命令或范围 | 结果 |
| --- | --- | --- |
| 后端全量 | `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test -q` | `490 passed` |
| AI 权限与脱敏 | `test_ai_history_security.py`、`test_ai_platform.py`、`test_ai_services.py` | `48 passed` |
| 迁移 | `test_project_rbac_unified_audit_migration.py` | `6 passed`，覆盖唯一 head、SQLite/PostgreSQL/MySQL DDL 与 SQLite `r7 → r8 → r7` |
| 配额授权 | `test_quota_adjustment.py` | `19 passed` |
| 关联与模型审计 | correlation、AI 模型、操作审计和统一审计组合 | `51 passed` |
| 前端全量覆盖率 | `npm run test:coverage` | 无失败；Lines/Statements `97.67%`、Functions `82.26%`、Branches `87.40%` |
| 前端生产构建 | `npm run build:prod` | 通过；保留未定义 `%VITE_APP_TITLE%` 和大 chunk 警告 |

## 已验收的行为

- 成员唯一性、角色矩阵、跨项目拒绝、`pt_user` 删除、采集补齐 `reader`、项目组负责人配额例外及 `editor` 拒绝均有自动化覆盖。
- 统一审计为单一合并迁移；审计触发器、三方言 DDL、请求/追踪 ID、异常响应回写和 AI/任务关联均已回归。
- AI 会话没有 `project_id`；当前权限撤销后历史项目工具回合隐藏，安全的全局工具回合仍可见；管理员 AI 审计详情不返回 prompt、原始 response、路径或凭据。
- 项目资源列表、统计、导出、趋势、审计页签及配额按钮均由服务端项目权限和 capabilities 约束。

## 未在本地完成的生产验收

- PostgreSQL 生产备份恢复、`stamp`、upgrade/downgrade、触发器、应用写入账号和审计只读账号的实际授权。
- 真实 NetApp/Isilon 的配额设备写入、采集和 Feishu 通知投递。
- 浏览器端到端流程：仓库没有 Playwright 配置或依赖，当前桌面环境也没有可用 Browser runtime；前端自动化仅覆盖 Vitest 和生产构建。

## 上线前强制事项

升级 `000000000008` 前备份数据库。迁移删除 `projects.pt_user_id`，downgrade 只重建空列，不能恢复历史 PT 负责人数据。
