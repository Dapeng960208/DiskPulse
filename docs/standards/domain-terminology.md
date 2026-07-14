# 领域术语表

本文档统一 DiskPulse 后端、前端和文档中的核心领域命名。代码字段名保留英文，说明文本使用简体中文。

## 产品与入口

| 术语 | 说明 | 代码/配置 |
| --- | --- | --- |
| DiskPulse | 当前产品名称，用于 API 标题、邮件模板和项目文档。 | `DiskPulse` |
| 存储监控 | 对存储集群、容量池、存储空间、Qtree（NetApp）、用户目录、容量使用率和告警的采集与展示。 | `storage` |
| 管理后台 | 前端访问 DiskPulse 的页面入口。 | `domain_name` |

## 存储资源

| 术语 | 说明 | 代码/表 |
| --- | --- | --- |
| 存储集群 | NetApp 或 Isilon 等后端存储系统实例。 | `StorageCluster` |
| 容量池 | 厂商提供的物理容量池；NetApp 对应 Aggregate / Local Tier，Isilon 对应 Storage Pool / Node Pool。 | `Aggregate` |
| 存储空间 | 可分配给项目组的逻辑存储目标；NetApp 对应 Volume，Isilon 对应 Directory Quota。 | `Volume` |
| Qtree（NetApp） | NetApp 存储空间下级的目录和配额目标；Isilon 不适用。 | `Qtree` |
| 项目组 | 组织或业务维度的存储使用单位。 | `Project` / `Group` |
| 项目组标签 | 只包含名称、由项目组引用的全局分类标签；不绑定项目或存储集群。 | `GroupTag` / `group_tag_id` |
| 用户目录 | 分配给单个用户的目录和配额记录。 | `StorageUsage` |
| 大文件 | 满足阈值条件、需要清理或告警的文件记录。 | `LargeFiles` |

## 容量指标

| 术语 | 说明 | 代码字段 |
| --- | --- | --- |
| 限额 | 管理员配置或存储系统返回的容量上限。 | `limit` |
| 已用容量 | 当前已使用容量。 | `used` |
| 已分配容量 | 已分配给下级资源的容量。 | `allocated` |
| 使用率 | 已用容量占限额的比例。 | `use_ratio` / `used_ratio` |
| 阈值 | 告警、扩容或清理判断使用的比例或容量值。 | `threshold` |

## 权限与安全

| 术语 | 说明 | 代码/配置 |
| --- | --- | --- |
| 登录用户 | 通过 LDAP 登录并持有有效 JWT 的用户。 | `CurrentUserDep` |
| 超级管理员 | 可执行配置、用户、资源变更和扩容等高风险操作的用户。 | `super_admin_usernames` |
| Bearer Token | API 鉴权要求的 `Authorization` 头格式。 | `Authorization: Bearer <token>` |
| 令牌撤销 | 登出后当前 JWT 的 `jti` 加入撤销列表，后续请求拒绝。 | `revoke_token` |

## 通知与任务

| 术语 | 说明 | 代码 |
| --- | --- | --- |
| 告警邮件 | 容量、备份、大文件等事件触发的邮件通知。 | `EmailNotification` |
| 备份记录 | 离职或清理场景下的目录备份任务记录。 | `StorageBackUpRecord` |
| 扩容 | 对用户目录、项目组、存储空间或 Qtree（NetApp）增加容量限额。 | `expand` |
| 手工集成检查 | 连接真实 NetApp/Isilon 的本地脚本，不属于单元测试。 | `backend/scripts/manual_*_check.py` |
