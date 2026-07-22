# 四维容量耗尽风险实施计划

- 批准时间：2026-07-22 09:05:36 +08:00
- 设计文档：[四维容量耗尽风险设计](../specs/2026-07-22-four-dimension-capacity-exhaustion-risk-design.md)
- 实施分支：`codex/four-dimension-capacity-risk`
- 实施工作区：`D:\dev\DiskPulse\.worktrees\four-dimension-capacity-risk`

## 已确认范围

容量预测收敛为存储集群、项目、项目组和用户目录四个维度的耗尽风险。一级预测栏目和列表行预测操作移除，风险进入对应资源详情页。存储集群仅超级管理员可见；项目范围资源按当前项目权限和发布开关开放。治理页解释基线、风险分级和 AI 启用标准，AI 候选只允许已配置且已启用的模型。

## 实施步骤

1. 建立后端 RED：
   - 为 `project` 增加预测目标契约测试，并验证其使用 `project_storage_usages`；
   - 覆盖四类 `PredictionAssetType`、资源授权矩阵和轻量风险摘要接口；
   - 覆盖“数据不足、紧急、高风险、关注、30 日内无风险”的日期边界；
   - 覆盖 AI 候选创建和启用时的 `enabled=true` 校验，以及四维候选任务范围。
2. 建立前端 RED：
   - 共享耗尽风险面板的加载、风险级别、数据不足、空态、错误态和无权限；
   - 四类资源详情页的懒加载挂载；
   - 一级菜单和列表操作移除、旧预测路由兼容跳转；
   - 治理页的三类规则说明、启用模型过滤和模型名称展示；
   - Mock 四维风险摘要与权限响应。
3. 运行新增聚焦测试，确认失败由缺失的四维风险实现导致；提交 RED 检查点。
4. 实现后端最小闭环：
   - 扩展资产类型、项目目标、可空集群归属和四维候选任务；
   - 在 service 中统一资源授权和风险分级；
   - 新增 Pydantic 风险摘要响应与 FastAPI 路由；
   - 创建/启用候选时复核已配置模型存在且启用。
5. 实现前端最小闭环：
   - 新增共享 `CapacityExhaustionRiskPanel` 和 API 方法；
   - 四类详情页新增或收敛“耗尽风险”页签；
   - 移除一级菜单和行操作，将旧路由改为隐藏重定向；
   - 治理页增加规则提示、只列启用模型并展示可读模型名；
   - 更新 Mock。
6. 运行与 RED 相同的聚焦测试确认 GREEN，并提交实现检查点。
7. 补齐事实和跟踪文档：
   - 新增 `docs/features/ai/capacity-prediction/overview.md`、`backend.md`、`frontend.md`；
   - 更新事件中心、项目 RBAC、存储集群、当前能力和文档索引；
   - 维护 `docs/tracking/sessions/2026-07-22-four-dimension-capacity-prediction/delivery.md` 与 `errors.md`。
8. 验证与收尾：
   - 后端容量预测、事件和权限聚焦测试；
   - 前端容量风险、治理、路由、详情和 Mock 聚焦测试；
   - 受影响代码覆盖率、前端 lint、构建、`git diff --check`；
   - 使用内置浏览器在 Mock 模式检查四类详情与治理页；
   - 明确未执行的真实 PostgreSQL、QuestDB、Redis、Celery 和外部 AI Provider 联调。

## 计划测试命令

后端聚焦测试使用仓库根虚拟环境，并把临时目录定向到工作区可写路径：

```powershell
D:\dev\DiskPulse\.venv\Scripts\python.exe -m pytest test/test_capacity_prediction_governance.py test/test_forecast_incident_center.py -q
```

前端聚焦测试：

```powershell
pnpm exec vitest run test/unit/forecast-governance-page.test.js test/unit/capacity-exhaustion-risk-panel.test.js test/unit/detail-capacity-prediction-navigation.test.js test/unit/list-capacity-prediction-navigation.test.js test/unit/router/routes.test.js test/unit/mock-capacity-prediction.test.js --coverage.enabled=false
```

完成检查：

```powershell
pnpm run lint
pnpm run build:prod
git diff --check
```

## 基线证据

- 后端 `test_capacity_prediction_governance.py` 与 `test_forecast_incident_center.py`：65 passed。
- 前端 6 个现有容量预测/治理相关文件：31 passed。
- 工作区从设计提交 `9a2275f` 创建；依赖使用 `pnpm install --frozen-lockfile` 安装。

## 假设与依赖

- `project_storage_usages` 和 `storage_cluster_storage_usages` 继续是项目与集群时序容量事实来源。
- `Project.limit`、`StorageCluster.limit`、`Group.limit`、`StorageUsage.limit` 使用现有 GB 原始口径。
- 不新增数据库表或迁移；预测资产类型为字符串契约扩展。
- 旧完整预测、容量计划和关联事件接口本次保留，仅用户可见入口切换到轻量风险摘要。
- 项目可以跨多个存储集群，项目预测不得伪造单一 `storage_cluster_id`。
