# 项目组额度与实时趋势修复交付记录

## 范围

- 项目详情“项目组”页签额度与使用率展示。
- 项目组详情容量趋势工作区高度回归。
- 存储目标文案简化确认。

## 进度

已完成：项目组额度列、实时趋势高度链和存储目标文案简化已实现并完成交付验证。

## 验证

- RED：`pnpm exec vitest run test/unit/project-context-tabs.test.js test/unit/realtime-page-height-contract.test.js --coverage.enabled=false`，2 个目标用例按预期失败。
- GREEN：同一命令通过，2 个测试文件、9 个用例全部成功。
- 相关门禁：7 个测试文件、47 个用例全部成功。
- ESLint：3 个改动 Vue 文件通过。
- 前端测试构建：`pnpm run build:test` 成功；保留现有大 chunk 警告。

## 未验证范围与风险

- 未进行真实浏览器和真实后端数据联调；高度修复以自动化布局契约和构建结果验证。
