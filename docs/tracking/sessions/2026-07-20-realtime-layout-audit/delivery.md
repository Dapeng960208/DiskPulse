# 实时页面布局复查交付记录

## 范围

- 静态枚举全站 `RealTimePage` 调用方，复查实时趋势、告警表与应用内容区/页脚的高度边界。
- 修复项目列表“项目存储概览图”、项目组详情、容量池详情和 Qtree 详情中缺失的受限填充高度契约。
- 修复项目列表页签自身缺失的可收缩 flex 高度链。

## 完成项

- `ProjectDiskUsage.vue` 始终启用 `fillContent`，使未选择具体项目的项目存储概览图也受内容区约束。
- `ProjectListPage.vue` 的标签页内容和页签面板建立 `flex: 1` 与 `min-height: 0` 高度链。
- 项目组详情、容量池详情、Qtree 详情向 `RealTimePage` 传递 `fillContent`；项目组详情补足外层可收缩 flex 容器。
- 新增静态回归合同，覆盖五个 `RealTimePage` 调用方与项目列表页签高度链；既有用户目录和项目详情合同继续覆盖已修复页面。

## 验证

- RED：新增实时页面高度合同首先因项目概览未启用 `fillContent` 失败；补充项目列表页签高度断言后再次因缺少可收缩高度链失败。
- GREEN：`npx vitest run test/unit/realtime-page-height-contract.test.js test/unit/project-disk-usage.test.js test/unit/usage-detail-realtime-layout.test.js test/unit/project-detail-table-scroll.test.js --coverage.enabled=false`，4 个文件、5 个测试通过。
- `npx eslint` 已检查本次涉及的页面与回归测试；`npm run build:prod` 生产构建通过。
- 浏览器：Mock 模式抽查 `/projects` 并切换“项目存储概览图”，以及 `/group/1`、`/admin/aggregate/1`、`/admin/qtree/1`；目标内容都停留在页脚上方，未出现框架错误覆盖层。

## 未验证范围与风险

- Mock 的项目组接口返回“没有权限”提示，项目组页面仅验证到布局容器而非真实授权数据；容量池与 Qtree 使用 Mock 数据完成渲染验证。
- 全量与覆盖率测试仍存在既有收集阶段失败，详见 [错误记录](./errors.md)；本次使用聚焦测试、lint、生产构建和浏览器抽查确认布局变更。
