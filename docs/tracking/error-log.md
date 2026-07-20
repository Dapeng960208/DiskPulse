# 可复现错误记录

只保留当前环境和项目结构中仍有复用价值的错误模式；已解决的逐次实施记录通过 Git 历史追溯。

| 场景 | 根因与处理 | 风险 |
| --- | --- | --- |
| 最终预测按历史项目快照授权 | 预测生成时的 `capacity_forecasts.project_id` 不是当前授权事实。列表在 `count` 和分页前反查当前 `Group` 或 `StorageUsage → Group` 归属、排除删除资源；异常历史 `asset_id` 先安全转换。 | 真实 PostgreSQL 查询计划和大数据量执行时间仍需隔离环境验证。 |
| 关联事件在预测发布关闭时返回 403 | `list_resource_related_incidents` 错误复用 `_require_prediction_visibility`。关联事件只保留资源项目 `reader` 校验，预测详情、最终预测和容量计划继续受发布开关控制；Mock 使用同一边界。 | 自动化覆盖服务层和 Mock，真实登录态与事件规模仍需部署验证。 |
| 并发分页旧响应覆盖当前页 | 多个 Promise 无请求身份，旧成功或失败会覆盖最新数据、总数、错误和加载状态。项目组、用户目录和最终预测页使用递增请求序号，只允许最新请求写状态。 | 旧网络请求仍会完成，但结果会被忽略，不再污染当前页面。 |
| 懒加载路由测试超时 | 新增路由后穷举式动态导入测试缺少页面 mock，导致等待真实模块链而超时。新增或移动懒加载页时同步维护 mock 清单和固定数量合同。 | 测试桩再次落后时会阻塞验证并掩盖真实路由结果。 |
| 前端全量与覆盖率保留 11 条失败 | `admin-deep-coverage` 与 `page-coverage-gaps` 的按钮桩、LDAP 旧入口断言、AI Chat 缺 active Pinia 已在 `main` 复现。本任务保持聚焦测试、lint、构建和浏览器验收独立通过。 | 覆盖率命令不会输出最终四项汇总，不能宣称覆盖率门禁通过。 |
| 从仓库根目录运行前端 Vitest | 前端别名、测试路径和脚本均以 `frontend/` 为工作目录。进入该目录后使用 `pnpm` 脚本或 `pnpm exec vitest`。 | 错误工作目录会导致“找不到测试”或别名解析失败。 |
| 直接使用系统 `python` 或 `pytest` | 当前 PowerShell 环境没有这两个命令的全局入口。使用仓库 `.venv\\Scripts\\python.exe` 和 `backend/requirements.txt` 维护的依赖。 | 虚拟环境未初始化时，测试无法启动。 |
| 将本地自动化等同于外部集成验收 | PostgreSQL、QuestDB、Redis、Celery、LDAP、NetApp、PowerScale 和飞书不一定在本地可用。 | 外部设备权限、网络、迁移和投递结果必须在隔离部署环境确认。 |
| 前端 Mock 代替授权验证 | Mock 只模拟前端请求与展示数据。真实路由和服务端仍负责最终授权。 | Mock 成功不能证明真实账号、跨项目隔离或设备写入可用。 |
