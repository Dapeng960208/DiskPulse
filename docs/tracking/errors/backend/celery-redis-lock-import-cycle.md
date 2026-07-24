# Celery Redis 锁在任务注册期形成循环导入

## 错误内容

`redis_lock` 在模块加载期导入 `celery_worker.redis_client`，而 `celery_worker` 注册任务时导入 `storages`，后者又导入 `redis_lock`，导致单独导入 LDAP 同步任务时出现 partially initialized module 的循环导入错误。

## 解决方案

保留 Redis client 归属 `celery_worker`，但把该导入移动到 `redis_lock()` 的调用时。这样任务注册完成后再获取 client，避免注册期的循环依赖，同时不改变锁的 Redis 实例或命名。

## 备注

- 分类：`backend`
- 首次出现：2026-07-24，`2026-07-24-router-transactions-startup-security`。
- 最近出现：2026-07-24，`2026-07-24-router-transactions-startup-security`。
- 出现次数：1。
