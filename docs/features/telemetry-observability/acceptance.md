# 遥测新鲜度与平台可观测验收复盘

## 自动化验收结论

本地自动化验收通过。复查后的功能契约、TDD 修复、Python 编译和迁移结构检查均成功完成。

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 遥测运行账本与新鲜度 | 通过 | `backend/test/test_telemetry_observability.py` 覆盖成功、失败、跳过、重试、空样本、不支持、150/630 秒边界、清理与权限查询。 |
| 指标专用连接 | 通过 | RED 后修复；聚焦测试 `32 passed`，断言路由不传应用 `SessionLocal`，专用 engine 会在抓取结束后释放。 |
| 后端回归 | 通过 | `D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test -q`，`442 passed`。 |
| Python 编译 | 通过 | `D:\dev\DiskPulse\.venv\Scripts\python.exe -m compileall -q backend`。 |
| Alembic 链 | 通过 | 遥测账本保留为 `000000000008`，项目 RBAC/审计以 r9 显式前向；`D:\dev\DiskPulse\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini heads` 输出唯一 `000000000009 (head)`。 |
| 迁移契约 | 通过 | 遥测及 RBAC 迁移回归 `38 passed`；覆盖 r8 → r9 的 SQLite 升降级和 SQLite/PostgreSQL/MySQL 离线 DDL 编译。 |
| 交付卫生 | 通过 | `git diff --check` 通过；没有提交运行时配置、Token 或设备凭据。 |

## 计划对应关系

| 计划验收要求 | 当前结论 |
| --- | --- |
| 所有活跃集群三类最后结果可查询 | 代码与自动化契约已覆盖；需要暗运行期以真实活跃集群数据最终确认。 |
| 不新增设备调用或业务域表写入 | 代码路径审查确认采集调用仍复用既有方法，新增持久化目标仅为运行账本；尚未做真实设备抓包。 |
| QuestDB 停止时 API 降级 | 单元/API 契约覆盖 `degraded`；真实服务停止演练待部署环境执行。 |
| PostgreSQL 或 Redis 停止时 API 503 | 单元/API 契约覆盖 `not_ready`；真实服务停止演练待部署环境执行。 |
| Worker 停止两个周期后变 stale | 新鲜度边界函数和指标读取路径已覆盖；需要真实 Beat/Worker 时间推进演练。 |
| `/metrics` P95 小于 1 秒 | 未执行 100 次真实已认证抓取压测，待部署环境采集。 |

## 部署验收清单

1. 在受控运行时配置下执行 `alembic upgrade head`，验证账本表、索引和集群删除后的 `ON DELETE SET NULL`。
2. 重启 API、Celery Worker 和 Beat，确认 03:17 清理任务被注册；不要复制 worktree 中不存在的真实 `config.yml`。
3. 从允许监控网段使用部署系统挂载的 Token 抓取 `/metrics`，连续 100 次记录 P95；确认 Token 文件不可被应用外不必要主体读取。
4. 分别停止 QuestDB、PostgreSQL、Redis，验证 `degraded`、`not_ready` 和无敏感响应体；恢复后验证依赖 Gauge。
5. 停止 Worker 至少两个采集周期，确认活跃集群的容量/厂商事件在 150 秒后、性能在 630 秒后转为 `stale`。
6. 先暗运行 7 天，对比账本、`/telemetry-runs` 和指标的最后成功时间；确认稳定后再启用既有通知体系中的 `not_ready` 与 `stale` 告警。

## 结论与风险

代码和本地自动化验收已完成，且复查发现的指标连接隔离问题已按 TDD 修复。真实依赖故障演练、网络访问控制、Token 文件权限、设备调用次数观测和指标 P95 属于部署环境验收范围，尚不能描述为已完成。
