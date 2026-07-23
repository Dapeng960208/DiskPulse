# 全局页面表格样式审计交付

## 范围

- 扫描 `frontend/src/pages/` 中直接使用 Element Plus 表格、分页及页面级深层表格样式的实现。
- 按页面或组件分别通过 TDD 接入共享 `DataTable`，不扩大业务行为、权限或接口边界。
- 同步受影响功能事实文档、页面级会话记录和全局架构测试。

## 页面与提交

| 页面或组件 | RED 提交 | GREEN 提交 |
| --- | --- | --- |
| `ForecastGovernancePage.vue` | `7f376b5` | `62762e4` |
| `RealTimePage.vue` | `1537e0c` | `9b4fcd2` |
| `ClusterIncidentsTab.vue` | `4ecae71` | `90cf592` |
| `ClusterResourceListTab.vue` | `39e755e` | `7074012` |
| `CapacityPredictionPanel.vue` | `2a86dc9` | `8b7bc44` |
| `AiCenterPage.vue` | `7bb5209` | `a6a7547` |

全局扫描门禁与迁移后的测试同步提交为 `398a319`、`df5d427`。

## 已完成

- 上述六个页面或组件中的查询、加载、分页或动态数据表均改为共享 `DataTable`。
- 审计完成后扫描 `frontend/src/pages/`，未发现直接 `<ElTable>`、直接 `<ElPagination>`，也未发现页面级 `:deep(.el-table)`、`:deep(.el-pagination)` 或 `:deep(.table-wrapper)` 覆盖。
- 各页面保留原有数据、权限、加载、分页和响应式业务边界；页面局部样式不再复制共享表格视觉规则。
- 三条表格迁移后过时的旧测试断言已同步修复，相关聚焦测试 22 项全部通过。

## 验证

- 六个页面或组件的 RED 用例均先按预期失败，GREEN 后各自聚焦测试均通过。
- 目标 ESLint 检查均为 `0 errors`；宽测试文件保留 21 条既有 `vue/one-component-per-file` 警告。
- `pnpm run build:prod`：通过；保留既有单个 chunk 大于 `500 kB` 的构建警告。
- 全局源码扫描：
  - `rg -n '<ElTable\b' frontend/src/pages --glob '*.vue'`：无匹配；
  - `rg -n '<ElPagination\b' frontend/src/pages --glob '*.vue'`：无匹配；
  - 页面级 `el-table`、`el-pagination`、`table-wrapper` 深层覆盖扫描：无匹配。
- 表格迁移测试同步后，对应聚焦测试 22 项通过。

## 全量测试基线

审计期间运行 `pnpm test` 时共有 10 项失败：

- 其中 3 项为本次表格迁移后的旧组件断言，已经修复，并由 22 项聚焦测试验证；
- 剩余 7 项未在本次表格样式范围内处理：
  - 1 项路由数量基线断言；
  - 4 项 `list-action-permissions` 断言；
  - 2 项来自用户当前未提交的 `StorageClusterDetailPage.vue` 列宽与响应式类修改。

该全量基线失败已归入[前端全量与覆盖率曾保留既有失败](../../errors/frontend/baseline-test-debt.md)。

## 未验证范围与风险

- 未执行真实浏览器、窄屏交互或部署环境验收。
- 未执行全量覆盖率门禁。
- 未重新确认修复三条表格旧断言后的全量 `pnpm test` 结果；上述 7 项剩余失败仍需由各自主题处理。
- 生产构建的大 chunk 警告为既有风险，本次未调整拆包策略。
