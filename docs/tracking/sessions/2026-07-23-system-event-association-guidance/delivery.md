# 系统事件关联提示交付记录

## 范围

- 调整存储集群详情“故障分析 → 系统事件”的关联类型展示。
- 保持事件代码与中文含义直接可见。
- 同步健康分析事实文档和聚焦前端测试。

## 已完成

- 关联类型列只展示关联类型，不再重复展示审核状态。
- 关联类型列最小宽度由 `170` 收窄为 `120`。
- 鼠标悬浮关联类型时展示“关联提示”和“采取措施”。
- 待审核或未知定义继续显示“未分类厂商事件”，不输出候选诊断结论。

## 验证

- `cd frontend && pnpm exec vitest run test/unit/pages/storage-cluster-health-analytics.test.js --coverage.enabled=false`
- `cd frontend && pnpm exec eslint src/pages/admin/storage-cluster/StorageClusterDetailPage.vue`
- `cd frontend && pnpm run build:test`
- `git diff --check`
- 本地浏览器 `http://localhost:5173/admin/storage-cluster/2`：系统事件行仅保留一个关联类型标签，事件代码与中文含义可见，列表无审核状态标签，控制台无错误。
- `cd frontend && pnpm exec vitest run test/unit/pages/storage-cluster-health-analytics.test.js --coverage.enabled=true --coverage.include=src/pages/admin/storage-cluster/StorageClusterDetailPage.vue`：17 条用例通过；Statements `96.94%`、Functions `82.22%`、Lines `96.94%`，Branches `69.54%` 未达到全局 `80%` 门禁。
- `cd frontend && pnpm run test:coverage`：未通过；本次聚焦测试通过，但全量门禁存在列表权限源码契约、页面矩阵数量契约和并行收集阶段 `CrudApi` 基类未定义等既有失败。

## 未验证范围和风险

- 尚未执行真实 NetApp/PowerScale 数据与部署环境浏览器冒烟。
- 浏览器自动化鼠标移动未触发展示层；悬浮层内容与结构由组件测试覆盖，仍需人工鼠标悬浮复核视觉位置。
- 全量覆盖率没有产生可接受的最终全局覆盖率结果；失败项与本次改动文件无关，见本会话错误记录。
- 厂商事件说明和建议措施的完整性仍取决于关联目录数据质量。
