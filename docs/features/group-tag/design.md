# 项目组标签设计

## 1. 目标

`GroupTag` 是项目组的全局标签，只负责提供可复用的名称。它不代表项目存储环境，不绑定项目或存储集群，也不承载容量、采集状态、实时趋势等运行数据。

## 2. 数据模型

```text
Project 1 ── * Group * ── 1 StorageCluster
                  |
                  *
                  |
                  1
               GroupTag
```

`group_tags` 仅包含：

| 字段 | 约束 | 说明 |
| --- | --- | --- |
| `id` | 主键 | 标签标识 |
| `name` | 非空、全局唯一、最长 128 字符 | 标签名称 |

`groups` 直接保存 `project_id`、`storage_cluster_id` 和 `group_tag_id`。项目组名称在同一项目、存储集群和标签组合内唯一。Volume/Qtree 目标必须属于 `Group.storage_cluster_id` 指向的集群；Isilon 项目组只允许选择 Volume。

## 3. API

标签使用全局 CRUD：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET`、`POST` | `/storage-pulse/api/group-tags` | 分页查询或新增标签 |
| `GET`、`PUT`、`DELETE` | `/storage-pulse/api/group-tags/{id}` | 查询、修改或删除标签 |

写操作要求超级管理员。名称重复返回 `409`；仍被项目组引用的标签禁止删除并返回 `409`。标签写入只接受 `name`。

项目组创建时必须直接提交：

```json
{
  "project_id": 1,
  "storage_cluster_id": 2,
  "group_tag_id": 3,
  "name": "研发组",
  "volume_id": 10
}
```

## 4. 前端

- 系统管理提供“项目组标签”页面，只维护标签名称。
- 项目组表单分别选择项目、存储集群和项目组标签，不再按项目级联加载存储环境。
- 项目、Dashboard、用户目录和告警页面展示 `group_tag.name`；容量和实时趋势继续来自 Project、Group 与存储资源。

## 5. 迁移边界

`000000000001_initial_schema.py` 直接创建 `group_tags` 和新的 `groups` 外键；后续存储集群协议/TLS revision 不改变 GroupTag 数据结构。项目不提供旧 `project_storage_environments` 数据回填或兼容窗口；使用已删除旧 revision 链的开发数据库需确认数据可丢弃后重建空库。
