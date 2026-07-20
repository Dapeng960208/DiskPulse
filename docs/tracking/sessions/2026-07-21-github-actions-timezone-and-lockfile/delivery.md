# GitHub Actions 时区与锁文件修复交付

## 范围

- 定位并修复 Coverage CI run `29758760754` 的后端失败。
- 复现 CI 的完整安装路径，修复前端包管理器与锁文件漂移。
- 按 TDD 保持 RED 与 GREEN 提交边界，并把重复风险沉淀为项目约束。

## 根因与处理

| 严重度 | 问题 | 处理 | 提交 |
| --- | --- | --- | --- |
| 高 | 存储健康分析时间转换依赖 runner 操作系统时区，Ubuntu UTC 环境相差 8 小时 | 新增统一时间工具，显式使用 `Asia/Shanghai`，并覆盖 UTC、供应商偏移、naive 与 Unix 时间戳 | `6204f3e`、`9090853` |
| 高 | CI 在 pnpm 项目中继续使用 npm 与过期 `package-lock.json`，权威 pnpm lockfile 的 patch 配置也不同步 | 删除旧 lockfile，Coverage CI 统一 pnpm frozen install、cache 和脚本，增加工作流契约测试 | `20f2a8f`、`fa5c0b4` |

## 约束同步

- 后端时间转换必须显式指定业务时区；DiskPulse 本地墙上时间固定为 `Asia/Shanghai`，不能继承宿主机时区。
- 前端只保留 `packageManager` 对应的唯一权威 lockfile；CI、部署与本地门禁使用同一包管理器和 frozen install。
- 存储健康分析与性能事件功能事实已同步时间口径和跨 runner 验证边界。

## 验证

- 后端 RED：`D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest backend/test/test_datetime_utils.py -q`，实现前因 `utils.datetime_utils` 不存在而失败。
- 后端聚焦 GREEN：时间工具与完整存储健康分析测试共 101 passed。
- 后端完整覆盖：`coverage run -m pytest backend/test -q` 后执行 `coverage report`，665 passed，TOTAL 87%。
- 前端 RED：CI 契约测试在旧工作流上 1 failed、1 passed；`npm ci` 复现 `ERESOLVE`。
- 前端聚焦 GREEN：`pnpm exec vitest run test/unit/dependency-security-contract.test.js --coverage.enabled=false`，2 passed；`pnpm install --frozen-lockfile` 通过。
- 前端完整覆盖：`pnpm run test:coverage -- --reporter=dot`，100 files / 630 tests passed；Statements 95.74%、Branches 83.00%、Functions 81.38%、Lines 95.74%。
- 前端门禁：`pnpm run lint`、`pnpm run build:prod`、`pnpm run audit:high` 通过；审计剩余 1 个低危、5 个中危，高危/严重为 0。
- Python：`python -m compileall -q backend`、`python -m pip check` 通过。
- 远端：GitHub Actions [Coverage CI run 29760516451](https://github.com/Dapeng960208/DiskPulse/actions/runs/29760516451) 在提交 `fa5c0b4` 上成功。

## 未验证范围和风险

- 未执行真实 NetApp、PowerScale、PostgreSQL、QuestDB、Redis 与浏览器联调；本次验证覆盖静态契约、单元/集成测试、覆盖率、安装、lint 和生产构建。
- 前端仍有 1 个低危、5 个中危传递依赖；不触发当前 high 门禁，后续随上游兼容版本升级。
- 生产构建仍报告既有大 chunk 警告；构建成功，本次 CI 故障未扩展到拆包优化。
