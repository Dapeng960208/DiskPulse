# 用户信息管理

## 目标与入口

系统管理的“用户信息管理”页面位于 `/admin/users`，供超级管理员查询和维护系统用户，并通过“一键同步”把 LDAP 用户快照同步到本系统。现有 `GET /storage-pulse/api/users/` 列表接口继续供所有已登录用户及既有用户选择场景复用；页面维护、写操作和 LDAP 同步仅允许超级管理员执行。

## 人工维护

- 列表展示登录用户名、姓名、邮箱、部门、用户类型、告警状态和存储用量，并支持按用户关键字查询。
- 创建用户时必须填写唯一的登录用户名 `rd_username`；创建后该字段不可修改。
- 超级管理员可维护姓名 `username`、邮箱 `email`、部门 `department`、用户类型 `user_type` 和告警状态 `is_alert`，也可删除用户。
- 用户类型固定为 `0=离职`、`1=公共用户`、`2=在职`；模型默认值保持为 `2`，本功能不新增数据库字段或 Alembic migration。

## LDAP 同步

超级管理员调用 `POST /storage-pulse/api/users/sync-ldap` 获取完整 LDAP 用户快照并在单个数据库事务中应用。成功响应返回以下统计：

| 字段 | 说明 |
| --- | --- |
| `ldap_total` | LDAP 快照中的用户总数。 |
| `created` | 新增为在职用户的数量。 |
| `updated` | 已同步非空资料的现有用户数量。 |
| `reactivated` | 从离职恢复为在职的用户数量。 |
| `marked_inactive` | 因 LDAP 快照缺失而转为离职的在职用户数量。 |

同步按忽略大小写的 `rd_username` 匹配用户，并遵循以下生命周期：

- LDAP 新用户创建为在职用户 `2`。
- LDAP 中存在的离职用户 `0` 恢复为在职用户 `2`，并把 `quit_days` 清零。
- LDAP 中缺失的在职用户 `2` 标记为离职用户 `0`，不会删除记录。
- 公共用户 `1` 的类型永远不由 LDAP 改变；只有超级管理员可以人工调整。公共用户在 LDAP 中存在时仍可更新非空的姓名、邮箱和部门，缺失时不受影响。
- LDAP 返回的非空姓名、邮箱和部门可覆盖现有资料；空邮箱或空部门保留系统原值。
- 超级管理员把公共用户改为离职或在职后，该用户从下一次同步开始遵循对应生命周期。

### Celery 自动同步

- Celery Beat 每 8 小时投递一次 `ldap_users_sync_schedule_task`，任务继续复用 `usersService.sync_ldap_users`，因此自动同步与人工同步使用相同的快照、匹配、生命周期和事务规则。
- 自动任务使用独立 PostgreSQL 会话和 Redis 非阻塞锁；同一同步仍在运行时，后续实例跳过，避免并发应用同一份用户快照。
- Worker 或 Beat 启动时不立即执行同步，首次执行由正常的 8 小时周期触发。
- 自动任务失败时保留原有回滚语义并向 Celery 暴露失败状态；人工 `POST /storage-pulse/api/users/sync-ldap` 入口继续保留，不改变权限和响应契约。

## 配置与安全边界

- LDAP 用户搜索范围和字段映射继续使用本地 `backend/config.yml`；可提交结构参考 `backend/config.example.yml`。
- `ldap.user_department_attribute` 指定部门属性，默认值为 `department`。目录使用其他属性时，部署侧必须在真实 `backend/config.yml` 中显式修改；真实配置保持本地，不提交到仓库。
- 任一 LDAP 搜索范围查询不完整、目录查询失败或完整快照为空时，同步返回 `503` 且不写入数据库，避免误把全部在职用户标记为离职。
- LDAP 快照或本地数据存在忽略大小写的用户名冲突时，同步拒绝并回滚整个事务。
- 同步不删除用户，不提供同步历史表或预演接口；后台自动同步只复用现有全量同步服务，不引入第二套 LDAP 规则。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest backend\test\test_user_management_ldap_sync.py backend\test\test_scheduled_user_tasks.py -q
cd frontend
npx vitest run test/unit/user-management-ldap-sync.test.js test/unit/router/routes.test.js --coverage.enabled=false
```

真实 LDAP 连通性、字段权限和目录规模仍需在部署环境执行只读快照与同步验收。
