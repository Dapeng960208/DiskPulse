# 2026-07-20 事件中心关联证据可读性

## 范围

- 将 Incident 详情的内部证据标识转换为可处置的关联信息。
- 保留原始证据追溯能力，但不在默认视图暴露内部拼接标识。
- 收紧 Incident 准入，仅保留紧急集群侧事件；原始告警和监控质量记录仍在各自事实页面留存。

## 已实现

- 在 Incident 详情响应中新增证据和时间线的结构化展示字段，不改变既有原始事实字段。
- 监控质量内部引用会生成采集链路、覆盖不足/采集过期结论、影响范围与安全技术追溯号。
- 详情抽屉新增关联概览和分组证据项；技术追溯号默认折叠；时间线显示中文动作、说明与操作人。
- 仅 `critical` 厂商事件、`critical` 原始容量告警、`critical` 性能异常和未来 7 天内的 P90 容量耗尽可创建或重开 Incident；监控质量快照和采集失败不再入队。
- 已更新事件中心专题事实文档、操作指南和产品能力清单，并将本功能的面向用户术语统一为“监控”。

## 验证

- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test/test_incident_evidence_presentation.py --basetemp <worktree-temp>`：3 passed。
- `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test/test_incident_evidence_presentation.py test/test_incident_admission.py test/test_forecast_incident_center.py --basetemp <worktree-temp>`：35 passed；并已对改动的后端模块执行 `compileall`。
- `pnpm exec vitest run test/unit/IncidentDetailDrawer.test.js --coverage.enabled=false`：6 passed。
- `pnpm run lint`：通过。
- `pnpm run build:prod`：通过；仅出现仓库既有的 `%VITE_APP_TITLE%` 未定义和大 chunk 提示。

## 未验证范围与原因

- Browser QA 未执行：Browser Node 运行时在初始化时返回 `agent is not defined`，无法获得目标标签页；依照前端测试流程，未在未获批准的情况下改用外部 Playwright。
- 未执行仓库全量覆盖率门禁：其覆盖范围包含整个 `backend/` 与 `frontend/src/`，不适合作为本次聚焦改动的日常检查；本次新增的后端 API/展示逻辑与前端详情行为均有聚焦回归测试。
