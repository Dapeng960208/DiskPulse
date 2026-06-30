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

## 展示与导出

- 用户用量、项目组、Qtree、Volume 列表展示“硬限额/硬利用率”和“软限额/软利用率”。
- 无软限额时页面显示“无软限额”，不显示 0%。
- 存储使用导出增加“软限额”“软使用率”列。

## 数据库与迁移

迁移 `f4b2c8d9e701_add_soft_quota_fields.py` 为以下表新增 nullable 字段：

- `projects.soft_limit`、`projects.soft_use_ratio`
- `volumes.soft_limit`、`volumes.soft_use_ratio`
- `qtrees.soft_limit`、`qtrees.soft_use_ratio`
- `groups.soft_limit`、`groups.soft_use_ratio`
- `storage_usages.soft_limit`、`storage_usages.soft_use_ratio`

当前工作区中既有多份历史 migration 文件处于删除状态，本次未恢复也未回退；新增 migration 的 `down_revision` 仍接在 Git 中既有链路末端 `a1d670c60836`。

## 验证

- `.\.venv\Scripts\python.exe -m unittest backend.test.test_storage_soft_quota`
- `.\.venv\Scripts\python.exe -m unittest backend.test.test_core_api`
- `cd frontend && npx vitest run test/unit/utils/quota.test.js --coverage.enabled=false`
- `cd frontend && npx vitest run test/unit/smoke/surface-regression.test.js --coverage.enabled=false`

## 已知规范缺口

`docs/standards/domain-terminology.md` 在当前仓库不存在，但 `AGENTS.md` 和部分标准文档仍要求读取；本次按实际存在的标准文档执行，并在当前交付记录中保留该缺口。
