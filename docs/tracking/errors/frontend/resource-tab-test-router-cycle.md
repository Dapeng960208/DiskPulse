# 资源表单测触发请求层与路由循环依赖

## 错误内容

直接挂载集群详情资源表组件时，`Progress.vue` 会加载告警阈值 Store，进而经配置 API、请求构建器和路由导入用户 API，测试环境中出现 `Class extends value undefined is not a constructor or null`。

## 解决方案

资源表单元测试显式 Mock `Progress.vue` 和 `AccessibleResourceLink.vue`，隔离容量展示与资源链接的外部依赖；组件自身的集群筛选、分页和失败态使用 API Mock 验证。该处理不改变生产请求层或路由初始化顺序。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次出现：2026-07-20 集群详情资源页签会话
- 最近出现：2026-07-20 集群详情资源页签会话
- 出现记录：`sessions/2026-07-20-cluster-detail-resources/errors.md`
