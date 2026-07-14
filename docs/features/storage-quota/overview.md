# 存储配额软限额

## 目标

NetApp 和 Isilon 的配额数据同时包含硬限额和软限额。本功能在现有硬限额字段 `limit`、`use_ratio` 不改名的前提下，新增 `soft_limit` 和 `soft_use_ratio`，用于展示和持久化软限额。

## 范围

- 覆盖配额链路：`storage_usages`、`qtrees`、`volumes`、`groups`、`projects`。
- 不覆盖物理容量层：`aggregates`、`storage_clusters` 仍只展示容量硬口径。
- 现有告警继续按 `use_ratio` 判断，不切换到 `soft_use_ratio`。

## 数据来源

| 存储类型 | 资源 | 硬限额来源 | 软限额来源 |
| --- | --- | --- | --- |
| NetApp | 用户配额 | `space.hard_limit` | `space.soft_limit` |
| NetApp | Qtree/tree 配额 | `space.hard_limit` | `space.soft_limit` |
| Isilon | 用户配额 | `thresholds.hard`，linked 用户继承 default-user | `thresholds.soft`，linked 用户继承 default-user |
| Isilon | 目录配额 | `thresholds.hard` | `thresholds.soft` |

软限额为空、`0` 或 `-1` 时视为未设置，接口返回 `soft_limit = null`、`soft_use_ratio = null`。

## 集群配置后的自动采集

- 新建启用的 NetApp 或 Isilon 集群后，后端立即投递该集群的存储采集任务并同步卷信息。
- 将集群更新为启用状态，或更新已启用集群配置后，同样重新投递该集群采集任务。
- 存储集群新增/编辑表单提供“是否启用”开关，新建默认启用；停用后保存不会投递采集任务。
- 未启用集群不投递；任务异步执行，配置保存不等待设备响应。任务投递或采集失败写入服务端日志，周期采集仍会在后续轮次重试。
- NetApp 卷来自 ONTAP volume API；Isilon 卷继续按 OneFS directory quota 路径生成。

开发环境使用 `uvicorn main:app --reload` 时，API 控制台记录任务投递开始、成功或失败；Celery worker 控制台记录任务开始及现有的轮次完成/失败信息。日志只包含集群 ID 和任务状态，不输出设备地址、账号或密码。

## 展示与导出

- 用户用量、项目组、Qtree、Volume 列表展示“硬限额/硬利用率”和“软限额/软利用率”。
- 无软限额时页面显示“无软限额”，不显示 0%。
- 存储使用导出增加“软限额”“软使用率”列。

## 数据库与迁移

单一 initial baseline `000000000001` 在以下表直接创建 nullable 字段：

- `projects.soft_limit`、`projects.soft_use_ratio`
- `volumes.soft_limit`、`volumes.soft_use_ratio`
- `qtrees.soft_limit`、`qtrees.soft_use_ratio`
- `groups.soft_limit`、`groups.soft_use_ratio`
- `storage_usages.soft_limit`、`storage_usages.soft_use_ratio`

项目处于初始开发阶段，不保留软限额增量 revision，也不提供旧数据库字段回填；开发数据库从空库执行 baseline。

## 验证

- `.\.venv\Scripts\python.exe -m unittest backend.test.test_storage_soft_quota`
- `.\.venv\Scripts\python.exe -m unittest backend.test.test_core_api`
- `cd frontend && npx vitest run test/unit/utils/quota.test.js --coverage.enabled=false`
- `cd frontend && npx vitest run test/unit/smoke/surface-regression.test.js --coverage.enabled=false`
- `.\.venv\Scripts\python.exe -m pytest backend\test\test_core_api.py backend\test\test_storage_collection_trigger.py -q`
