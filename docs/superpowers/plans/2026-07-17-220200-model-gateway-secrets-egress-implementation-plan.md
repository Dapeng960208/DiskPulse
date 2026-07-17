# 模型网关、Secrets/KMS 与数据出口控制实施计划

- 依据：[实施计划索引](./2026-07-17-220000-enterprise-ai-storage-implementation-index.md)
- 状态：待实施。
- 前置条件：项目级 RBAC 与统一审计已上线；HashiCorp Vault KV v2、私有模型端点、TLS CA 和网络出口策略可用。

## 目标与边界

- 所有模型调用统一经过 `ModelGateway`，按数据等级、路由策略、允许端点和出口策略做“允许、脱敏后允许、拒绝”。
- 本计划将 AI、存储设备、邮件和文件管理秘密迁移至 Vault；应用数据库不再保存这些可解密秘密。JWT、LDAP、数据库、Redis 和其他运行时秘密的统一治理另行立项，不能被误表述为本计划已完成。
- 大模型永远不获得设备凭据、任意内部 URL 或绕过 DLP 的项目上下文。
- 本工作包不训练模型、不建设向量数据库/RAG、不执行自治配额或保护操作，也不引入 CMDB/SIEM/审批编排。

## 数据与接口契约

- Vault 固定使用 KV v2。面向当前私有化裸机/VM 部署，DiskPulse 固定通过 AppRole 访问：Role ID 为非敏感部署配置，Secret ID 仅通过 systemd credential 或受控只读挂载注入，应用不落库、不记录日志；轮换后旧 Secret ID 立即失效。未来 Kubernetes 部署应另立身份适配工作包，不能在本期以“或工作负载身份”替代可验证方案。应用配置只保存 Vault 地址、认证引用和非敏感路径；不得保存业务秘密。
- 新增 `secret_bindings`：`id`、`resource_type`、`resource_id`、`purpose`、`vault_path`、`key_name`、`status`、`rotated_at`、`validated_at`、审计字段；唯一约束 `(resource_type,resource_id,purpose)`。
- 第一批秘密迁移范围：`AIConfig.api_key_encrypted`、`StorageCluster.storage_password`、`StorageConf.mail_password`、`StorageConf.file_manage_password`。资源改为引用 `secret_binding_id`，服务仅通过 `SecretResolver` 获取瞬态秘密。
- 新增 `model_deployments`：名称、provider、已批准 HTTPS endpoint、模型名、`network_class(private|public)`、`secret_binding_id`、工具能力、超时、Token 上限、启停状态。
- 新增 `model_routing_policies`：优先级、第一阶段全局作用域、允许数据等级、允许工具、允许网络类别、限流与 DLP 策略版本。
- 数据等级固定为 `public`、`internal`、`restricted`：项目、资产、遥测、告警、工具结果、用户标识、IP、完整路径和日志上下文一律至少是 `restricted`。
- 路由规则固定为：`restricted`、工具调用、任何设备或项目数据只能使用私有模型；无可用私有路由时稳定拒绝，绝不降级到公有模型。公有模型只允许 `public`，或 DLP 通过且没有工具/项目上下文的 `internal`。
- 新增 DLP：移除凭据、Token、授权头、LDAP 用户标识、IP、完整 Linux/存储路径、受限日志和标记敏感字段；网关审计只保存发现码、内容哈希和策略版本，不保存原文。同步改造 `AIAuditLog.request_payload/response_payload/detail_payload` 为摘要：上线迁移时对既有原文执行一次 DLP 清洗并永久保留摘要/元数据 365 天。`AIMessage.content` 只在项目作用域、静态加密和最小权限下保存，保留 90 天后删除；历史无项目归属会话在同一窗口内归档或清理。任何不同于这两个期限的客户合规要求必须在生产变更前重新评审，不能在运行时静默放宽。
- 新接口：
  - `GET/POST/PATCH /storage-pulse/api/v1/model-deployments`
  - `GET/POST/PATCH /storage-pulse/api/v1/model-routing-policies`
  - `POST /storage-pulse/api/v1/model-deployments/{id}/validate`
  - `GET /storage-pulse/api/v1/model-egress-decisions`

## 实施步骤

1. 先在非生产部署 Vault KV v2、最小权限 AppRole、systemd credential/受控挂载、出口代理/防火墙规则；完成不可用、权限不足、Secret ID 轮换和恢复演练。
2. 先补 Gateway、DLP、SecretResolver、端点白名单和路由拒绝场景的 RED 测试，再实现 service 和 adapter。
3. 新增数据库表和 nullable `secret_binding_id`；先建立所有连接器、Celery 任务和运维脚本的旧密码字段引用清单，并统一改用 `SecretResolver`。维护窗口执行受限迁移 CLI：解密旧值、写入 Vault、创建 binding、固定探针验证、记录统一审计。
4. 每项资源验证成功后切换到 Vault；全部迁移范围完成后禁止创建/更新 legacy 密文字段，下一版本删除旧字段和 Fernet 解密路径。迁移范围之外的运行时秘密保留现状并在交付清单中明确标识为未治理。
5. 将 `AIConfig` 演进为 `model_deployments`，保留 ID 映射迁移 `AIConversation.model_id` 与 `AIAuditLog.model_id`；会话只可选网关根据用户、项目和数据等级返回的允许模型。
6. 将 `ai_client` 的 provider 直连收敛到 `ModelGateway`；注册时和每次调用时均解析 endpoint，按 `network_class` 校验 FQDN/CIDR allowlist，禁止 HTTP、重定向、用户输入 URL、环境代理继承、未批准 FQDN、地址漂移和不匹配网络类别的地址。公网只能经批准 egress proxy，私有 endpoint 必须使用受信 CA；解析或校验失败一律 fail-closed。
7. 维持现有显式 AI 工具白名单，但强制“工具调用 = `restricted` = 私有模型”；工具执行仍以当前用户身份做确定性权限校验。
8. 更新 AI、部署、配置、密钥轮换和故障降级文档，标明真实 Provider/Vault 联调范围，以及 `AIAuditLog` 365 天摘要/元数据和 `AIMessage` 90 天加密内容的保留/删除任务。

## 验证与验收

- 单元/契约：秘密不出现在 API、日志、异常或审计；Vault 不可用时模型和设备操作 fail-closed；迁移幂等，轮换不改变资源 ID；连接器、Celery 任务和运维脚本均不再直接读取 legacy 密文字段。
- 网关：未批准 URL、HTTP、重定向、DNS/私网绕过、超时、Provider 5xx、格式错误均稳定失败且不泄露内部信息。
- 数据出口：`restricted` 和工具上下文绝不走公有模型；DLP 在脱敏后重新分类；网关和 AI 详细审计不保存请求/响应原文，既有审计已被 DLP 清洗为摘要，会话数据经过加密、作用域检查和 90 天保留策略处理；出口审计能按 `trace_id` 关联路由、策略、DLP 和权限但无原文。
- 真实验收：断开 Vault、私有模型、代理；轮换密钥；模拟证书失败、工具调用与跨项目对话，均得到预期拒绝或降级。
- 验收：无 Secret 明文落库或外泄；敏感数据违规出网为零；所有模型调用均可追溯。
