# 当前能力

本页是当前可用能力的简要入口，不重复专题中的接口、实现步骤或历史测试结果。

| 能力域 | 当前行为 | 事实来源 |
| --- | --- | --- |
| 存储采集与资源映射 | 统一展示 NetApp 与 PowerScale 的存储资源；系统管理在“存储集群”下组织集群列表、容量池、存储空间和 Qtree（NetApp），集群详情按需展示当前集群的三类资源，其表格正文可滚动且底部分页始终可达，Isilon 不展示 Qtree。 | [存储集群总览](../../features/storage/cluster/overview.md) |
| 性能、事件与健康分析 | 集群详情提供容量、性能、厂商事件、故障分析和导出；无稳定对象映射时不伪造性能数据。 | [健康分析](../../features/storage/cluster/health-analytics.md) |
| 配额与告警 | 支持软限额展示、受控直接配额调整、规则继承和异步告警投递。 | [配额](../../features/storage/quota/overview.md) · [告警规则](../../features/storage/alerts/design.md) |
| 容量趋势与概览 | Dashboard 与资源详情使用统一趋势口径，容量响应携带字段级显示单位；容量池、存储空间、项目、项目组和集群实时容量曲线使用 TB。 | [趋势](../../features/storage/trends/design.md) · [Dashboard](../../features/experience/dashboard/design.md) |
| 认证与用户管理 | LDAP/JWT 认证、人工用户维护和受控 LDAP 同步。 | [认证](../../features/identity/authentication/backend.md) · [用户管理](../../features/identity/user-management/overview.md) |
| 项目隔离与审计 | 项目详情集中展示占满内容区的项目使用实时、基于当前数据库记录的“项目组 → 用户”存储分布、可筛选的项目组和用户目录、成员与权限及审计；项目组页签的右侧操作列仅向超级管理员提供添加和编辑，并仅在服务端授予行级额度能力时提供调整额度。四个数据页签将筛选、可滚动表格和底部分页保持在同一受限内容区，项目概览、项目组、用户目录、容量池和 Qtree 详情的容量趋势也不会侵入页脚。用户目录所属用户自动获得项目只读权限，资源详情保留项目层级面包屑，服务端负责项目隔离、能力字段和追加式统一审计；统一审计可显示资源名称、直接或经资源反查的项目及其关联路径。 | [项目组标签设计](../../features/organization/group-tags/design.md) · [RBAC 与审计](../../features/identity/project-rbac/frontend.md) · [后端边界](../../features/identity/project-rbac/backend.md) |
| 监控与可观测性 | 采集运行账本、新鲜度、健康检查、就绪检查和受令牌保护的指标。 | [监控与可观测性](../../features/storage/observability/overview.md) |
| AI 对话 | 流式对话、受限工具、同参成功结果复用、失败改参恢复、性能/故障分析查询、模型管理、审计及按当前权限恢复历史消息；配额确认的成功、失败和取消结果会随会话历史恢复。 | [AI 对话](../../features/ai/chat/overview.md) |
| 预测与事件中心 | 一级容量预测列表、资源最终预测、异常/RCA、仅紧急集群事件进入的处置队列，以及项目范围访问控制。 | [预测、RCA 与事件中心](../../features/storage/incident-center/overview.md) |
| 前端体验与演示 | 应用壳、统一写入交互、页面级 Mock 演示和角色边界；登录页演示账户入口仅在 Mock 模式提供。 | [应用壳](../../features/experience/application-shell/design.md) · [Mock](../../features/experience/mock-runtime/frontend.md) |
