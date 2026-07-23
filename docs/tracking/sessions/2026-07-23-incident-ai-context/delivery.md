# 交付记录

## 改动

- 性能争用事件的 AI 快照新增当前事件资源近 24 小时的 UTC 小时聚合：读/写/总延迟、IOPS、吞吐、每桶采样数、指标汇总和缺失小时数。
- 查询固定为当前事件的集群、资产类型、资产 ID 和最近证据时间窗；模型不接收通用聊天工具。
- 无样本、资产身份不完整和 QuestDB 查询失败会写为安全的数据缺口，不把缺失数据解释为正常。
- 非性能路径仅附带脱敏来源数、观测时间和数据缺口；提示词禁止模型编造未提供的 CPU、内存、进程、网络或业务请求检查。
- AI 输入进一步剔除了事件类别、确定性严重程度、诊断候选/分数/置信度、MAD 等鲁棒统计、旧异常触发摘要和证据类型；服务端内部仍可据此选择受限取数路径，但不将该选择标签发送给模型。

## 验证

- `cd backend; ..\\.venv\\Scripts\\python.exe -m pytest test\\test_incident_ai_agent.py test\\test_forecast_incident_center.py test\\test_storage_health_analytics.py -q`：165 passed。
- `cd backend; ..\\.venv\\Scripts\\python.exe -m pytest test\\test_questdb_time_contract_guard.py test\\test_datetime_utils.py -q`：15 passed。

## 未验证范围与风险

- 未连接真实 QuestDB 或真实模型执行端到端审查；部署后需确认不同厂商的 `object_type`/`object_id` 映射是否与 Incident 资产一致。
