# 开发跟踪记录：厂商事件时间关联补充

- 会话：`2026-07-22-event-time-association`
- 状态：修复后待 PostgreSQL 复验
- 范围：补充 Dell PowerScale 事件清单对应的事件候选定义、时间关联建议与边界说明。

## 已完成

- 在厂商事件关联事实文档中新增时间标签、默认窗口、关联键和缺失事件边界。
- 明确时间标签属于 DiskPulse 操作性元数据，不改变 PowerScale `pending` 定义的审核状态。
- 保留 Dell 官方 SRS Brevity URL 作为外部依据，并说明逐代码语义仍需 OneFS 运行时或版本化官方手册核验。
- 当时在迁移 `000000000018` 中补充 15 条 SRS Brevity 候选定义，保存中文摘要和官方链接，统一保持 `unknown + pending`；这些数据后续已迁移到独立初始化目录。
- 通过内置浏览器读取 Dell Table 11 的 150 条记录，并将其中尚未在目录出现的 131 条作为知识储备录入当时的迁移；这些数据后续已并入独立初始化目录。
- 读取《PowerScale OneFS Event Reference Guide》（2021 年 10 月）最后两章，对全部 499 条软件与硬件事件提取标题、说明和管理员操作，翻译为中文并升级为 `reviewed`；SRS 表格中未出现在该版指南的 15 条代码继续保持 `pending`。
- 读取 NetApp《raid events : ONTAP EMS reference》，按 `WARNING` 及以上门槛筛选并翻译 152 条 RAID 事件的 Description 与 Corrective Action；实际分布为 `ERROR=104`、`ALERT=31`、`EMERGENCY=17`，文档中没有 `WARNING` 条目。

## 验证状态

- 已检查新增段落与现有 `Asia/Shanghai`/UTC 时间口径、去重和 Incident 门禁无冲突。
- 已执行 Markdown 链接与差异空白检查（见最终交付说明）。
- 隔离 SQLite 的迁移链、升级/降级、事件关联契约和管理接口聚焦测试曾有 44 项通过；真实 PostgreSQL 首次执行 `000000000018` 时因 `vendor_event_definitions.id` 序列落后而事务回滚，不能据此宣称业务库已达到 543 条 `reviewed`、42 条 `pending`。
- 已为 PostgreSQL 序列同步补充回归测试并修复迁移；仍需重新执行 `alembic -c alembic.ini upgrade head` 并回读统计后才能恢复“已交付”状态。
- 加入 NetApp RAID 定义后，迁移目标为 730 条目录，其中 688 条 `reviewed`、42 条 `pending`；该统计仍需真实 PostgreSQL 迁移成功后回读确认。

## 风险

- 本轮新增事件目录数据迁移并更新文档，未修改时间关联运行时代码或数据库表结构；时间窗口值仍需实现时通过目标 OneFS 版本和采集周期验收。
- 自动化迁移使用隔离 SQLite 数据库验证；未对真实 PostgreSQL 业务库执行迁移，目标设备版本差异仍需部署环境验收。

## 后续处置

2026-07-23 已将全部目录数据移出 Alembic revision，并通过独立初始化入口在 PostgreSQL 测试库从空目录写入 730 条、幂等复跑新增 0 条；详见[厂商事件目录独立初始化交付](../2026-07-23-vendor-event-definition-initialization/delivery.md)。本会话保留当时的失败与风险记录，不再作为当前部署方式。
