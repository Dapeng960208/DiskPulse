# 项目级 RBAC、统一操作审计与 AI 数据隔离设计

## 目标

在不改变 LDAP、JWT、Redis 会话和超级管理员语义的前提下，为项目资源建立最小项目角色模型，并使关键写操作可追溯、审计记录不可篡改。AI 会话不属于任何项目；它只属于创建者，工具结果在调用和读取历史时都按当前项目权限重新约束。

## 权限模型

`project_memberships` 的角色为 `reader`、`editor`、`project_admin`。项目 `in_charge_user_id` 初始化为 `project_admin`；已删除 `pt_user_id`。`project_admin` 只能管理本项目的 `reader` 和 `editor`，授予或撤销 `project_admin` 仅限超级管理员。

项目组负责人是设备写配额的受控例外：仅其负责的项目组及其用户目录可调整配额。普通 `editor` 没有 `adjust_quota` 能力，也会被服务端拒绝。前端只消费后端返回的 `capabilities`，不承担授权判断。

## 资源隔离

项目反查以 `Group.project_id` 为根；用户目录和大文件经 `group_id` 反查，告警仅在关联资源可反查时进入项目范围。列表、统计和导出在数据库分页前加入项目过滤；无项目作用域的集群、容量池、卷和 Qtree（NetApp）只对超级管理员可见。

采集写入用户目录后，同一事务批量补齐 `StorageUsage → Group → Project` 的 `reader` 成员关系；已有较高角色不降级。

## AI 设计

`AIConversation` 不新增 `project_id`。工具通过当前用户身份签发的内部 Bearer token 调用原 HTTP 路由，因此沿用后端资源授权。每个工具轨迹保存最小、脱敏的项目可见范围；读取历史时重新计算当前成员项目集合。权限已失效或旧轨迹没有可证明范围时，助手内容和工具结果一并隐藏。全局工具的显式空范围仍对会话创建者可见。

AI 专项表 `ai_audit_logs` 保留；其 `trace_id` 继承请求审计上下文。显示或管理员读取前再次清除 token、密码、完整路径、prompt、原始 response 和设备原始响应。

## 统一审计

`audit_events` 是只追加记录，包含请求、追踪和操作关联 ID。HTTP 中间件校验或生成 `X-Request-ID`、`X-Trace-ID`，无论正常还是异常响应均回写它们。登录、成员变更、配额、AI 生命周期、AI 模型治理、采集、通知任务及其他管理写入均写入统一审计；设备调用使用同一 `operation_id` 的 attempt/result。

数据库迁移为 SQLite、PostgreSQL、MySQL 创建拒绝审计 `UPDATE`/`DELETE` 的触发器。生产应用/只读账号的实际授权仍需要在上线窗口验证。

## 迁移与回滚边界

合并迁移为 `000000000008_project_rbac_unified_audit.py`，是唯一 head。SQLite batch 迁移显式保留 `projects.storage_alert_rule`。升级删除 `pt_user_id`；downgrade 只重建空列，不能恢复历史 PT 负责人值，因此上线前必须备份，不能用 downgrade 作为数据回滚方案。
