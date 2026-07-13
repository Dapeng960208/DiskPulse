# 后端 LDAP 认证

## 目标

DiskPulse 后端通过 LDAP 校验人工用户身份，登录成功后签发 JWT。前端继续使用现有 `/storage-pulse/api/users/*` 调用形态，并通过 `Authorization: Bearer <token>` 访问业务接口。

## 接口

- `POST /storage-pulse/api/users/login`
  - 请求：`{"username": "alice", "password": "secret"}`
  - 成功：`{"result": {"token": "<jwt>", "token_type": "bearer"}}`
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
- `jwt.access_ttl_minutes`：access token 有效期，默认 60 分钟。
- `ldap.uri`：LDAP 服务地址。`ldap://` 必须配合 `ldap.starttls: true`；也可使用 `ldaps://`。
- `ldap.bind_dn`、`ldap.bind_password_file`：service bind 凭据；相对密码文件路径按 `config.yml` 所在目录解析。
- `ldap.user_bases`：用户搜索 base 的 YAML 列表。
- `ldap.group_bases`：保留组搜索范围配置，本版本不据此映射角色或权限。
- `ldap.lookup_user_dn: true`、`ldap.lookup_as_user: false`：固定为服务账号查询用户 DN、用户账号执行 bind；其他组合启动时拒绝。
- `ldap.user_class`、`ldap.user_name_attribute`、`ldap.user_fullname_attribute`：用户对象和字段映射。
- `ldap.user_extra_filters`：额外 LDAP filter 列表，默认排除 computer 和 group。
- `super_admin_usernames`：超级管理员 `rd_username` 的 YAML 列表。

## 安全边界

- LDAP filter 中的用户名会转义 `\`、`*`、`(`、`)` 和 NUL。
- 启用 `ldap.starttls: true` 时，用户 bind 必须发生在 STARTTLS 成功之后。
- JWT 签名使用 HMAC-SHA256，并使用常量时间比较校验签名。
- JWT header 必须为 `alg=HS256`、`typ=JWT`；裸 token 请求头会返回 `401`。
- 登出会撤销当前 JWT 的 `jti`，同一进程内后续请求会被拒绝。
- 错误响应保持通用，不回显密码、token、LDAP 原始异常或敏感配置。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest backend\test\test_app_config.py backend\test\test_auth_ldap.py backend\test\test_auth_api.py
cd frontend
npx vitest run test/unit/auth-login.test.js --coverage.enabled=false
```
