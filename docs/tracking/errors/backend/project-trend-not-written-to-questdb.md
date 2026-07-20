# 项目趋势未写入 QuestDB

## 错误内容

项目容量详情读取 `project_storage_usages`，但容量采集只写入项目组、用户目录、存储资源和存储集群时序数据。项目汇总只更新 PostgreSQL 的 `projects` 表，导致项目时序表始终为空，页面没有趋势点。

## 解决方案

在所有存储集群成功采集且 PostgreSQL 项目汇总事务提交后，将已刷新的项目汇总写入 QuestDB `project_storage_usages`。不得在单个集群写入阶段写项目指标，避免跨集群项目出现旧值或部分结果。

## 备注

- 会话：`2026-07-20-project-capacity-trend-write`。
- 首次出现：2026-07-20；最近出现：2026-07-20；出现次数：1。
