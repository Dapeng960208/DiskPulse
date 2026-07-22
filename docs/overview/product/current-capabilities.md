# 当前能力

本页是当前可用能力的简要入口，不重复专题中的接口、实现步骤或历史测试结果。

| 能力域 | 当前行为 | 事实来源 |
| --- | --- | --- |
| 存储采集与资源映射 | 统一展示 NetApp 与 PowerScale 的存储资源；系统管理在“存储集群”下组织集群列表、容量池、存储空间和 Qtree（NetApp），集群详情按需展示当前集群的三类资源，其表格正文可滚动且底部分页始终可达，Isilon 不展示 Qtree。存储分页列表、容量树、项目容量汇总/分布、仪表盘容量项、用户目录导出和存储告警均可按利用率区间查询。 | [存储集群总览](../../features/storage/cluster/overview.md) |
| 性能、事件与健康分析 | 集群详情提供容量、性能、厂商事件、故障分析和导出；厂商事件只使用已启用且已审核目录中有官网依据的中文含义与明确类型，待审核项不形成正式语义或重复故障。故障指纹只用于重复归组且可打开具体日志，无稳定对象映射时不伪造性能数据。 | [健康分析](../../features/storage/cluster/health-analytics.md) · [厂商事件关联](../../features/storage/event-association/overview.md) |
| 配额与告警 | 支持软限额展示、受控直接配额调整、规则继承和异步告警投递。 | [配额](../../features/storage/quota/overview.md) · [告警规则](../../features/storage/alerts/design.md) |
| 容量趋势与概览 | Dashboard 与资源详情使用统一趋势口径，容量响应携带字段级显示单位；容量池、存储空间、项目、项目组和集群实时容量曲线使用 TB。 | [趋势](../../features/storage/trends/design.md) · [Dashboard](../../features/experience/dashboard/design.md) |
| 认证与用户管理 | LDAP/JWT 认证、人工用户维护和受控 LDAP 同步。 | [认证](../../features/identity/authentication/backend.md) · [用户管理](../../features/identity/user-management/overview.md) |
| 项目隔离与审计 | 项目详情集中展示占满内容区的项目使用实时、基于当前数据库记录的“项目组 → 用户”存储分布、可筛选的项目组和用户目录、成员与权限及审计；项目组页签的右侧操作列仅向超级管理员提供添加、编辑和额度调整。项目负责人变更会同步授予新负责人项目管理员角色并移除旧负责人该角色；超级管理员还可独立添加项目管理员。项目管理员可查看项目内内容但不能调整项目组额度，项目负责人只能调整其负责项目的用户目录额度。四个数据页签将筛选、可滚动表格和底部分页保持在同一受限内容区，项目概览、项目组、用户目录、容量池和 Qtree 详情的容量趋势也不会侵入页脚。用户目录所属用户自动获得项目只读权限，资源详情保留项目层级面包屑，服务端负责项目隔离、能力字段和追加式统一审计；统一审计以本地可读时间展示事件，明确显示人工接口请求人或系统任务触发方，并展示已采集的执行阶段、关联标识和可读摘要。 | [项目组标签设计](../../features/organization/group-tags/design.md) · [RBAC 与审计](../../features/identity/project-rbac/frontend.md) · [后端边界](../../features/identity/project-rbac/backend.md) |
| 监控与可观测性 | 采集运行账本、新鲜度、健康检查、就绪检查和受令牌保护的指标。 | [监控与可观测性](../../features/storage/observability/overview.md) |
| AI 对话 | 流式对话、受限工具、同参成功结果复用、失败改参恢复、性能/故障分析查询、模型管理、审计及按当前权限恢复历史消息；配额确认的成功、失败和取消结果会随会话历史恢复。 | [AI 对话](../../features/ai/chat/overview.md) |
| 容量耗尽风险与事件中心 | 存储集群、项目、项目组和用户目录在各自详情展示服务端统一判断的 30 日耗尽风险；存储集群仅超级管理员可见，其他维度按项目权限和全局发布开关控制。管理页明确展示内置基线、风险分级及 AI 候选启用标准，并通过 Tooltip 和专题文档解释 Theil-Sen 趋势与残差分位的工作原理。紧急预测可进入事件处置队列，异常与 RCA 继续遵守项目范围。 | [四维容量耗尽风险](../../features/ai/capacity-prediction/overview.md) · [预测、RCA 与事件中心](../../features/storage/incident-center/overview.md) |
| 前端体验与演示 | 应用壳、统一写入交互、页面级 Mock 演示和角色边界；登录页演示账户入口仅在 Mock 模式提供。 | [应用壳](../../features/experience/application-shell/design.md) · [Mock](../../features/experience/mock-runtime/frontend.md) |
