# Celery 控制命令没有收到节点回复

## 错误内容

维护窗口前执行 `celery inspect active/reserved/scheduled --timeout=5` 均返回 `No nodes replied within time constraint`。该结果不能证明 Worker 已停止；同一时间本地 Beat/Worker 进程仍存在并继续向 QuestDB 写入。

## 解决方案

把控制面探测视为辅助信号。控制命令无回复时，按仓库虚拟环境可执行文件、`-A celery_worker:diskpulse_app` 启动参数和父子进程树确认目标进程；停止后再用两次间隔审计验证 QuestDB 行数与最大时间静止，只有两项都满足才允许执行表换名。

## 备注

- 首次出现：2026-07-23，`2026-07-23-questdb-utc-time-contract`。
- 最近出现：2026-07-23，`2026-07-23-questdb-utc-time-contract`。
- 出现次数：1。
