# 存储资源利用率区间查询交付

## 范围

为当前利用率资源的分页查询接口增加 `use_ratio_min` 和 `use_ratio_max` 参数；不改变详情、趋势、分析、导出或配额写入接口。

## 已完成

- 存储集群、容量池、存储空间、Qtree、项目组、用户目录和项目列表支持 0--100 的闭区间利用率筛选。
- 两个边界同时提供且最小值大于最大值时返回 `422`；边界值越界由 FastAPI 查询参数校验拒绝。
- 筛选在 CRUD 查询层通过 SQLAlchemy 条件与既有权限、资源归属、名称筛选、排序和分页组合。

## 验证

- RED：`backend/test/test_core_api.py -k utilization` 在实现前执行，两个新增行为测试按预期失败。
- GREEN：`./.venv/Scripts/python.exe -m pytest backend/test/test_core_api.py -k utilization --basetemp <temp>/pytest-utilization -q` 通过（`3 passed, 20 deselected`）。
- `./.venv/Scripts/python.exe -m compileall -q backend` 通过。
- 完整 `backend/test/test_core_api.py`：`22 passed, 1 failed`；失败为既有的存储集群实时趋势 TB/GB 断言不一致，见本会话 `errors.md`。
- `backend/test/test_project_scope_authorization.py`：`7 passed, 1 failed`；失败为既有的项目负责人配额能力不一致，见本会话 `errors.md`。

## 未验证范围和风险

- 未执行全量后端测试、真实 PostgreSQL 和真实存储设备验证；本次仅新增当前态的关系数据库分页筛选，不涉及设备调用或时序数据。
