# 后端 LDAP 认证

## 目标

DiskPulse 后端通过 LDAP 校验人工用户身份，登录成功后签发 JWT，并在 Redis 中保存对应会话。前端继续使用现有 `/storage-pulse/api/users/*` 调用形态，并通过 `Authorization: Bearer <token>` 访问业务接口。

## 接口

- `POST /storage-pulse/api/users/login`
  - 请求：`{"username": "alice", "password": "secret"}`
  - 成功：`{"result": {"token": "<jwt>", "token_type": "bearer"}}`，同时写入 Redis 会话白名单。
  - 失败：`401 invalid credentials`，不返回密码、LDAP 原始载荷或内部路径。
- `POST /storage-pulse/api/users/logout`
  - 请求头：`Authorization: Bearer <token>`。
  - 成功：`{"result": null}`。后端撤销当前 JWT，前端同时清理本地 token。
- `GET /storage-pulse/api/users/current/profile`
  - 请求头：`Authorization: Bearer <token>`。
  - 成功返回前端 store 所需字段：`id`、`avatarUrl`、`commonName`、`roleCodes`、`permissionCodes`、`extensionAttributes.rdUsername`。

除登录和 `OPTIONS` 外，`/storage-pulse/api/**` 业务接口默认要求有效 JWT。配置、用户变更、资源变更、扩容、备份删除和回滚等高风险操作要求 `super_admin_usernames` 中配置的超级管理员。

## 配置

运行配置统一来自本地 `backend/config.yml`，结构参考可提交的 `backend/config.example.yml`。真实配置和密码文件由 `.gitignore` 排除，不读取 `.env` 或运行时环境变量。

- `jwt.secret_key`：JWT HMAC 密钥，必须使用非空、非占位、长度至少 8 的值。
- `jwt.access_ttl_minutes`：JWT 和 Redis 会话的共同有效期，默认 `10080` 分钟（7 天）。
- `redis.host`、`redis.port`：认证会话复用 Redis DB 7；Redis 不可用时登录和鉴权返回 `503`，不会绕过会话校验。
- `ldap.uri`：LDAP 服务地址。`ldap://` 必须配合 `ldap.starttls: true`；也可使用 `ldaps://`。
- `ldap.bind_dn`、`ldap.bind_password_file`：service bind 凭据；相对密码文件路径按 `config.yml` 所在目录解析。
- `ldap.user_bases`：用户搜索 base 的 YAML 列表。
- `ldap.group_bases`：保留组搜索范围配置，本版本不据此映射角色或权限。
- `ldap.lookup_user_dn: true`、`ldap.lookup_as_user: false`：固定为服务账号查询用户 DN、用户账号执行 bind；其他组合启动时拒绝。
- `ldap.user_class`、`ldap.user_name_attribute`、`ldap.user_fullname_attribute`：用户对象和字段映射。
- `ldap.user_department_attribute`：用户部门属性，默认 `department`；目录字段不同时必须在本地真实 `backend/config.yml` 中调整。
- `ldap.user_extra_filters`：额外 LDAP filter 列表，默认排除 computer 和 group。
- `super_admin_usernames`：超级管理员 `rd_username` 的 YAML 列表。

超级管理员还可通过“用户信息管理”页面把完整 LDAP 用户快照同步到系统用户表。同步生命周期、公共用户保护和失败回滚规则见[用户信息管理](../user-management/overview.md)。

## 安全边界

- LDAP filter 中的用户名会转义 `\`、`*`、`(`、`)` 和 NUL。
- 登录按用户名逐个搜索 `ldap.user_bases`，某个范围无匹配时继续搜索其他范围；只有完整用户同步才要求所有搜索范围成功返回。
- 启用 `ldap.starttls: true` 时，用户 bind 必须发生在 STARTTLS 成功之后。
- JWT 签名使用 HMAC-SHA256，并使用常量时间比较校验签名。
- JWT header 必须为 `alg=HS256`、`typ=JWT`；裸 token 请求头会返回 `401`。
- Redis key 使用 `diskpulse:auth:token:<jti>`，value 只保存 JWT 的 SHA-256 摘要，不保存原始 token；摘要比较使用常量时间比较。
- 每次鉴权同时校验 JWT 签名、到期时间和 Redis 会话白名单；签名有效但 Redis 中不存在的 token 返回 `401`。
- 登出删除当前 JWT 的 Redis 会话；后端重启后只要 `jwt.secret_key` 和 Redis 数据未变化，会话仍然有效。
- Redis 连接或读写失败时认证链路 fail-closed 并返回 `503`，避免把缓存故障降级成免校验。
- 错误响应保持通用，不回显密码、token、LDAP 原始异常或敏感配置。

## 请求与连接性能

- 登录页取得 profile 后，路由守卫复用前端 store；只有刷新后 store 为空时才重新请求 `GET /users/current/profile`。
- 后端把已通过 JWT 校验并从数据库读取的用户保存到当前 `Request`，同一请求内的依赖直接复用；每个新请求仍独立校验 JWT 和查询用户，不跨请求缓存认证结果。
- Redis 缓存的是 token 会话白名单，不缓存用户资料或权限；用户资料仍从 PostgreSQL 读取。
- LDAP `Server` 使用 `get_info=NONE`，不在每次连接时读取无关的目录 schema/info；STARTTLS、CA 证书校验、连接超时和 TLS-before-bind 保持不变。
- 部署环境精确用户查询优化前为 `1738.9/1548.0/1601.1 ms`，优化后为 `651.4/353.6/366.4 ms`，六次均为 `matches=1`。独立进程数据库查询 cold 为 `777.4 ms`，warm 为 `41.9–46.1 ms`。
- 上述数据是 LDAP 查询和数据库查询的分项测量，不包含真实密码用户 bind 的完整登录耗时；浏览器真实登录仍需单独冒烟验证。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest backend\test\test_auth_api.py backend\test\test_auth_ldap.py backend\test\test_user_management_ldap_sync.py
cd frontend
npx vitest run test/unit/auth-login.test.js test/unit/router/index.test.js --coverage.enabled=false
```

部署本版本后，旧 token 因未写入 Redis 白名单会返回 `401`，用户需要重新登录一次；随后新 token 默认保持 7 天。后端进程和 Celery 使用同一 Redis DB 7 时必须保留 `diskpulse:auth:*` key，不能按普通临时缓存整体清空。
