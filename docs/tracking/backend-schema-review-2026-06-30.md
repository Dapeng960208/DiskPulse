# 后端 Schema 审查记录 - 2026-06-30

## 主题

本次审查聚焦后端数据库模型和 API schema 的一致性，同时补充文档结构和回归测试。

## 已完成

- 从 `backend/models.py` 删除未使用的 `StorageRecords` ORM 映射。
- 从 `ProjectBase` 删除不属于 `projects` 表、也没有当前后端计算来源的历史资源字段。
- 新增 `backend/test/test_backend_schema_contract.py`，防止无用模型和历史字段回归。
- 没有新增 Alembic 迁移脚本；数据库侧清理由单独变更处理。

## 删除的数据库结构

### `storage_records`

原 ORM 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `Integer` | 主键 |
| `linux_path` | `String` | 路径 |
| `used` | `Float` | 用量 |
| `updated_at` | `DateTime` | 更新时间 |

审查结果：

- 没有 router 引用。
- 没有 CRUD 模块引用。
- 没有 Celery manager/task 读写。
- 没有 Pydantic schema 暴露。
- 前端源码没有引用 `storage_records` 或 `StorageRecords`。

处理方式：

- 删除 ORM 映射。
- 不在本轮新增迁移脚本。若部署数据库仍存在该表，需在对应环境单独确认后删除。

## Project Schema 清理

删除的历史字段：

```text
master, max_swp, resources, rsv, r15s, r1m, r15m, ut, pg, ls, it, tmp, swp, sut, mut
```

这些字段不在 `Project` ORM 中，也没有当前后端计算逻辑。继续暴露会让 API 契约看起来像包含持久化字段。

保留字段：

```text
mem, mem_reserved, slot, slot_reserved, run_jobs, ssusp_jobs, ususp_jobs, pend_jobs
```

这些字段存在于 `projects` 表或仍属于当前项目资源契约。

## 已审查但保留

### `Host` 和 `Group.monitor_host_id`

保留原因：

- `SynchronousPathState` 通过 `Group.monitor_host_id` 查找 `Host.ip` 并执行 SSH 路径检查。
- `LargeFileAlert` 使用同样链路检查大文件是否仍存在。
- 前端组配置表单仍包含 Host 选择。

### `StorageUsage` 文件元数据

保留字段：

```text
size, blocks, io_block, type, device, inode, links, access, gid,
access_time, modify_time, change_time, birth_time
```

保留原因：

- `SynchronousPathState` 会从 `stat` 输出写入这些字段。
- 使用量详情页和列表展开区域会展示其中多个字段。
- 导出和告警模板会使用 `access_time`、`modify_time`。

### `StorageUsage.file_limit`

保留原因：

- NetApp、Isilon 和旧版 quota 采集路径仍会写入该字段。

## 后续建议

- 为 `/hosts` 补齐后端 CRUD，或移除前端 Host 选择并改用集群级 SSH 配置。
- 对 CRUD 动态排序字段加白名单。
- 明确 `storageMonitor.py`、`netAppMonitor.py`、`isilonMonitor.py` 是否仍是生产路径。
- 如果线上存在 `storage_records`，单独制定数据库清理方案。

## 验证

```bash
.\.venv\Scripts\python.exe -m unittest backend.test.test_backend_schema_contract
.\.venv\Scripts\python.exe -m unittest discover backend/test
```
