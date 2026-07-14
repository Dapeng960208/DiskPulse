# 后端架构说明

## 1. 范围

本文说明 `backend/` 当前实现。后端使用 FastAPI 提供 REST API，使用 PostgreSQL 保存业务状态，使用 QuestDB 保存时序监控数据，并通过 Celery 执行采集、告警、备份等周期任务。

## 2. 运行拓扑

```text
Frontend / Client
    |
    v
FastAPI: backend/main.py
    |
    +-- routers/*                # API 路由
    |       |
    |       +-- crud/*           # 查询和写入逻辑
    |               |
    |               +-- models.py
    |
    +-- crud/questDbCrud.py      # QuestDB 查询
    |
    +-- celery_tasks/tasks/*     # Celery 任务入口
            |
            +-- celery_tasks/manager/*
                    |
                    +-- 存储系统 API / SSH / IAM / 邮件
```

## 3. API 入口

`backend/main.py` 将所有路由注册在统一前缀下：

```text
/storage-pulse/api
```

| 模块 | 路径 | 职责 |
| --- | --- | --- |
| `users` | `/users` | 用户、离职状态、告警偏好、用户总用量 |
| `projects` | `/projects` | 项目元数据和项目级存储汇总 |
| `config` | `/config` | 系统集成配置 |
| `group` | `/groups` | 项目组目录监控配置 |
| `storage_cluster` | `/storage-clusters` | NetApp/Isilon 集群配置 |
| `aggregate` | `/aggregates` | Aggregate 容量和趋势 |
| `volumes` | `/volumes` | Volume 容量和趋势 |
| `qtrees` | `/qtrees` | Qtree 容量和趋势 |
| `storage_usage` | `/storage-usages` | 用户目录用量、导出、备份、扩容 |
| `storage_alerts` | `/storage-alerts` | 告警和报告记录 |
| `storage_back_up_records` | `/storage-back-up-records` | 备份记录和回滚 |
| `large_files` | `/large-files` | 大文件扫描结果 |

请求级 PostgreSQL session 由 `db_session_middleware` 创建并关闭，业务代码通过 `dependencies.get_db()` 获取。

## 4. 配置

`backend/appConfig.py` 使用 PyYAML 加载按子系统分类的 `backend/config.yml`。应用不读取 `.env` 或运行时环境变量；手工 NetApp/Isilon 检查脚本仍单独使用环境变量，避免把设备凭据并入应用配置。

| 分类 | 用途 |
| --- | --- |
| `application` | 运行模式、公司名称和 CORS 来源 |
| `database.postgres` | PostgreSQL 连接和连接池 |
| `database.questdb` | QuestDB 连接和连接池 |
| `redis` | Celery broker/backend 地址 |
| `jwt`、`ldap`、`super_admin_usernames` | 登录、令牌和超级管理员 |
| `storage` | 存储客户端运行开关 |

真实 `backend/config.yml` 和 LDAP 密码文件不得提交；仓库只保留 `backend/config.example.yml` 与无敏感值的 `backend/config.test.yml`。相对密码文件路径以 YAML 所在目录为基准，PostgreSQL 和 QuestDB URL 由加载器集中生成并转义凭据。

## 5. 数据层

### PostgreSQL

`backend/models.py` 是关系模型入口。

| 模型 | 表 | 说明 |
| --- | --- | --- |
| `StorageConf` | `storage_conf` | 系统配置 |
| `User` | `users` | 用户和 IAM 同步信息 |
| `Host` | `hosts` | SSH 主机信息，路径状态和大文件检查仍在使用 |
| `Project` | `projects` | 项目和项目级资源统计 |
| `StorageCluster` | `storage_clusters` | 存储集群配置 |
| `Aggregate` | `aggregates` | Aggregate 容量 |
| `Volume` | `volumes` | Volume 容量和分配量 |
| `Qtree` | `qtrees` | Qtree 容量和状态 |
| `Group` | `groups` | 项目组目录监控配置 |
| `StorageUsage` | `storage_usages` | 用户目录配额、用量和文件元数据 |
| `StorageAlerts` | `storage_alerts` | 告警和报告 |
| `StorageBackUpRecord` | `storage_back_up_records` | 备份生命周期 |
| `LargeFiles` | `large_files` | 大文件扫描结果 |

### QuestDB

`backend/questdb/models.py` 保存趋势数据模型。实时图表查询通过 `backend/crud/questDbCrud.py` 完成。

| 表 | 维度 |
| --- | --- |
| `storage_cluster_storage_usages` | `storage_cluster_id` |
| `aggregate_storage_usages` | `aggregate_id`、`storage_cluster_id` |
| `volume_storage_usages` | `volume_id` |
| `qtree_storage_usages` | `qtree_id` |
| `project_storage_usages` | `project_id` |
| `group_storage_usages` | `group_id` |
| `storage_usages` | `storage_usage_id`、`user_id` |

## 6. 领域关系

```text
StorageCluster
    +-- Aggregate
    +-- Volume
            +-- Qtree
                    +-- Group
                            +-- StorageUsage

Project
    +-- Group

User
    +-- StorageUsage
    +-- owned Group
    +-- StorageBackUpRecord
    +-- LargeFiles
```

## 7. 后台任务

| 任务 | 入口 | 说明 |
| --- | --- | --- |
| 存储采集 | `storages_schedule_fetching_task` | 遍历启用的 `StorageCluster`，执行 `StoragePulseMonitor`。 |
| 路径状态同步 | `check_user_path_status_hourly` | 通过 `Host` 和 SSH 扫描用户目录，更新 `StorageUsage`。 |
| 用户告警 | `user_storage_usage_alert_hourly` | 生成用户目录告警。 |
| 项目组/系统告警 | `group_storage_usage_alert_hourly` | 生成项目组和系统告警。 |
| 周报 | `project_storage_usage_report_weekly` | 生成项目周报。 |
| 离职用户备份 | `quit_user_back_up_daily` | 触发备份流程、清理和通知。 |

## 8. 维护注意事项

- 不要删除 `Host` 或 `Group.monitor_host_id`，除非同步替换路径状态和大文件检查链路。
- 不要删除 `StorageUsage` 文件元数据字段，除非同步修改详情页、导出和告警模板。
- CRUD 中的动态排序参数应逐步改为白名单，避免调用方传入任意 ORM 属性。
- PostgreSQL 使用单一 Alembic initial baseline `000000000001` 从空库创建当前 `14` 张表；旧 revision 数据库不支持原地升级。QuestDB 由独立模型和初始化流程维护，不属于 Alembic。
