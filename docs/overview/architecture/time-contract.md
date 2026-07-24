# UTC 时间契约

## 目标

自 2026-07-24 UTC 整改起，新写入的业务“瞬时”只有一个语义：UTC 时间线上的确定时刻。历史数据不在本契约的修复范围内；开发库必须在切换前清空并重建，非开发环境需要独立的停写、备份、逐表校验和回滚方案。

## 存储边界

| 边界 | 表示 | 规则 |
| --- | --- | --- |
| PostgreSQL | `UTCDateTime` / `TIMESTAMP WITH TIME ZONE` | 只绑定 aware datetime；模型在绑定时归一化为 aware UTC，naive 输入失败。 |
| QuestDB designated timestamp | 驱动要求的 UTC-naive datetime | 业务代码只能调用 `questdb_write_timestamp(<table>, value)`；该函数只接收 aware UTC，最后一刻才移除 `tzinfo`。 |
| QuestDB 读取 | aware UTC datetime | 先调用 `from_questdb_utc()` 将驱动返回的 naive 值按 UTC 解释。 |

`utc_now()` 是持久化业务时间的唯一时钟入口。厂商提供无时区墙上时间时，必须调用 `parse_source_datetime(value, source_time_zone)` 并声明来源 IANA 时区；不得猜测或按服务器本地时区解释。

## API 与查询边界

- API 响应中的瞬时统一序列化为 RFC 3339 UTC `Z`，例如 `2026-07-24T06:30:00Z`。
- 范围查询参数必须带 `Z` 或数字 UTC offset；无时区值由全局请求依赖以 `422` 拒绝。
- 业务、CRUD 和 API 层都不得将 QuestDB 时间固定转换成 `Asia/Shanghai`。

## 用户展示与导出

用户的可空 `users.time_zone` 保存经后端 `zoneinfo.ZoneInfo` 校验的 IANA 标识。首次登录仅在其值为空时读取浏览器 IANA 时区并保存；浏览器无法提供合法值时使用 `Asia/Shanghai`，以后不自动覆盖用户选择。

前端通过 `frontend/src/stores/current-user.js` 和 `frontend/src/utils/datetime.js` 维护当前展示时区：页面、图表 Tooltip、审计和预测时间都传入该时区格式化。范围组件的墙上时间经 `toUtcRange()` 转为 `Z` 后请求 API。用户主动导出不信任客户端时区参数，服务端从当前认证用户的 `time_zone` 格式化 XLSX/PDF 内容、页脚和文件名。

## 开发切换与门禁

1. 停止开发 API、Celery、采集任务及所有 QuestDB 写入者。
2. 明确目标为开发配置后，清空 PostgreSQL 与 QuestDB 开发数据，重建 schema、执行 Alembic 和 QuestDB 迁移。
3. 启动服务和采集器，比较首批两库记录的 epoch 或 UTC ISO 值，确认表达同一瞬时。
4. 不得把此清空步骤用于非开发环境。

静态/契约测试禁止 `UTCDateTime` 业务列退回普通 `DateTime`、QuestDB 业务写入绕过 `questdb_write_timestamp()`，并覆盖 aware UTC 写入、QuestDB 往返、无时区查询拒绝、用户时区资料和跨方言迁移编译。
