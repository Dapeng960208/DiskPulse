# 实时监控告警表格样式交付

## 范围

- 将实时监控页的异步告警表接入共享 `DataTable`。
- 移除页面级 Element Plus 表格深层样式和内联尺寸。
- 保留告警数据、加载状态、紧凑密度和固定高度容器内滚动。

## 已完成

- 告警表由共享 `DataTable` 统一提供卡片、表格、加载和空态样式，不再嵌套额外 `ElCard`。
- 页面自有卡片样式仅作用于资源摘要和趋势图卡片，不覆盖共享表格卡片。
- 新增静态架构回归测试，并同步运行时数据与加载属性断言。
- 同步存储趋势事实文档。

## 验证

- `cd frontend && pnpm exec vitest run test/unit/page-coverage-gaps.test.js --coverage.enabled=false -t "uses one shared data table for async alerts without page-level table styling"`：新增架构门禁 1 项通过。
- `cd frontend && pnpm exec vitest run test/unit/page-coverage-gaps.test.js --coverage.enabled=false -t "real-time page coverage gaps"`：实时监控相关 5 项通过。
- `cd frontend && pnpm exec vitest run test/unit/detail-route-loading.test.js test/unit/storage-resource-terminology.test.js test/unit/project-disk-usage.test.js --coverage.enabled=false`：关联契约 8 项通过。
- `cd frontend && pnpm exec eslint src/pages/common/RealTimePage.vue test/unit/page-coverage-gaps.test.js`：无错误；测试文件保留 18 条既有单文件多组件警告。
- `git diff --check -- frontend/src/pages/common/RealTimePage.vue frontend/test/unit/page-coverage-gaps.test.js docs/features/storage/trends/design.md docs/tracking/sessions/2026-07-23-realtime-table-style/delivery.md docs/tracking/sessions/2026-07-23-realtime-table-style/errors.md`：通过。

## 未验证范围与风险

- 未运行前端全量测试、全量覆盖率、生产构建或真实浏览器窄屏验证；本次以聚焦单元测试和 SFC 编译验证固定高度布局。
- 完整运行 `page-coverage-gaps.test.js` 时，本次实时监控相关用例全部通过，但同文件的存储集群分页旧用例仍因找不到已移除的分页组件失败；该失败不属于本页改动范围。
