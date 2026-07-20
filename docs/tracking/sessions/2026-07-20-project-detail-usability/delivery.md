# 项目详情可用性修复交付

## 范围

- 项目详情的存储分布、项目组、用户目录、成员与权限和项目级详情面包屑。
- 保留项目列表中的“项目存储概览图”，不删除既有列表字段。

## 当前状态

已完成：项目详情可用性修复已在独立分支实现、验证并记录。

## 已完成

- 项目详情保留“项目使用实时”并新增“存储分布”；项目列表的“项目存储概览图”未删除。
- 存储分布不提供筛选项，固定按项目组 → 用户读取当前数据库使用量；项目使用实时与存储分布图表均撑满其页签可用内容高度。
- 项目组、用户目录、成员与权限增加项目范围筛选；用户目录保留原列表关键字段并补齐项目组标签、软限额和软限额使用率。
- 用户目录隐藏“项目”和“存储类型”列；研发用户名仅对离职用户显示用户类型标识。
- 项目、项目组和用户目录详情写入项目层级动态面包屑。

## 验证

- 前端聚焦基线：16 项通过，1 项因 Windows CRLF 与静态测试 LF 断言不一致失败；已在本会话用跨平台断言修复。
- `cd frontend && npx vitest run test/unit/project-context-tabs.test.js test/unit/project-disk-usage.test.js test/unit/project-storage-distribution.test.js test/unit/project-members-tab.test.js test/unit/project-detail-breadcrumbs.test.js test/unit/utils/breadcrumbs.test.js test/unit/stores/breadcrumbs.test.js test/unit/chart-coverage-gaps.test.js test/unit/mock-runtime.test.js --coverage.enabled=false`：9 文件、50 项通过。
- `cd frontend && npx vitest run test/unit/project-context-tabs.test.js --coverage.enabled=false`：8 项通过（用户目录展示收敛）。
- `cd frontend && npm run lint`：通过。
- `cd frontend && npm run build:prod`：通过；保留既有的 Vite 标题变量和大 bundle 提示。
- 本地 Mock 浏览器验收：项目详情的实时使用量与存储分布均可见；存储分布无筛选项、按项目组 → 用户展示。浏览器实测存储分布页签与卡片高度均为 746.4px；实时使用量的趋势与告警列高度均为 411.1px，未出现控制台错误。

## 未验证范围与风险

- 未运行前端全量测试和覆盖率门禁；本次只执行受影响的聚焦用例。
- 浏览器验收使用本地 Mock 数据；未对真实后端数据源进行端到端验收。
