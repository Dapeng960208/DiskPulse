# 存储资源利用率区间查询交付

## 范围

为所有返回当前存储容量对象集合的查询增加 `use_ratio_min` 和 `use_ratio_max` 参数；不改变单资源详情、时序趋势、汇总指标、遥测记录、预测或配额写入接口。

## 已完成

- 存储集群、容量池、存储空间、Qtree、项目组、用户目录和项目列表支持 0--100 的闭区间利用率筛选。
- 用户目录 PDF/Excel 导出、Dashboard 容量项、容量池存储树、项目容量汇总/分布/存储树及存储告警也支持该筛选；告警使用 `avg_use_ratio`，其他接口使用当前对象 `use_ratio`。
- 树形响应按命中节点裁剪，并为命中后代保留必要的父级路径；父级仅作结构上下文时可能不在区间内。
- 两个边界同时提供且最小值大于最大值时返回 `422`；边界值越界由 FastAPI 查询参数校验拒绝。
- 筛选在 CRUD 查询层通过 SQLAlchemy 条件与既有权限、资源归属、名称筛选、排序和分页组合；树查询在构造响应后按相同区间语义裁剪。

## 验证

- RED：`backend/test/test_core_api.py -k "all_capacity_collections or storage_usage_export_passes"` 在实现前执行，仪表盘未过滤、导出未传递区间、反向区间未拒绝，按预期失败。
- GREEN：`./.venv/Scripts/python.exe -m pytest backend/test/test_core_api.py -k "all_capacity_collections or storage_usage_export_passes" --basetemp <temp>/pytest-capacity-range-final -q` 通过（`4 passed, 23 deselected`）。
- `./.venv/Scripts/python.exe -m compileall -q backend` 通过。
- 完整 `backend/test/test_core_api.py`：`25 passed, 1 failed`；失败为既有的存储集群实时趋势 TB/GB 断言不一致，见本会话 `errors.md`。
- `backend/test/test_dashboard_overview.py`：`7 passed`。
- `backend/test/test_project_scope_authorization.py`：`7 passed, 1 failed`；失败为既有的项目负责人配额能力不一致，见本会话 `errors.md`。

## 未验证范围和风险

- 未执行全量后端测试、真实 PostgreSQL 和真实存储设备验证；本次仅新增当前态关系数据库容量集合筛选，不涉及设备调用或时序数据。
