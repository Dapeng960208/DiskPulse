# 存储集群实时趋势测试仍按 GB 断言

## 错误内容

`backend/test/test_core_api.py::TestCoreApi::test_storage_cluster_crud_and_realtime_contract` mock 了 GB 原始值 `200`，但 `GET /storage-clusters/{id}/realtime` 按容量单位契约将存储集群趋势转换为 TB，实际返回 `0.1953`。测试仍断言 GB 原始值，导致核心 API 文件的该用例失败。

## 解决方案

在单独的趋势契约修复中，将测试预期与 `data_unit="TB"` 的接口契约对齐，并同时核对同类实时趋势断言。本会话只新增列表利用率筛选，不修改趋势行为或该既有测试。

## 备注

- 首次出现：2026-07-20，`2026-07-20-storage-utilization-range-query` 会话。
- 最近出现：2026-07-20；出现次数：1。
- 差异：本次改动仅触及分页列表查询；`storage_cluster` 实时趋势函数在基线提交中已使用单位换算。
