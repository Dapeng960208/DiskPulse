# 厂商事件目录独立初始化交付

- 会话：`2026-07-23-vendor-event-definition-initialization`
- 状态：已交付
- 范围：将 NetApp/Isilon 事件目录数据移出 Alembic，提供幂等初始化入口和两份厂商清单。

## 改动

- 汇总测试库与 revision `000000000016` 至 `000000000018` 的目录数据，按 `(storage_type, event_code)` 去重为 730 条。
- 新增统一初始化入口，先升级 Alembic，再在独立事务中只插入缺失定义；现有同键和目录外记录保持不变。
- `000000000016`、`000000000017` 只保留结构变更，`000000000018` 只保留 revision 兼容标记。
- 新增 NetApp ONTAP 199 条、Dell PowerScale（Isilon）531 条 Markdown 精简索引，并通过自动化测试与初始化目录逐字同步。

## 验证

- RED：新测试因初始化模块不存在和迁移仍写入 730 条而失败。
- GREEN：初始化器、结构迁移、目录证据和事件关联契约聚焦测试通过。
- PostgreSQL 测试库执行前为 revision `000000000018`、585 条目录；已导出到仓库外 `C:\Users\guojianpeng\AppData\Local\Temp\diskpulse-vendor-event-association-backups\vendor-event-definitions-before-independent-init-20260723-093036.json`，SHA-256 为 `7fcccf54e655ff215073c5ce57de442d4774390d182e109e85ed5ea4f629c611`。
- 确认没有其他表外键引用后，仅清空 `vendor_event_definitions` 并重置序列；首次统一初始化回报 `matched_existing=0, inserted=730, unmanaged=0`，第二次回报 `matched_existing=730, inserted=0, unmanaged=0`。
- PostgreSQL 回读为 revision `000000000018`、ID `1..730` 且 730 个 ID 唯一；分组为 NetApp `189 reviewed + 10 pending`、Isilon `499 reviewed + 32 pending`。
- 一次内联回读命令从仓库根目录导入 `appConfig` 失败，未执行清表；修正工作目录后重新完整执行空目录初始化。该问题属于无复用价值的命令路径输入错误，不进入全局错误分类库。

## 风险

- 本次只清空 PostgreSQL 测试库的 `vendor_event_definitions`，不会清理其他业务表、QuestDB 或 Redis。
- 真实 NetApp/PowerScale 设备版本和运行时事件目录仍需部署环境验收。
