# 厂商事件关联信息全覆盖

## 交付范围

- 原地补全 `000000000017_update_vendor_event_associations.py`：以 68 个当前测试库代码的静态证据矩阵做确定性 upsert；33 条 NetApp 逐代码官方 EMS 依据为 `reviewed`，10 条 NetApp 与 25 条 Dell PowerScale 因证据不足统一归为 `unknown + pending`。
- 增加 `recommended_solution_zh` 的数据库、Pydantic、服务序列化、管理 API、Mock 与前端一致性约束：仅 `reviewed` 必填，`pending` 保持空值。
- 在管理目录和存储集群系统事件详情中展示推荐解决方案；待核验项只显示“暂无可核验官方方案”。
- 不改动 `storage_alerts` 原始事件正文，不新增 API 路由或周期任务。

## 验证

- RED 检查点已提交；GREEN 后端验证：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_vendor_event_association_contract.py backend/test/test_vendor_event_definition_admin_api.py backend/test/test_vendor_event_definitions_migration.py -q --basetemp D:\dev\DiskPulse\.tmp\vendor-event-tests\pytest`，`38 passed`。
- GREEN 前端验证：`pnpm exec vitest run test/unit/pages/vendor-event-definitions.test.js test/unit/pages/storage-cluster-health-analytics.test.js test/unit/mock-runtime.test.js --coverage.enabled=false`，`75 passed`；目标文件 ESLint 和 `pnpm run build:test` 均通过。
- `git diff --check` 通过。迁移离线编译覆盖 SQLite、PostgreSQL、MySQL；本地迁移测试覆盖 `016 → 017 → 016 → 017`。
- 测试库在重放前已备份到仓库外 `C:\Users\guojianpeng\AppData\Local\Temp\diskpulse-vendor-event-association-backups\vendor-event-definitions-017-20260722-102612.json`，SHA-256 为 `ddfc1a61e684139cd713602a9075218230e01024e9ebc79d4d036f7cb193c984`。预检确认仅有本次 68 个 NetApp/Isilon 目录项。
- 已实际执行测试库 `017 → 016 → 017` 并读回：revision=`000000000017`、共 68 项、NetApp `33 reviewed + 10 pending`、PowerScale `25 pending`；所有已审核项具备 URL、版本、明确类型和非空方案，所有待核验项保持 `unknown` 且不带候选语义。回滚事务验证数据库会拒绝 `reviewed + 空 recommended_solution_zh`。

## 待核验范围

- 35 条 `pending` 项的已查入口、缺失证据和补证方式见[逐代码待核验清单](../../../features/storage/event-association/unverified-code-list.md)。未获得精确官方事件页或设备运行时目录证据前，不会输出推测性标题、关联类型或中文方案。
- 未在真实 OneFS/ONTAP 设备运行时目录上验收；该风险通过待核验清单显式保留，不以目录推测替代官方逐代码证据。
