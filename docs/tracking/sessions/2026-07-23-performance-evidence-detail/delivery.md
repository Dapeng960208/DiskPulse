# 性能证据详情交付记录

## 范围

- 消除事件详情“技术关联信息”与上方关联内容的重复。
- 为性能异常证据补充可核查的指标、时间窗、异常值、基线、正常范围和偏离程度。
- 说明证据标识的用途和原始异常观测回查方法。

## 已完成

- 事件详情按 `anomaly:<id>` 批量读取原始异常观测，避免逐条查询。
- 性能异常证据展示指标与单位、连续异常时间范围、窗口末点 P95、历史基线、正常参考范围及鲁棒 Z 分数。
- 正常参考范围使用与异常判定一致的鲁棒 Z 阈值反推，并对非负指标收敛下界。
- “技术关联信息”只保留证据标识、标识作用和回查方式。
- `anomaly:<id>` 明确说明数字部分对应异常观测 ID，并给出异常观测接口的筛选与精确核对方法。
- 后端和前端均补充回归测试，功能事实文档已同步。

## 验证

- `cd backend && ..\.venv\Scripts\python.exe -m pytest test\test_incident_evidence_presentation.py -q`
- `cd frontend && pnpm exec vitest run test/unit/IncidentDetailDrawer.test.js --coverage.enabled=false`
- `cd backend && ..\.venv\Scripts\python.exe -m pytest test\test_incident_evidence_presentation.py test\test_forecast_incident_center.py test\test_incident_admission.py test\test_incident_capabilities.py test\test_incident_vendor_semantics_contract.py -q`：本次相关 47 项通过；2 项厂商目录测试夹具在数据提交阶段被既有完整性约束拒绝，见本会话错误记录。
- `cd frontend && pnpm exec vitest run test/unit/IncidentDetailDrawer.test.js test/unit/IncidentCenterPage.test.js test/unit/ClusterIncidentsTab.test.js test/unit/incident-and-audit-list-layout.test.js --coverage.enabled=false`：26 项通过。
- `cd frontend && pnpm exec eslint src/pages/incident/components/IncidentDetailDrawer.vue`
- `cd frontend && pnpm run build:test`
- `cd backend && ..\.venv\Scripts\python.exe -m compileall -q crud\forecastIncidentCrud.py routers\forecast_incidents.py schemas\forecastIncidentSchema.py services\forecastIncidentService.py`
- 本地浏览器 `http://localhost:5173/admin/incidents`：性能证据显示 P95 IOPS、异常时间范围、窗口末点 P95、基线、正常参考范围和鲁棒 Z 分数；技术关联区只显示证据标识、标识作用和回查方式；页面控制台无错误。

## 未验证范围和风险

- 当前异常观测保存连续窗口的末点 P95，不包含其余两个窗口的逐点值；页面明确标注“窗口末点 P95”。
- 未执行全量后端和前端测试；扩展后端回归受两个既有厂商目录夹具失败影响，但失败发生在与本次路径无关的测试数据提交阶段。
- 未使用真实 NetApp/PowerScale 与生产 QuestDB 数据验证显示精度和单位。
