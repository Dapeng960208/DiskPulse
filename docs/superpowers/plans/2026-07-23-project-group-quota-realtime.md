# 项目组额度与实时趋势修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐项目内项目组额度信息并恢复项目组详情实时趋势工作区。

**Architecture:** 复用项目内用户目录表格的额度列组件组合，不引入新接口或共享抽象；为项目组容量页签补齐既有 flex 高度链。保留用户已完成的存储目标文案简化。

**Tech Stack:** Vue 3、Element Plus、Vitest、SCSS

---

### Task 1: 建立回归测试

**Files:**
- Modify: `frontend/test/unit/project-context-tabs.test.js`
- Modify: `frontend/test/unit/realtime-page-height-contract.test.js`

- [ ] 为项目组页签断言硬限额、软限额、使用量和两种使用率列，以及容量格式化与空状态。
- [ ] 为项目组容量页签断言独立的 flex class 和完整高度链。
- [ ] 运行两个聚焦测试，确认因缺少目标实现而失败。
- [ ] 提交 RED 检查点。

### Task 2: 最小实现

**Files:**
- Modify: `frontend/src/pages/project/components/ProjectGroupsTab.vue`
- Modify: `frontend/src/pages/group/GroupDetailPage.vue`

- [ ] 复用 `Progress`、`formatQuotaLimit` 和 `canRenderQuotaProgress` 增加五个额度列。
- [ ] 为容量 `ElTabPane` 增加可伸展 class，并补齐 tabs content 与 pane 的 flex 高度样式。
- [ ] 重跑相同聚焦测试，确认转为 GREEN。

### Task 3: 文档、验证与提交

**Files:**
- Modify: `docs/features/identity/project-rbac/frontend.md`
- Modify: `docs/tracking/errors/frontend/project-realtime-tab-content-height.md`
- Modify: `docs/tracking/errors/error-index.md`
- Create: `docs/tracking/sessions/2026-07-23-project-group-quota-realtime/delivery.md`
- Create: `docs/tracking/sessions/2026-07-23-project-group-quota-realtime/errors.md`

- [ ] 同步项目组额度列和高度修复事实。
- [ ] 将同类高度链错误出现次数加一并更新会话记录。
- [ ] 运行聚焦测试、相关静态门禁、lint 和 `git diff --check`。
- [ ] 只暂存本任务文件，检查 staged diff 后提交 GREEN 检查点。
