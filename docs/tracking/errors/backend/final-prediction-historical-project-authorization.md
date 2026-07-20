# 最终预测使用历史项目快照授权

## 错误内容

最终预测列表只按 `capacity_forecasts.project_id` 过滤。资源迁移项目后，旧项目成员在下一次预测生成前仍能看到预测；资源删除后还会出现幽灵结果。

## 解决方案

在 `count` 和数据库分页前反查当前 `Group` 或 `StorageUsage → Group` 归属并排除删除资源。历史 `asset_id` 先通过受保护的整数转换处理，避免异常值导致 PostgreSQL 整页查询失败。

## 备注

- 分类：`backend`
- 出现次数：1
- 首次与最近出现：2026-07-19 导航信息架构会话
- 出现记录：`sessions/2026-07-20-navigation-information-architecture/errors.md`
