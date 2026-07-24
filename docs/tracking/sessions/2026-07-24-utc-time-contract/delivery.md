# UTC 时间契约整改交付

## 范围

- 统一 PostgreSQL 业务瞬时为 `UTCDateTime`，QuestDB 保持受控的 UTC-naive 驱动表示。
- 新增用户 IANA 时区资料接口、前端时区初始化/设置和统一展示工具。
- 范围查询在前端转换为 UTC `Z`，后端拒绝无时区查询边界。
- 将存储使用 XLSX/PDF 导出固定为读取当前认证用户的已保存时区。
- 新增 025 Alembic 迁移、时间契约文档和静态/聚焦测试。

## 验证

- 后端聚焦：`test_storage_health_analytics.py`、`test_questdb_time_contract_guard.py`、`test_datetime_utils.py`、`test_utc_time_contract.py`、`test_auth_api.py`、`test_storage_soft_quota.py`，143 passed。
- 必跑 QuestDB 契约：`test_questdb_time_contract_guard.py test_datetime_utils.py`，18 passed；`alembic heads` 为单一 `000000000025`。
- 前端聚焦：日期工具、范围组件、审计、趋势、预测和 AI 页面，45 passed。
- 前端：本次变更文件 ESLint 通过，`npm run build:test` 通过。全量 `npm run lint` 仍被未触及的 `IncidentAiSettingsDialog.vue:28` 既有格式问题阻断。

## 未执行/风险

- 未清空或重建任何开发数据库，也未启动外部 PostgreSQL/QuestDB/Celery；开发切换须由环境责任人按时间契约文档执行。
- 未完成真实 PostgreSQL/QuestDB 集成环境的首批跨库写入比对。
- 后端全量历史测试仍有使用 naive 时间夹具的契约漂移，记录见本会话错误日志；当前改动范围内的聚焦测试已更新并通过。
