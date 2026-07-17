# 项目级 RBAC、统一操作审计与 AI 数据隔离功能说明

## 范围

- 为项目添加成员、角色和项目资源隔离。
- 提供项目审计与超级管理员统一操作审计页面/API。
- 对关键管理、设备、AI、采集和通知动作保留可关联的脱敏审计。
- 让 AI 会话独立于项目，但绝不返回当前用户无权访问的项目数据。

## 角色与能力

| 主体 | 读取项目资源 | 管理成员 | 授予项目管理员 | 调整配额 |
| --- | --- | --- | --- | --- |
| `reader` | 所属项目 | 否 | 否 | 否 |
| `editor` | 所属项目 | 否 | 否 | 否 |
| `project_admin` | 所属项目 | 可管理 `reader`/`editor` | 否 | 否，除非同时是项目组负责人 |
| 项目组负责人 | 受其负责项目组约束 | 否 | 否 | 仅该项目组和其用户目录 |
| `super_admin` | 全局 | 是 | 是 | 是 |

## API 与页面入口

- 成员 API：`/storage-pulse/api/projects/{project_id}/members`，提供集合 `GET/POST` 和单成员 `PATCH/DELETE`。
- 统一审计 API：`/storage-pulse/api/v1/audit-events` 及详情；超级管理员查询全局，项目管理员仅能查询已授权项目范围。
- 项目详情具有“项目组、成员、项目审计”页签；成员和项目审计由 `capabilities.manage_members` 与 `capabilities.view_audit_events` 控制。
- 系统管理具有 `/admin/audit-events` 和详情路由；前端只向超级管理员展示入口。
- 项目组和用户目录的调整配额按钮仅由 `capabilities.adjust_quota` 显示。

## AI 行为

- 新建 AI 会话只包含标题和模型，不要求或持久化项目 ID。
- 会话仅创建者可读写；工具调用沿用当前用户的后端授权。
- 项目成员资格变更后，历史工具结果及其后的无工具总结会立即按新权限重新检查；无可验证范围、缺少 visibility 或没有审计记录的旧助手回合默认隐藏。

## 非范围

本功能不引入 OIDC/SSO、服务账号、SIEM、双人审批或把设备写权限下放给 `editor`。
