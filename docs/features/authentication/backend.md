# 后端 LDAP 认证

## 目标

DiskPulse 后端通过 LDAP 校验人工用户身份，登录成功后签发 JWT。前端继续使用现有 `/storage-pulse/api/users/*` 调用形态和 `Authorization` token 交互。

## 接口

- `POST /storage-pulse/api/users/login`
  - 请求：`{"username": "alice", "password": "secret"}`
  - 成功：`{"result": {"token": "<jwt>", "token_type": "bearer"}}`
  - 失败：`401 invalid credentials`，不返回密码、LDAP 原始载荷或内部路径。
- `POST /storage-pulse/api/users/logout`
  - 成功：`{"result": null}`。JWT 无状态，前端负责清理本地 token。
- `GET /storage-pulse/api/users/current/profile`
  - 请求头兼容 `Authorization: <token>` 和 `Authorization: Bearer <token>`。
  - 成功返回前端 store 所需字段：`id`、`avatarUrl`、`commonName`、`roleCodes`、`permissionCodes`、`extensionAttributes.rdUsername`。

除登录、登出和 `OPTIONS` 外，`/storage-pulse/api/**` 业务接口默认要求有效 JWT。

## 配置

配置来源沿用 `backend/development.env`、`backend/test.env` 和运行时环境变量。

- `JWT_SECRET_KEY`：JWT HMAC 密钥，运行时必须使用非空、非占位、长度至少 8 的值。
- `JWT_ACCESS_TTL_MINUTES`：access token 有效期，默认 60 分钟。
- `LDAP_SERVER_URL`：LDAP 服务地址。为空时登录会失败。
- `LDAP_START_TLS`：为 `true` 时先执行 STARTTLS，再执行用户 bind。
- `LDAP_TIMEOUT_SECONDS`：LDAP 连接和接收超时。
- `LDAP_BIND_DN`、`LDAP_BIND_PASSWORD`、`LDAP_BIND_PASSWORD_FILE`：service bind 凭据。真实密码不要提交到仓库。
- `LDAP_CA_CERT_PATH`：启用自定义 CA 校验时使用。
- `LDAP_USER_BASES`：用户搜索 base，支持多行或分号分隔。
- `LDAP_USER_CLASS`、`LDAP_USER_NAME_ATTRIBUTE`、`LDAP_USER_FULLNAME_ATTRIBUTE`：用户对象和字段映射。
- `LDAP_USER_EXTRA_FILTERS`：额外 LDAP filter 片段，默认排除 computer 和 group。
- `SUPER_ADMIN_USERNAMES`：分号或换行分隔的超级管理员 `rd_username`。

## 安全边界

- LDAP filter 中的用户名会转义 `\`、`*`、`(`、`)` 和 NUL。
- 启用 `LDAP_START_TLS=true` 时，用户 bind 必须发生在 STARTTLS 成功之后。
- JWT 签名使用 HMAC-SHA256，并使用常量时间比较校验签名。
- 错误响应保持通用，不回显密码、token、LDAP 原始异常或敏感配置。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test.test_auth_ldap backend.test.test_auth_api
cd frontend
npx vitest run test/unit/auth-login.test.js --coverage.enabled=false
```
