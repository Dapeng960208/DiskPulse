# 项目详情可用性修复交付

## 范围

- 项目详情的存储分布、项目组、用户目录、成员与权限和项目级详情面包屑。
- 保留项目列表中的“项目存储概览图”，不删除既有列表字段。

## 当前状态

进行中：已完成 TDD RED/GREEN、实现和事实文档同步，待静态检查、构建与浏览器验收。

## 已完成

- 项目详情将原“容量概览”明确为“存储分布”，项目列表的“项目存储概览图”未删除。
- 项目组、用户目录、成员与权限增加项目范围筛选；用户目录保留原列表关键字段并补齐项目组标签、软限额和软限额使用率。
- 项目、项目组和用户目录详情写入项目层级动态面包屑。

## 验证

- 前端聚焦基线：16 项通过，1 项因 Windows CRLF 与静态测试 LF 断言不一致失败；已在本会话用跨平台断言修复。
- `cd frontend && npx vitest run test/unit/project-context-tabs.test.js test/unit/project-disk-usage.test.js test/unit/project-members-tab.test.js test/unit/project-detail-breadcrumbs.test.js test/unit/utils/breadcrumbs.test.js test/unit/stores/breadcrumbs.test.js --coverage.enabled=false`：6 文件、22 项通过。

## 未验证范围与风险

- 尚未完成浏览器验收、lint、构建及覆盖率验证。
