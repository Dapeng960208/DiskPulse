# 后端项目规范（AI 快速版）

本规范用于让 AI 快速判断 `backend/` 改动边界、实现位置、安全要求和验证范围。

## 1. 开工前

- 涉及后端代码、配置、数据库、迁移、脚本、测试、接口文档或部署时，先读本文、`docs/standards/documentation-standard.md`、`docs/standards/domain-terminology.md` 和 `docs/standards/frontend-design-standard.md`。
- 后端任务默认只改 `backend/` 和相关 `docs/`；除非需求明确联动前端，不改 `frontend/`。
- 功能、接口、配置、权限、数据库、部署、测试入口或用户可见行为变化，必须同步 `docs/` 和 `docs/tracking/current-release.md`。

## 2. 技术与目录

- 技术栈：FastAPI、Pydantic、SQLAlchemy、Alembic；依赖和命令使用 `uv`。
- 数据库：PostGres QuestDB时序数据库 中间件：Redis。
- OpenAPI / FastAPI 标题、README、部署文档和架构文档中的主产品名称统一使用“回归分析平台”，不要再出现与前端站点不一致的产品名。

## 3. 安全与权限

- 禁止硬编码真实密钥、密码、token、生产地址和个人凭据；`backend/config.yml`、真实 `.env`、密码文件不得提交。
- 运行时必须拒绝空值、占位或过短的 `JWT_SECRET_KEY`；启用上报时也必须校验 `REPORT_INGEST_TOKEN`。
- 人工用户认证走 LDAP 登录和 JWT；机器上报使用独立 `X-Report-Ingest-Token`，不得复用人工登录。
- token 比较必须使用常量时间比较。
- 涉及项目数据的读写必须校验项目上下文、项目权限和项目隔离。
- 新增管理接口必须明确 super admin、project admin、editor、reader 的访问边界。
- LDAP 必须遵守 TLS-before-bind；LDAP filter 中的用户输入必须转义。
- 错误响应不得回显密码、token、LDAP 原始载荷、敏感配置、内部路径或栈信息。

## 4. API 与业务分层

- 路由函数保持单一 HTTP 操作；参数和依赖优先用 `typing.Annotated`。
- 新增公开接口应定义返回类型或 `response_model`。
- 输入校验放 Pydantic schema；跨资源、权限、数据库存在性校验放 dependency 或 service。
- Router 只做 HTTP 参数、权限依赖和响应组装；不得定义 Pydantic `BaseModel`，不得直接导入 SQLAlchemy/model，不得执行表级查询或写入。
- Service 负责领域编排、权限后置校验、跨表组合、事务边界和错误转换。
- 表级 `select/get/list/exists/create/update/delete/add/count` 必须放到 CRUD 文件，不在 router 或 service 重写表级 SQL。

## 5. 数据库、事务与配置

- 数据访问必须使用 SQLAlchemy 参数化表达式，不拼接 SQL 字符串。
- 写操作必须明确 commit、rollback 和异常边界；`IntegrityError` 等数据库异常必须 rollback 并返回稳定错误。
- 列表接口必须使用数据库分页和 count 查询，不得先全量加载再分页。
- 跨项目查询必须带项目过滤条件。
- 新增或改造列表接口时，默认使用“列表摘要查询”而不是详情级 ORM 深度预加载：
  - 列表页只查询当前页面展示所需字段，不得直接复用详情页的 `selectinload` / `joinedload` 深加载路径。
  - 多值摘要字段必须先分页拿到当前页主键，再按主键批量补充统计、预览和字典信息；禁止为列表页加载完整 `build_jobs`、`simulation_jobs`、`issues` 等大集合后在 Python 中裁剪。
- 新增高频过滤、排序、关联查找或物化读路径时，必须同步评估数据库索引：
  - 项目隔离字段应进入组合索引前缀，例如 `project_id + 时间/维度/id`。
  - 作业、标签、模块等关联过滤应优先补 lookup 组合索引，避免大表 join 或关联表全表扫描。
  - Alembic migration 与 ORM 模型索引声明必须同步，并补跨方言 SQL 编译或迁移验证测试。
- 新增模型字段必须同步 Alembic migration、schema、serializer 和测试。
- Alembic revision id 必须控制在 32 字符内，避免 PostgreSQL 在写入 `alembic_version.version_num` 时失败。
- 新增或修改 Alembic migration 时，默认必须继续兼容 `SQLite`、`PostgreSQL` 和 `MySQL`；不要依赖单一数据库对布尔字面量、默认值、DDL 语法或隐式类型转换的宽松行为。
- 迁移中的 DML/DDL 优先使用 SQLAlchemy 类型、绑定参数和 `sa.true()/sa.false()` 等方言无关表达；如果必须按方言分支，分支必须显式覆盖兼容策略，而不是只为单一数据库打补丁。
- 改造读路径（深加载改物化表/标量查询、ORM 对象改 dict 行）时，必须先盘点旧路径“顺带”提供的隐性行为，逐条迁移而非只搬主字段：
  - 旧实现经 serializer 产出的派生字段（如最新 run 通过原始报告恢复结束时间时区 `resolve_run_end_time_iso`）在换成标量查询后会丢失；必须把所需源列（如 `raw_report_path`）一并选出，并抽出仅依赖标量的等价函数复用，避免逻辑分叉。
  - 用 `select(标量列...)` 替换 `select(Model)` 时，下游一切 `run.xxx` 属性访问都要改为 dict/Row 取值；先确认 overview、序列化、排序键等所有消费点。
  - service 之间存在循环依赖（如 `analytics_service` ↔ `analytics_materialization_service`）时，刷新/状态判断等反向依赖用函数内延迟 import，不要提到模块顶层。
  - 物化读路径要显式处理“窗口内无数据但物化本身有效”的情况：兜底同步刷新只在 `status 为空或 dirty` 时触发，已刷新且窗口为空不得反复强刷。

## 6. 测试与验证

- 新增行为优先 TDD：先补失败测试，再实现，再验证。
- 关键安全路径必须直接测试：JWT、LDAP bind、机器上报 token、权限拒绝、输入校验、错误响应。
- API 测试必须覆盖成功路径和至少一个失败路径。
- 整体覆盖率门槛为 Statements、Branches、Functions、Lines 均不低于 90%；核心功能目标不低于 90%。
- 涉及 Alembic 的变更必须验证迁移可应用；涉及数据库差异时优先补 PostgreSQL 集成测试，或说明仅 SQLite 验证风险。
- 涉及 Alembic 的变更，除迁移链验证外，还必须补至少一条跨方言回归保障：优先覆盖 `SQLite`、`PostgreSQL`、`MySQL` 的 SQL 编译或参数绑定行为，防止迁移只在当前本地数据库上可用。
- 涉及列表、分析、搜索或统计性能的变更必须补性能治理测试：
  - 列表接口测试需锁定不会调用详情级深加载函数，不会加载完整作业/问题集合。
  - 分页测试需覆盖 `total` 与当前页数据分离，过滤条件在分页前生效。
  - 分析接口测试需锁定高频场景读取物化表或轻量 SQL 点位，不回退到深加载路径。
  - 新增索引需补模型索引存在性、跨方言 SQL 编译或 Alembic upgrade 验证。
- 最终说明必须如实写明已执行验证、未执行项、原因、未验证范围和风险。

## 7. 常用命令

```powershell
```
