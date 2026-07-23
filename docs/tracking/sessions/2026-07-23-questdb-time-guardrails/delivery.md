# QuestDB 时间契约防回归门禁

- 会话：`2026-07-23-questdb-time-guardrails`
- 状态：已完成
- 范围：把 QuestDB UTC 时间规范固化为项目提醒、运行时注册约束和自动化测试门禁。

## 成功标准

- 新增 designated timestamp 表但未登记时，测试失败且运行时写入被拒绝。
- 业务写入不能绕过带表名的统一转换入口。
- 项目级开发说明、数据库规范和运维指南给出同一套提交检查。

## 实现

- 新增 `backend/questdb/time_contract.py`，以 `QUESTDB_TIME_CONTRACTS` 登记全部 9 张时间表。
- 新增 `questdb_write_timestamp(table_name, value)`，拒绝未登记表并统一输出 UTC naive。
- 将容量、项目、用户和性能写入路径切换到带表名入口。
- 新增动态契约测试，比对 QuestDB SQL 迁移、历史修复注册表和权威注册表，并扫描业务代码中的底层转换绕过。
- CI 在后端覆盖率任务前增加命名明确的 QuestDB UTC 契约快速失败步骤。
- 在 `AGENTS.md`、数据库规范和修复指南中加入 QuestDB 时间硬约束与提交命令。

## 验证

- TDD RED：契约测试因缺少 `questdb.time_contract` 导入失败；CI 命名门禁测试因工作流缺少步骤失败。
- `..\.venv\Scripts\python.exe -m pytest test/test_questdb_time_contract_guard.py -q`
  - 结果：7 passed。
- `..\.venv\Scripts\python.exe -m pytest test/test_questdb_time_contract_guard.py test/test_datetime_utils.py test/test_questdb_timestamp_repair.py test/test_storage_health_analytics.py test/test_scheduled_user_tasks.py test/test_storage_resource_mapping.py test/test_storage_soft_quota.py -q`
  - 结果：162 passed。
- `..\.venv\Scripts\python.exe -m coverage run --source=questdb.time_contract -m pytest test/test_questdb_time_contract_guard.py -q`
- `..\.venv\Scripts\python.exe -m coverage report -m`
  - 结果：`questdb/time_contract.py` 9/9 statements，100%。
- 负向守卫验证：测试临时创建直接导入并调用 `to_questdb_utc_naive` 的业务样例，守卫准确报告导入行和调用行。

## 未验证范围与风险

- 未在远端 GitHub Actions 实际运行本次工作流；本地静态契约测试已确认命名步骤和目标测试存在。
- AST 扫描防止 Python 业务代码直接导入或调用底层转换，但不能约束仓库外部脚本；仓库外写入必须复用同一注册入口或单独建立等价门禁。
