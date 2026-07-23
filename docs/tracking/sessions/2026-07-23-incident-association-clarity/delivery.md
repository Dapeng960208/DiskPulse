# Incident 关联信息清晰化交付记录

## 范围

- 明确 Incident 详情抽屉的事件主题。
- 修复性能异常证据被展示为“其他关联依据”的服务端映射缺口。
- 明确每条证据的关联类型和实际关联内容。

## 已完成

- 性能 Incident 标题显示“性能异常 #编号”，并展示“性能异常 · 受影响对象”主题。
- 容量类、性能类、监控类和厂商事件使用明确的关联类型文案。
- `anomaly_observation / continuous_performance_anomaly` 返回“性能异常 / 持续性能异常”和具体核查内容。
- 只有已确认 `fault_log` 的厂商证据显示“系统故障事件”；未分类严重事件保持“设备健康风险”。
- 证据卡片将“异常说明”调整为“关联内容”，新增“关联类型”字段。
- 历史时间线中的泛化“关联事件证据”改为按当前主题说明，并引导查看上方具体证据。

## 验证

- `cd backend && ..\.venv\Scripts\python.exe -m pytest test\test_incident_evidence_presentation.py -q`
- `cd frontend && pnpm exec vitest run test/unit/IncidentDetailDrawer.test.js --coverage.enabled=false`
- `cd frontend && pnpm exec eslint src/pages/incident/components/IncidentDetailDrawer.vue`
- `cd frontend && pnpm run build:test`
- `git diff --check`
- 本地浏览器 `http://localhost:5173/admin/storage-cluster/2`：Incident #615 标题为“性能异常 #615”，主题、4 条性能证据、关联类型、关联内容和历史时间线兼容文案均符合预期，未再出现“其他关联依据”或“关联关联事件证据”。

## 未验证范围和风险

- 尚未执行全量前后端测试。
- 尚未执行真实 NetApp/PowerScale 数据与部署环境浏览器冒烟。
- Vite 热更新期间复现一次 `CrudApi` 初始化顺序错误；完整刷新后页面恢复，见本会话错误记录。
