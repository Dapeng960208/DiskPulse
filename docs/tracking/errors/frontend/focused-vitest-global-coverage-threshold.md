# 聚焦 Vitest 覆盖率套用全局阈值

## 错误内容

仅运行一个前端测试文件并启用 `--coverage` 时，Vitest 仍按全量 `src/` 文件计算全局覆盖率。聚焦用例全部通过且目标页面 Statements、Lines 和 Functions 均超过 80%，但大量未由该测试加载的文件以 0% 计入汇总，最终因全局 Statements、Branches、Functions 和 Lines 阈值不足而以状态码 1 退出。

## 解决方案

日常聚焦回归按前端规范使用 `--coverage.enabled=false`；需要验证仓库全局 80% 门禁时运行完整的 `pnpm run test:coverage`。不得把单文件覆盖率命令的全局汇总结果误认为目标页面测试失败。

## 备注

- 分类：`frontend`
- 出现次数：1
- 首次出现：2026-07-23 存储集群详情表格样式会话
- 最近出现：2026-07-23 存储集群详情表格样式会话
- 出现记录：`sessions/2026-07-23-storage-cluster-table-style/errors.md`
