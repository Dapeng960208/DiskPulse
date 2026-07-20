# 用户目录存储用量汇总交付

## 范围

修复系统管理“用户信息管理”列表中的存储用量始终显示为 `0 MB`：用户总容量应由其用户目录记录汇总得到。

## 已完成

- 用户存储统计任务继续按 `StorageUsage.user_id` 汇总用户目录的 `used` 值，并保留原有 QuestDB `user_storage_usages` 历史样本写入。
- 同一任务现在把各用户目录的已用容量总和写回 PostgreSQL `User.storage_used`，这是用户列表排序和响应序列化使用的字段。
- 没有有效用户目录的用户被同步为 `0`，避免目录删除后继续显示过期总容量。
- 增加回归覆盖：一个用户多个目录的用量会相加；无目录用户和全量目录为空时都会清零。

## 验证

- RED：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend\test\test_scheduled_user_tasks.py -q --basetemp <writable-temp>`，分别验证“目录求和未回填”和“无目录未清零”失败。
- GREEN：同一命令通过，`14 passed`。
- 编译：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m compileall -q backend\crud\usersCrud.py backend\celery_tasks\tasks\storages.py`，通过。

## 未验证范围和风险

- 未连接真实 PostgreSQL、QuestDB 或存储设备；定时任务会在下一次每小时运行后刷新现有用户列表值。
- 未执行浏览器端到端验证；接口的 `capacity.storage_used` 显示单位契约未改变。
- 扩展运行 `backend/test/test_core_api.py` 时有 4 项当前工作区的无关失败（重复集群、Qtree 排序、资源列表计数），不属于本任务改动；未修改或提交这些并发工作区变更。
