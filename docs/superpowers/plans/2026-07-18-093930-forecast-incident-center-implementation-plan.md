# 预测、RCA 与事件中心实施计划

- 审批时间：2026-07-18
- 设计依据：[预测、RCA 与事件中心设计](../specs/2026-07-18-forecast-incident-center-design.md)
- 范围：只读分析、事件管理、通知与 AI 诊断说明；不建设模型网关、RAG、CMDB 或设备写操作。

## 实施顺序

1. 先添加 `backend/test/test_forecast_incident_center.py` 与前端 Incident 中心测试，覆盖数据不足、陈旧遥测、孤立尖峰、跨项目拒绝、状态机、去重/重开、维护窗口、通知受众和 AI 受限输出，并运行获得 RED。
2. 新增 `000000000010_forecast_incidents` 迁移、模型、schema、CRUD 和服务；以组合索引保证项目过滤、时间排序、资产检索与证据幂等。
3. 实现质量快照、Theil-Sen P10/P50/P90 容量预测、MAD 性能异常、证据关联、事件归并、维护/静默、确定性 RCA 与默认禁用的工作负载适配契约。
4. 注册 Celery 调度与采集完成钩子；新增 v1 路由并复用项目授权、统一审计和既有通知设施。
5. 增加事件中心与集群详情关联事件页签，保持告警和厂商系统事件页面语义不变；同步文档、配置样例和交付跟踪。

## 固定契约

- 预测返回 30 天曲线及 `exhaustion_dates.p10/p50/p90`；少于 30 个有效日或覆盖率低于 80% 只返回数据缺口。
- 异常基线为过去 28 天相同星期/小时的中位数和 MAD，绝对鲁棒 Z 分数至少 3.5 且连续三点；同一证据 `(source, source_ref)` 全局唯一。
- Incident 状态只允许 `open → acknowledged → investigating → mitigated → resolved`；同键 resolved 事件 24 小时内自动重开。
- API 位于 `/storage-pulse/api/v1`，列表先授权过滤后数据库分页且 `size <= 100`；新增 `forecasts`、`anomalies`、`incidents`、诊断、评论及维护窗口资源。
- Incident 通知默认管理员；其余受众和邮件/飞书通道由 `incident_notifications` 配置启用。维护和静默不改动原始告警。

## 完成检查

- RED/GREEN 分别建立当前分支可达的 checkpoint commit。
- 运行聚焦 pytest、Alembic upgrade、聚焦 Vitest、前端构建和固定历史回放；真实 NetApp/PowerScale 只读回放作为独立环境验收并在跟踪文档中说明结果。
