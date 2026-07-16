# 系统设置废弃配置清理设计

> 状态：已完成
> 确认日期：2026-07-16
> 完成日期：2026-07-16

## 1. 目标

收敛系统设置为仍在使用的存储告警规则，移除已经废弃的全局存储连接和 IAM/BPM 配置，避免继续保存无效凭据或保留不可达逻辑。

## 2. 前端范围

- 系统设置标题区改为普通背景，只保留“系统设置”标题，不显示蓝色区块和副标题。
- 邮箱配置和邮件链接不再显示，但其字段、配置 API 和邮件发送逻辑继续保留。
- 删除 IAM 相关配置和存储配置的页签及字段展示。
- 页面只剩存储告警规则，因此移除单页签容器，直接展示 `StorageAlertRuleForm` 和保存按钮。
- 保留现有保存中状态、规则校验和成功提示。

## 3. 配置与数据库范围

从 `storage_conf`、ORM 模型和读写 schema 中删除：

- IAM：`iam_url`、`iam_account`、`iam_password`。
- BPM：`bpm_api_url`、`bpm_process_id`。
- 废弃的全局存储连接：`storage_host`、`storage_port`、`storage_user`、`storage_password`。

已新增 Alembic `000000000007_deprecated_config_cleanup` 迁移。升级物理删除上述九列；降级恢复 `nullable` 空列，不恢复已删除数据。迁移覆盖 SQLite 在线升降级，并生成 SQLite、PostgreSQL 和 MySQL 离线 SQL。

以下内容明确保留：

- `storage_clusters` 表中的每集群 `storage_host`、`storage_port`、`storage_user`、`storage_password`，当前采集仍依赖这些字段。
- 邮件配置、邮件链接、目录操作、备份配置和 `storage_alert_rule` 字段。
- 用户表中的 `iam_id` 等历史业务数据字段；本轮只删除外部 IAM 集成，不清洗已有用户数据。

## 4. 逻辑删除范围

- 删除 `utils/iam/iamApi.py` 及仅供该集成使用的 `IamUser` schema。
- 删除 `RemoteFileManager.initiating_quit_users_bpm_process()` 和每日备份任务中对它的调用；备份删除、回滚、告警和其他目录操作保持不变。
- 删除无前端调用的 `/storage-usages/expand` 路由及 `StorageUsageExpand` schema。
- 删除依赖全局存储凭据的旧 `StorageManagement`、`SynchronousPathState` 和对应未启用任务。当前按每集群运行的容量、事件、性能与告警采集保持不变。
- 删除同样依赖全局存储账号和密码的 `LargeFileState` 及未启用的 `check_large_files_status_daily` 任务；大文件邮件告警能力继续保留。
- 删除后执行全仓引用扫描，确保生产代码不再读取已删除字段或导入已删除模块。

## 5. API 行为

- `GET /config/storage` 和 `PUT /config/storage` 不再返回或接受 IAM、BPM、全局存储连接字段。
- 邮件、邮件链接、备份和存储告警规则字段继续保持现有契约。
- `/storage-usages/expand` 从 OpenAPI 中移除；其他用户目录接口不变。
- 不新增替代接口，不把旧全局扩容迁移到每集群凭据。

## 6. 安全与迁移

- 数据库升级会物理删除废弃凭据列，而不是只在 API 中隐藏。
- 不在日志、迁移或测试中回显历史密码。
- 升级前如需保留历史配置，部署方自行备份数据库；降级只恢复空列和默认值，不恢复已删除数据。
- 邮箱配置仅隐藏，因此仍可能通过配置 API 由已有调用者读写；本轮不改变邮件服务。

## 7. TDD 与验收

1. 前端 RED：系统设置只显示普通标题和告警规则，不包含四个废弃页签或副标题。
2. 后端 RED：schema、ORM、OpenAPI 和生产引用中不存在被删除字段、IAM/BPM 类或旧扩容路由。
3. 迁移 RED：升级删除九个字段，降级恢复字段；验证 SQLite 在线升降级及 PostgreSQL/MySQL SQL 生成。
4. GREEN 后运行前后端聚焦测试、前端 ESLint、后端 `compileall`、Alembic 单 head 和引用扫描。
5. 页面契约验证系统设置仅显示普通标题、告警规则和保存按钮。

实际 TDD 与验收结果：

- RED 契约提交为 `2e36631`。
- 前端设置与告警规则相关测试 `10 passed`，目标 ESLint 通过。
- 后端聚焦测试 `84 passed`；独立只读验收执行后端全量回归为 `326 passed`。
- 后端 `compileall` 通过；Alembic `heads`、`history` 通过，唯一 head 为 `000000000007`。
- SQLite 在线 upgrade/downgrade 通过；SQLite、PostgreSQL、MySQL 离线 SQL 生成通过。
- 生产引用扫描未发现九个废弃字段、IAM/BPM 类、旧扩容及旧全局凭据任务的残留调用；未发现敏感配置值写入日志。

## 8. 风险与边界

- 删除 `/storage-usages/expand` 是公开接口收缩；代码确认当前前端没有调用者，外部脚本若仍调用将无法再使用该接口。
- 删除 IAM/BPM 后，离职备份不再自动创建 BPM 流程；其他备份任务是否执行仍由现有调度和配置决定。
- 删除旧路径同步逻辑不会影响当前每集群容量采集，但任何绕过 Celery Beat 手工调用旧任务的外部运维脚本需要同步下线。
- 不删除 `StorageCluster` 连接凭据、不修改 LDAP 登录、不修改飞书通知和存储告警规则。
- PostgreSQL 和 MySQL 仅完成离线 SQL 编译，未连接真实实例执行迁移；部署前仍需按目标数据库备份并验证升级与回滚。
