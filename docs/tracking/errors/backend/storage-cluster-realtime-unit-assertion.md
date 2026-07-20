# 存储集群实时趋势测试仍按 GB 断言

## 错误内容

`backend/test/test_core_api.py::TestCoreApi::test_storage_cluster_crud_and_realtime_contract` mock 了 GB 原始值 `200`，但 `GET /storage-clusters/{id}/realtime` 按容量单位契约将存储集群趋势转换为 TB，实际返回 `0.1953`。测试仍断言 GB 原始值，导致核心 API 文件的该用例失败。

## 解决方案

在单独的趋势契约修复中，将测试预期与 `data_unit="TB"` 的接口契约对齐，并同时核对同类实时趋势断言。本会话只新增列表利用率筛选，不修改趋势行为或该既有测试。

## 备注

- 首次出现：2026-07-20，`2026-07-20-storage-utilization-range-query` 会话。
- 最近出现：2026-07-20；出现次数：3。
- 差异：首次仅触及分页列表查询；本次扩展到容量集合筛选。两次均未修改 `storage_cluster` 实时趋势函数，基线已使用单位换算。
- 出现记录：`sessions/2026-07-20-recent-code-review-remediation/errors.md`；近三日审查确认接口继续返回 `data_unit="TB"` 和 `0.1953`，已将核心 API 测试与权威单位契约对齐。
