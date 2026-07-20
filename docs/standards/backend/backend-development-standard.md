# 后端开发规范

本规范用于判断 `backend/` 改动边界、实现位置、安全要求和验证范围。

## 1. 开工前

- 涉及后端代码、配置、脚本、测试、接口文档或部署时，先读本文、[文档规范](../documentation/documentation-standard.md)、[Git 提交规范](../git/git-commit-standard.md)，并按[开发阅读矩阵](../documentation/development-reading-guide.md)阅读对应功能专题。
- 涉及模型、迁移、查询、索引、QuestDB 或 Redis 数据边界时，必须再读[数据库规范](../database/database-development-standard.md)；只有接口契约或用户体验联动前端时才读前端规范。
- 后端任务默认只改 `backend/` 和相关 `docs/`；除非需求明确联动前端，不改 `frontend/`。
- 功能、接口、配置、权限、数据库、部署、测试入口或用户可见行为变化，必须同步 `docs/`、本会话 `docs/tracking/sessions/<session-id>/delivery.md`；可复现错误按[开发跟踪索引](../../tracking/README.md)分类记录。

## 2. 技术与目录

- 技术栈：FastAPI、Pydantic、SQLAlchemy、Alembic；后端依赖以 `backend/requirements.txt` 为准，本地检查使用仓库 `.venv` 解释器。
- 数据库：PostGres QuestDB时序数据库 中间件：Redis。
- OpenAPI / FastAPI 标题、README、部署文档和架构文档中的主产品名称统一使用“DiskPulse”。

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
- 存储容量接口必须遵守[容量单位 API 契约](./capacity-unit-contract.md)：保留 GB 原始字段、返回字段级 `capacity` 显示单位，并为曲线返回 `data_unit`。
- 输入校验放 Pydantic schema；跨资源、权限、数据库存在性校验放 dependency 或 service。
- Router 只做 HTTP 参数、权限依赖和响应组装；不得定义 Pydantic `BaseModel`，不得直接导入 SQLAlchemy/model，不得执行表级查询或写入。
- Service 负责领域编排、权限后置校验、跨表组合、事务边界和错误转换。
- 表级 `select/get/list/exists/create/update/delete/add/count` 必须放到 CRUD 文件，不在 router 或 service 重写表级 SQL。

## 5. 数据库、事务与配置

- 模型、迁移、查询、索引、时序数据和 Redis 的权威规则见[数据库规范](../database/database-development-standard.md)；后端实现不得在 router 中绕过这些边界。
- Router 负责 HTTP 参数、权限依赖和响应组装；Service 负责跨资源编排、事务边界和错误转换；CRUD 负责表级读取与写入。
- 真实配置、密码文件和密钥不得提交。配置、数据模型或迁移变化必须同步对应功能专题、架构说明和验证。

## 6. 测试与验证

- 新增行为优先 TDD：先补失败测试，再实现，再验证。
- 关键安全路径必须直接测试：JWT、LDAP bind、机器上报 token、权限拒绝、输入校验、错误响应。
- API 测试必须覆盖成功路径和至少一个失败路径。
- 整体覆盖率门槛为 Statements、Branches、Functions、Lines 均不低于 85%；核心功能目标不低于 85%。
- 涉及数据库的验证、跨方言兼容和性能治理按[数据库规范](../database/database-development-standard.md)执行。
- 最终说明必须如实写明已执行验证、未执行项、原因、未验证范围和风险。
