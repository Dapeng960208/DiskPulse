# 已审核厂商事件测试夹具缺少必填处置方案

## 错误内容

`test_incident_vendor_semantics_contract.py` 中两个已审核厂商事件定义夹具没有填写 `recommended_solution_zh`。当前数据库约束 `ck_vendor_event_definition_reviewed_evidence` 要求已审核定义同时具备官方链接、版本范围和非空处置方案，因此测试在提交夹具时失败，尚未进入事件详情断言。

## 解决方案

更新该测试的已审核定义工厂或具体夹具，为 `review_status="reviewed"` 的记录补充可核验的 `recommended_solution_zh`；待审核记录继续保持空值。修复应归属厂商事件目录契约测试，不应通过放宽数据库约束绕过。

## 备注

- 分类：`backend`
- 出现次数：2
- 首次出现：2026-07-23 性能证据详情会话
- 出现记录：`sessions/2026-07-23-performance-evidence-detail/errors.md`
- 最近出现：2026-07-24，`2026-07-24-router-transactions-startup-security`：全量后端测试中两个事件详情夹具再次缺少 `recommended_solution_zh`；已为 NetApp 和 Dell 已审核记录补齐处置方案。
